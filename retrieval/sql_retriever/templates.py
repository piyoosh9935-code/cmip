"""Parameterized query templates, not text-to-SQL: a local CPU-bound Ollama model
generating raw SQL against a real schema is unreliable and a real injection risk. Query
intent is classified into this fixed set instead, each mapped to a safe, parameterized
SQLAlchemy query. See README "Why Hybrid Retrieval" for the full rationale."""

import os

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://cmip:cmip123@localhost:5432/cmip")
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine


def claims_history(member_id: str, limit: int = 10) -> list[dict]:
    sql = text(
        """
        select claim_id, service_date, diagnosis_desc, procedure_desc, paid_amount,
               provider_id, provider_name, provider_specialty
        from gold.member_claims_fact
        where member_id = :member_id
        order by service_date desc
        limit :limit
        """
    )
    with _get_engine().connect() as conn:
        return [dict(r) for r in conn.execute(sql, {"member_id": member_id, "limit": limit}).mappings()]


def medication_list(member_id: str, active_only: bool = True) -> list[dict]:
    table = "gold.member_medications_current" if active_only else "silver.ehr_medications"
    sql = text(
        f"""
        select medication_id, medication_name, start_date, end_date, status
        from {table}
        where member_id = :member_id
        order by start_date desc
        """
    )
    with _get_engine().connect() as conn:
        return [dict(r) for r in conn.execute(sql, {"member_id": member_id}).mappings()]


def recent_encounters(member_id: str, limit: int = 10) -> list[dict]:
    sql = text(
        """
        select encounter_id, encounter_date, encounter_type, reason, provider_id
        from silver.ehr_encounters
        where member_id = :member_id
        order by encounter_date desc
        limit :limit
        """
    )
    with _get_engine().connect() as conn:
        return [dict(r) for r in conn.execute(sql, {"member_id": member_id, "limit": limit}).mappings()]


def sdoh_profile(member_id: str) -> dict | None:
    sql = text(
        """
        select housing_status, food_security, transportation_access, income_bracket
        from silver.sdoh
        where member_id = :member_id
        """
    )
    with _get_engine().connect() as conn:
        row = conn.execute(sql, {"member_id": member_id}).mappings().first()
        return dict(row) if row else None


def provider_info(provider_id: str) -> dict | None:
    sql = text(
        "select provider_id, provider_name, specialty, region from silver.providers where provider_id = :provider_id"
    )
    with _get_engine().connect() as conn:
        row = conn.execute(sql, {"provider_id": provider_id}).mappings().first()
        return dict(row) if row else None


def member_summary(member_id: str) -> dict | None:
    sql = text("select * from gold.member_summary where member_id = :member_id")
    with _get_engine().connect() as conn:
        row = conn.execute(sql, {"member_id": member_id}).mappings().first()
        return dict(row) if row else None


_INTENT_KEYWORDS = {
    "medication_list": ["medication", "med ", "meds", "drug", "prescri", "insulin", "dose", "taking"],
    "claims_history": ["claim", "billed", "paid amount", "procedure", "cost of", "cpt", "icd"],
    "recent_encounters": ["encounter", "visit", "appointment", "hospital", "admission", "ed visit"],
    "sdoh_profile": ["housing", "food insecurity", "transportation", "income", "sdoh", "social determinant"],
}


def classify_intent(query: str) -> str:
    q = query.lower()
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return intent
    return "member_summary"
