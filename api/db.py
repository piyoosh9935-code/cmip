import os

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://cmip:cmip123@localhost:5432/cmip")

_engine = None

_CREATE_TRACES_TABLE = """
CREATE TABLE IF NOT EXISTS public.pipeline_traces (
    trace_id TEXT PRIMARY KEY,
    member_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    citations JSONB,
    groundedness_score DOUBLE PRECISION,
    groundedness_passed BOOLEAN,
    retry_count INTEGER,
    low_confidence BOOLEAN,
    routed_model TEXT,
    routing_reason TEXT,
    trace JSONB,
    latency_ms DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine


def ensure_traces_table() -> None:
    with get_engine().begin() as conn:
        conn.execute(text(_CREATE_TRACES_TABLE))
