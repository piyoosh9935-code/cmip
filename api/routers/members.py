from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from api.db import get_engine
from api.schemas import MemberDetail, MemberListItem
from retrieval.sql_retriever import templates

router = APIRouter()


@router.get("/members", response_model=list[MemberListItem])
def list_members(limit: int = 50, cohort: str | None = None):
    sql = "select member_id, first_name, last_name, age, plan_type, cohorts from gold.member_summary"
    params: dict = {"limit": limit}
    if cohort:
        sql += " where cohorts like :cohort_pattern"
        params["cohort_pattern"] = f"%{cohort}%"
    sql += " order by member_id limit :limit"

    with get_engine().connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


@router.get("/members/{member_id}", response_model=MemberDetail)
def get_member(member_id: str):
    summary = templates.member_summary(member_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"member {member_id!r} not found")

    return MemberDetail(
        summary=summary,
        recent_claims=templates.claims_history(member_id, limit=10),
        medications=templates.medication_list(member_id),
        recent_encounters=templates.recent_encounters(member_id, limit=10),
        sdoh=templates.sdoh_profile(member_id),
    )
