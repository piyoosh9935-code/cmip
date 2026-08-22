from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from api.db import get_engine
from api.schemas import TraceResponse

router = APIRouter()

_SELECT_TRACE = text("select * from public.pipeline_traces where trace_id = :trace_id")


@router.get("/trace/{trace_id}", response_model=TraceResponse)
def get_trace(trace_id: str) -> TraceResponse:
    with get_engine().connect() as conn:
        row = conn.execute(_SELECT_TRACE, {"trace_id": trace_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"trace {trace_id!r} not found")

    data = dict(row)
    data["created_at"] = str(data["created_at"])
    return TraceResponse(**data)
