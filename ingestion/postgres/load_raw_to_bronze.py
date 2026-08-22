"""Loads each `<table>_batch<N>.csv` file in ingestion/bronze_silver_gold/raw/ into
bronze.<table>, append-only. Idempotent: a bronze._loaded_files bookkeeping table
tracks which files have already been loaded, so re-running only picks up new batches -
this is what makes the "incremental loading" claim real and testable, not simulated."""

import glob
import os
import re

import pandas as pd
from sqlalchemy import create_engine, text

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "bronze_silver_gold", "raw")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://cmip:cmip123@localhost:5432/cmip")

_FILENAME_RE = re.compile(r"^(?P<table>[a-z_]+)_batch(?P<batch>\d+)\.csv$")


def _ensure_bookkeeping(engine):
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS bronze"))
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS bronze._loaded_files (
                    filename TEXT PRIMARY KEY,
                    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )


def _already_loaded(engine, filename: str) -> bool:
    with engine.connect() as conn:
        return (
            conn.execute(
                text("SELECT 1 FROM bronze._loaded_files WHERE filename = :f"), {"f": filename}
            ).first()
            is not None
        )


def _mark_loaded(engine, filename: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO bronze._loaded_files (filename) VALUES (:f) ON CONFLICT DO NOTHING"),
            {"f": filename},
        )


def load_file(engine, path: str) -> None:
    filename = os.path.basename(path)
    match = _FILENAME_RE.match(filename)
    if not match:
        return
    if _already_loaded(engine, filename):
        print(f"  skip   {filename} (already loaded)")
        return
    table = match.group("table")
    df = pd.read_csv(path)
    df.to_sql(table, engine, schema="bronze", if_exists="append", index=False)
    _mark_loaded(engine, filename)
    print(f"  loaded {filename} -> bronze.{table} ({len(df)} rows)")


def main() -> None:
    engine = create_engine(DATABASE_URL)
    _ensure_bookkeeping(engine)
    files = sorted(glob.glob(os.path.join(RAW_DIR, "*_batch*.csv")))
    if not files:
        print(f"No raw CSVs found in {RAW_DIR} - run the synthetic data generator first.")
        return
    for path in files:
        load_file(engine, path)


if __name__ == "__main__":
    main()
