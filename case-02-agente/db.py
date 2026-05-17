import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("Variável POSTGRES_URL ou DATABASE_URL não definida no .env")
        _engine = create_engine(url)
    return _engine


def execute_query(sql: str) -> pd.DataFrame:
    stripped = sql.strip().upper()
    if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
        raise ValueError("Apenas queries SELECT/WITH são permitidas.")
    with _get_engine().connect() as conn:
        return pd.read_sql_query(text(sql), conn)
