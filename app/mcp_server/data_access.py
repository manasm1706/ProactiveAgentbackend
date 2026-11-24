"""Read-only data access shared by the MCP tools and resources."""
from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.models.entities import Customer, Signal, Transaction, Engagement, AIDecision
from app.rules.engine import derive_signals


def _customer_dict(row):
    return {key: getattr(row, key) for key in [
        "customer_id", "age", "city", "occupation", "customer_segment",
        "monthly_income_inr", "preferred_channel", "preferred_contact_hour",
        "app_usage_frequency", "marketing_opt_out", "cooldown_active",
        "existing_products", "approx_account_balance_inr", "record_type"
    ]}


def _signal_dict(row):
    return {key: getattr(row, key) for key in [
        "signal_id", "customer_id", "snapshot_date", "spending_change_pct",
        "savings_contribution_change_pct", "app_login_change_pct",
        "unusual_withdrawal_flag", "detected_signal_summary", "inferred_life_event",
        "inference_confidence", "sensitivity_level", "label_status", "data_status"
    ]}


def _transaction_dict(row):
    return {key: getattr(row, key) for key in [
        "transaction_id", "customer_id", "transaction_datetime", "merchant_category",
        "merchant_label", "amount_inr", "transaction_type", "channel", "is_recurring"
    ]}


def _engagement_dict(row):
    return {key: getattr(row, key) for key in [
        "engagement_id", "customer_id", "created_at", "trigger_type",
        "recommended_next_best_action", "selected_channel", "scheduled_hour",
        "delivery_status", "suppression_reason", "opened", "clicked", "converted",
        "human_escalation_required"
    ]}


def _decision_dict(row):
    return {key: getattr(row, key) for key in [
        "customer_id", "final_status", "priority", "confidence", "action", "channel", "message", "created_at"
    ]}


def read_customer_data(customer_id: str, kind: str, limit: int = 10):
    """Return a bounded, customer-scoped view from the existing SQLite database."""
    db: Session = SessionLocal()
    try:
        customer = db.query(Customer).filter_by(customer_id=customer_id).first()
        if not customer:
            return {"error": "Customer not found", "customer_id": customer_id}
        if kind == "profile":
            return _customer_dict(customer)
        if kind == "signals":
            rows = db.query(Signal).filter_by(customer_id=customer_id).order_by(Signal.snapshot_date.desc()).limit(limit).all()
            result = []
            for row in rows:
                item = _signal_dict(row)
                item["derived_signals"] = derive_signals(item)
                result.append(item)
            return result
        if kind == "transactions":
            rows = db.query(Transaction).filter_by(customer_id=customer_id).order_by(Transaction.transaction_datetime.desc()).limit(limit).all()
            return [_transaction_dict(row) for row in rows]
        if kind == "engagements":
            rows = db.query(Engagement).filter_by(customer_id=customer_id).order_by(Engagement.created_at.desc()).limit(limit).all()
            return [_engagement_dict(row) for row in rows]
        if kind == "decision":
            row = db.query(AIDecision).filter_by(customer_id=customer_id).order_by(AIDecision.created_at.desc()).first()
            return _decision_dict(row) if row else None
        return {"error": "Unsupported data type"}
    finally:
        db.close()
