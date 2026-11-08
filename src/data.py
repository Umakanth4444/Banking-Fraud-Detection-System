from pathlib import Path
import pandas as pd
from sqlalchemy import text
from src.db import get_engine

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

def load_data(csv_path=None, replace=False):
    path = Path(csv_path) if csv_path else DATA_DIR / "banking_transactions_sample.csv"
    if not path.exists():
        candidates = list(DATA_DIR.glob("*.csv"))
        if not candidates:
            raise FileNotFoundError(f"No CSV found in {DATA_DIR}")
        path = candidates[0]
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    aliases = {
        "amount":"transaction_amount", "date":"transaction_date", "transaction_time":"transaction_date",
        "merchant":"merchant_category", "category":"merchant_category", "type":"transaction_type",
        "city":"location", "fraud":"is_fraud", "isfraud":"is_fraud", "channel":"payment_channel",
        "international":"is_international"
    }
    df = df.rename(columns={c: aliases[c] for c in df.columns if c in aliases})
    required = ["transaction_id","customer_id","transaction_amount","transaction_date",
                "merchant_category","transaction_type","location","is_fraud"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Missing CSV columns: " + ", ".join(missing) + ". See README.md.")
    for col, default in {"payment_channel":"Unknown","device_type":"Unknown","is_international":False,
                          "customer_segment":"Standard","account_age_months":12}.items():
        if col not in df.columns:
            df[col] = default
    if "home_city" not in df.columns:
        df["home_city"] = df["location"].fillna("Unknown")
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    for col in ["transaction_id","customer_id","transaction_amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[["transaction_id","customer_id","transaction_amount","transaction_date"]].isna().any().any():
        raise ValueError("Invalid or missing ID, amount, or date values in CSV.")
    def to_bool(value):
        return value if isinstance(value, bool) else str(value).strip().lower() in ("true","1","yes","y")
    df["is_fraud"] = df["is_fraud"].map(to_bool)
    df["is_international"] = df["is_international"].map(to_bool)
    customers = df[["customer_id","customer_segment","account_age_months","home_city"]].drop_duplicates("customer_id")
    transactions = df[["transaction_id","customer_id","transaction_amount","transaction_date",
        "merchant_category","transaction_type","location","payment_channel","device_type",
        "is_international","is_fraud"]].copy()
    engine = get_engine()
    with engine.begin() as conn:
        if replace:
            conn.execute(text("TRUNCATE TABLE transactions, customers CASCADE"))
        customers.to_sql("customers", conn, if_exists="append", index=False, method="multi", chunksize=1000)
        transactions.to_sql("transactions", conn, if_exists="append", index=False, method="multi", chunksize=1000)
    return len(transactions)

def read_query(query):
    with get_engine().connect() as conn:
        return pd.read_sql(text(query), conn)

def get_overview():
    query = """SELECT COUNT(*) AS total_transactions,
      COUNT(*) FILTER (WHERE is_fraud) AS fraud_transactions,
      ROUND(100.0*COUNT(*) FILTER (WHERE is_fraud)/NULLIF(COUNT(*),0),2) AS fraud_rate_pct,
      ROUND(COALESCE(SUM(transaction_amount),0),2) AS total_value,
      ROUND(COALESCE(SUM(transaction_amount) FILTER (WHERE is_fraud),0),2) AS fraud_value,
      ROUND(AVG(transaction_amount),2) AS average_amount FROM transactions"""
    return read_query(query).iloc[0].to_dict()
