from app.agents.base import Agent
from app.rules.engine import derive_signals


class SignalIngestionAgent(Agent):
    name = "Signal Ingestion Agent"

    def run(self, c):
        signal = c.signals[0] if c.signals else {}
        detected = derive_signals(signal)
        confidence = max((0.55, float(signal.get("inference_confidence") or 0)))
        out = {
            "status": "completed",
            "signals": detected,
            "signal_count": len(detected),
            "confidence": min(confidence, 1.0),
            "reason": "Latest behavioral snapshot converted into explainable signals",
        }
        c.audit_events.append(out)
        return out


class BehaviorShiftAgent(Agent):
    name = "Behavioral Shift Agent"

    def run(self, c):
        signal = c.signals[0] if c.signals else {}
        spend = float(signal.get("spending_change_pct") or 0)
        save = float(signal.get("savings_contribution_change_pct") or 0)
        login = float(signal.get("app_login_change_pct") or 0)
        unusual = bool(signal.get("unusual_withdrawal_flag"))
        significant = abs(save) >= 40 or abs(spend) >= 40 or abs(login) >= 50 or unusual

        transaction_count = len(c.transactions)
        debit_total = sum(
            float(t.get("amount_inr") or 0)
            for t in c.transactions
            if str(t.get("transaction_type", "")).lower() == "debit"
        )
        credit_total = sum(
            float(t.get("amount_inr") or 0)
            for t in c.transactions
            if str(t.get("transaction_type", "")).lower() == "credit"
        )

        observations = [
            f"Savings contribution: {save:+.0f}%",
            f"Spending: {spend:+.0f}%",
            f"App activity: {login:+.0f}%",
        ]
        if unusual:
            observations.append("unusual withdrawal flagged")

        out = {
            "status": "completed",
            "result": "significant_shift" if significant else "no_major_shift",
            "confidence": 0.84 if significant else 0.62,
            "observed": "; ".join(observations),
            "reason": "Behavioral changes compared with the supplied customer snapshot",
            "transaction_count": transaction_count,
            "observed_debit_total": round(debit_total, 2),
            "observed_credit_total": round(credit_total, 2),
        }
        c.behavior_analysis = out
        return out


class NextBestActionAgent(Agent):
    name = "Next Best Action Agent"

    def run(self, c):
        need = str(c.need_inference.get("possible_need", "")).lower()
        sensitivity = str(c.need_inference.get("sensitivity", "standard")).lower()
        confidence = float(c.need_inference.get("confidence", 0))

        if sensitivity == "high":
            action, priority = "Human Relationship Manager", "HIGH"
        elif "investment" in need:
            action, priority = "Investment Education", "MEDIUM"
        elif "saving" in need:
            action, priority = "Savings Guidance", "MEDIUM"
        elif "spending" in need or "cash" in need or "budget" in need:
            action, priority = "General Financial Education", "MEDIUM"
        else:
            action, priority = "General Financial Education", "LOW"

        out = {
            "status": "completed",
            "action": action,
            "priority": priority,
            "confidence": confidence,
            "reason": "Action combines inferred need, sensitivity and confidence",
        }
        c.next_best_action = out
        return out


class ChannelTimingAgent(Agent):
    name = "Channel & Timing Agent"

    def run(self, c):
        if c.next_best_action.get("action") == "Human Relationship Manager":
            channel = "Relationship Manager"
            timing = "Human follow-up"
        else:
            channel = c.customer.get("preferred_channel") or "Mobile App Push"
            hour = c.customer.get("preferred_contact_hour")
            timing = f"Preferred contact hour: {hour}:00" if hour != "" and hour is not None else "Customer preference"

        out = {
            "status": "completed",
            "channel": channel,
            "timing": timing,
            "reason": "Uses customer preference unless sensitivity requires human review",
        }
        c.channel = out
        return out


class SuppressionAgent(Agent):
    name = "Suppression & Consent Agent"

    def run(self, c):
        customer = c.customer
        action = c.next_best_action.get("action")

        if bool(customer.get("marketing_opt_out")):
            reason = "OPT-OUT"
        elif bool(customer.get("cooldown_active")):
            reason = "COOLDOWN ACTIVE"
        elif action == "Human Relationship Manager":
            reason = "PROMOTIONAL MESSAGING BLOCKED"
        else:
            reason = "Eligible after suppression checks"

        suppressed = reason != "Eligible after suppression checks"
        out = {
            "status": "completed",
            "suppressed": suppressed,
            "reason": reason,
            "marketing_opt_out": bool(customer.get("marketing_opt_out")),
            "cooldown_active": bool(customer.get("cooldown_active")),
        }
        c.suppression = out
        return out


class ResponseTrackingAgent(Agent):
    name = "Response Tracking Agent"

    def run(self, c):
        return {
            "status": "completed",
            "result": "Ready to track Sent → Delivered → Opened → Clicked → Replied → Converted",
            "confidence": 1.0,
        }


class EscalationAgent(Agent):
    name = "Sensitive Escalation Agent"

    def run(self, c):
        required = (
            c.next_best_action.get("action") == "Human Relationship Manager"
            or str(c.need_inference.get("sensitivity", "")).lower() == "high"
        )
        out = {
            "status": "completed",
            "required": required,
            "priority": c.next_best_action.get("priority", "LOW"),
            "reason": "Sensitive or high-impact behavioral pattern requires human review" if required else "No human escalation required",
        }
        c.escalation = out
        return out
