from datetime import datetime
import uuid
from app.agents.base import CustomerContext
from app.agents.implementations import (
    SignalIngestionAgent,
    BehaviorShiftAgent,
    NextBestActionAgent,
    ChannelTimingAgent,
    SuppressionAgent,
    ResponseTrackingAgent,
    EscalationAgent,
)
from app.services.ai import infer_with_groq, message_with_groq
from app.models.entities import AIDecision, AuditLog, Escalation
from app.rules.engine import derive_signals, channel_scores


async def run_pipeline(db, customer, signals, transactions, engagements):
    latest_signal = signals[0] if signals else {}
    context = CustomerContext(
        customer=customer,
        signals=signals,
        transactions=transactions,
        engagements=engagements,
    )

    signal_stage = SignalIngestionAgent().run(context)
    behavior_stage = BehaviorShiftAgent().run(context)

    derived = derive_signals(latest_signal)
    high_signal = any(x["severity"] == "High" for x in derived)
    save = float(latest_signal.get("savings_contribution_change_pct") or 0)
    spend = float(latest_signal.get("spending_change_pct") or 0)
    unusual = bool(latest_signal.get("unusual_withdrawal_flag"))
    investment_activity = any(
        str(t.get("merchant_category", "")).lower() == "investment"
        for t in transactions
    )

    if high_signal and (save <= -40 or unusual) and spend >= 30:
        possible_need = "Possible change in financial circumstances"
    elif investment_activity and save >= 15:
        possible_need = "Possible investment interest"
    elif save >= 25:
        possible_need = "Possible savings goal opportunity"
    elif spend >= 40:
        possible_need = "Possible need for spending or budgeting education"
    else:
        possible_need = "Possible need for general financial education"

    fallback = {
        "possible_need": possible_need,
        "confidence": float(latest_signal.get("inference_confidence") or behavior_stage["confidence"]),
        "reason": "Observed behavior supports a cautious hypothesis; it is not a confirmed life event",
        "sensitivity": "high" if high_signal and (save <= -40 or unusual) else "standard",
        "evidence": [x["type"] for x in derived],
    }

    context.need_inference = await infer_with_groq(
        customer,
        context.behavior_analysis,
        signals,
        engagements,
        fallback,
    )

    next_action_stage = NextBestActionAgent().run(context)

    if next_action_stage["action"] == "Human Relationship Manager":
        fallback_message = "No automated promotional message generated. A relationship manager should review this case."
    else:
        fallback_message = (
            "We noticed a recent change in your account activity. If useful, we can share "
            "general educational resources or help you review your options."
        )

    generated_message = await message_with_groq(
        customer,
        context.need_inference,
        context.next_best_action,
        fallback_message,
    )
    context.message = {
        "status": "completed",
        "message": generated_message,
        "tone": "cautious" if context.need_inference.get("confidence", 0) < 0.75 else "personalized",
        "provider": "Groq" if __import__("app.config", fromlist=["settings"]).settings.groq_api_key else "Rules fallback",
    }

    channel_stage = ChannelTimingAgent().run(context)
    suppression_stage = SuppressionAgent().run(context)
    response_stage = ResponseTrackingAgent().run(context)
    escalation_stage = EscalationAgent().run(context)

    if context.escalation.get("required"):
        final_status = "ESCALATED TO HUMAN"
    elif context.suppression.get("suppressed"):
        final_status = "DO NOT CONTACT" if context.suppression.get("reason") == "OPT-OUT" else "SUPPRESSED"
    else:
        final_status = "READY FOR CUSTOMER ENGAGEMENT"

    decision = {
        "customer_id": customer["customer_id"],
        "observed": context.behavior_analysis.get("observed"),
        "possible_interpretation": context.need_inference.get("possible_need"),
        "confidence": context.need_inference.get("confidence", 0),
        "priority": context.next_best_action.get("priority"),
        "recommended_action": context.next_best_action.get("action"),
        "channel": context.channel.get("channel"),
        "message": context.message.get("message"),
        "suppression": context.suppression,
        "escalation": context.escalation,
        "final_status": final_status,
        "ai_reason": context.need_inference.get("reason"),
        "evidence": context.need_inference.get("evidence", []),
    }

    stages = [
        {"agent": "Signal Ingestion Agent", **signal_stage},
        {"agent": "Behavioral Shift Agent", **behavior_stage},
        {"agent": "Need Inference Agent", "status": "completed", **context.need_inference},
        {"agent": "Next Best Action Agent", **next_action_stage},
        {"agent": "Message Generation Agent", **context.message},
        {"agent": "Channel & Timing Agent", **channel_stage},
        {"agent": "Suppression & Consent Agent", **suppression_stage},
        {"agent": "Response Tracking Agent", **response_stage},
        {"agent": "Sensitive Escalation Agent", **escalation_stage},
        {
            "agent": "Orchestrator Agent",
            "status": "completed",
            "final_status": final_status,
            "reason": "Combined agent outputs and governance rules",
        },
    ]

    case_id = None
    if final_status == "ESCALATED TO HUMAN":
        case_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        db.add(
            Escalation(
                case_id=case_id,
                customer_id=customer["customer_id"],
                priority=decision["priority"],
                reason=decision["possible_interpretation"],
                confidence=decision["confidence"],
                assigned_to="Unassigned",
                status="Open",
                created_at=datetime.utcnow(),
            )
        )
        decision["case_id"] = case_id

    db.add(
        AIDecision(
            customer_id=customer["customer_id"],
            final_status=final_status,
            priority=decision["priority"],
            confidence=decision["confidence"],
            action=decision["recommended_action"],
            channel=decision["channel"],
            message=decision["message"],
            created_at=datetime.utcnow(),
        )
    )
    db.add(
        AuditLog(
            timestamp=datetime.utcnow(),
            customer_id=customer["customer_id"],
            signal=decision["observed"],
            agent="Orchestrator Agent",
            decision=final_status,
            confidence=decision["confidence"],
            channel=decision["channel"],
            suppression_reason=decision["suppression"].get("reason"),
            escalation=decision["escalation"].get("required", False),
            final_action=decision["recommended_action"],
        )
    )
    db.commit()

    return {
        "customer": customer,
        "stages": stages,
        "decision": decision,
        "ai_mode": "Groq LLM" if __import__("app.config", fromlist=["settings"]).settings.groq_api_key else "Rules Fallback",
        "channel_scores": channel_scores(customer, engagements),
    }
