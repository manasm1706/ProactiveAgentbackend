import os
import pandas as pd
from sqlalchemy.orm import Session
from app.database.db import Base, engine, SessionLocal
from app.models.entities import Customer, Transaction, Signal, Engagement

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/PS22_dataset.xlsx"))


def _records(df, columns):
    for _, row in df.iterrows():
        yield {column: row.get(column) for column in columns}


def init_db():
    """Create the database and import the supplied dataset exactly once.

    There are intentionally no hard-coded demo customers. Every customer visible
    in the application comes from the workbook in /data/PS22_dataset.xlsx.
    """
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        if db.query(Customer).count() > 0:
            return
        if not os.path.exists(DATA_PATH):
            raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

        customers = pd.read_excel(DATA_PATH, sheet_name="Customers").fillna("")
        transactions = pd.read_excel(DATA_PATH, sheet_name="Transactions").fillna("")
        signals = pd.read_excel(DATA_PATH, sheet_name="Behavioral_Signals").fillna("")
        engagements = pd.read_excel(DATA_PATH, sheet_name="Engagement_History").fillna("")

        customer_columns = [
            "customer_id", "age", "city", "occupation", "customer_segment",
            "monthly_income_inr", "preferred_channel", "preferred_contact_hour",
            "app_usage_frequency", "marketing_opt_out", "existing_products",
            "approx_account_balance_inr", "record_type",
        ]
        transaction_columns = [
            "transaction_id", "customer_id", "transaction_datetime",
            "merchant_category", "merchant_label", "amount_inr", "transaction_type",
            "channel", "is_recurring", "data_status",
        ]
        signal_columns = [
            "signal_id", "customer_id", "snapshot_date", "spending_change_pct",
            "savings_contribution_change_pct", "app_login_change_pct",
            "unusual_withdrawal_flag", "detected_signal_summary", "inferred_life_event",
            "inference_confidence", "sensitivity_level", "label_status", "data_status",
        ]
        engagement_columns = [
            "engagement_id", "customer_id", "created_at", "trigger_type",
            "recommended_next_best_action", "selected_channel", "scheduled_hour",
            "delivery_status", "suppression_reason", "opened", "clicked", "converted",
            "human_escalation_required", "data_status",
        ]

        db.bulk_insert_mappings(Customer, list(_records(customers, customer_columns)))
        db.bulk_insert_mappings(Transaction, list(_records(transactions, transaction_columns)))
        db.bulk_insert_mappings(Signal, list(_records(signals, signal_columns)))
        db.bulk_insert_mappings(Engagement, list(_records(engagements, engagement_columns)))
        db.commit()
    finally:
        db.close()
