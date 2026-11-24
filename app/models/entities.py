from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from app.database.db import Base

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    customer_id = Column(String, unique=True, index=True)
    age = Column(Integer)
    city = Column(String)
    occupation = Column(String)
    customer_segment = Column(String)
    monthly_income_inr = Column(Float)
    preferred_channel = Column(String)
    preferred_contact_hour = Column(Integer)
    app_usage_frequency = Column(String)
    marketing_opt_out = Column(Boolean, default=False)
    cooldown_active = Column(Boolean, default=False)
    existing_products = Column(Text)
    approx_account_balance_inr = Column(Float)
    record_type = Column(String, default="SYNTHETIC")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String, index=True)
    customer_id = Column(String, index=True)
    transaction_datetime = Column(String)
    merchant_category = Column(String)
    merchant_label = Column(String)
    amount_inr = Column(Float)
    transaction_type = Column(String)
    channel = Column(String)
    is_recurring = Column(Boolean)
    data_status = Column(String)

class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True)
    signal_id = Column(String, index=True)
    customer_id = Column(String, index=True)
    snapshot_date = Column(String)
    spending_change_pct = Column(Float)
    savings_contribution_change_pct = Column(Float)
    app_login_change_pct = Column(Float)
    unusual_withdrawal_flag = Column(Boolean)
    detected_signal_summary = Column(Text)
    inferred_life_event = Column(Text)
    inference_confidence = Column(Float)
    sensitivity_level = Column(String)
    label_status = Column(Text)
    data_status = Column(String)

class Engagement(Base):
    __tablename__ = "engagement_history"
    id = Column(Integer, primary_key=True)
    engagement_id = Column(String, index=True)
    customer_id = Column(String, index=True)
    created_at = Column(String)
    trigger_type = Column(String)
    recommended_next_best_action = Column(Text)
    selected_channel = Column(String)
    scheduled_hour = Column(Integer)
    delivery_status = Column(String)
    suppression_reason = Column(Text)
    opened = Column(Boolean)
    clicked = Column(Boolean)
    converted = Column(Boolean)
    human_escalation_required = Column(Boolean)
    data_status = Column(String)

class AIDecision(Base):
    __tablename__ = "ai_decisions"
    id = Column(Integer, primary_key=True)
    customer_id = Column(String, index=True)
    final_status = Column(String)
    priority = Column(String)
    confidence = Column(Float)
    action = Column(String)
    channel = Column(String)
    message = Column(Text)
    created_at = Column(DateTime)

class Escalation(Base):
    __tablename__ = "escalations"
    id = Column(Integer, primary_key=True)
    case_id = Column(String, unique=True)
    customer_id = Column(String)
    priority = Column(String)
    reason = Column(Text)
    confidence = Column(Float)
    assigned_to = Column(String)
    status = Column(String, default="Open")
    created_at = Column(DateTime)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    customer_id = Column(String)
    signal = Column(String)
    agent = Column(String)
    decision = Column(String)
    confidence = Column(Float)
    channel = Column(String)
    suppression_reason = Column(Text)
    escalation = Column(Boolean)
    final_action = Column(String)
