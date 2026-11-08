import os
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def get_engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        user = os.getenv("DB_USER", "postgres")
        password = quote_plus(os.getenv("DB_PASSWORD", ""))
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        database = os.getenv("DB_NAME", "banking_fraud")
        url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url, pool_pre_ping=True)

def test_connection():
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT version()")).scalar()
