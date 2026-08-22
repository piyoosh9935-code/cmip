import json
import time
import uuid

from fastapi import APIRouter
from sqlalchemy import text

from agent_graph.state_graph import build_graph
from api.db import get_engine
from api.schemas import QueryRequest, QueryResponse
from llmops.mlflow.experiment import log_query_run
from model_routing.ollama_client import get_chat_model

router = APIRouter()

# Compiled once at import time (module-level), reused across requests - not rebuilt
# per call. llm_factory is called per-node with the routed model name, so a single
# compiled graph still supports dynamic per-query/per-retry model routing.
_app = build_graph(get_chat_model)

_INSERT_TRACE = text(
    """
    INSERT INTO public.pipeline_traces
        (trace_id, member_id, question, answer, citations, groundedness_score,
         groundedness_passed, retry_count, low_confidence, routed_model,
         routing_reason, trace, latency_ms)
    VALUES
        (:trace_id, :member_id, :question, :answer, :citations, :groundedness_score,
         :groundedness_passed, :retry_count, :low_confidence, :routed_model,
         :routing_reason, :trace, :latency_ms)
    """
)


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    t0 = time.time()
    result = _app.invoke(
        {
            "question": request.question,
            "member_id": request.member_id,
            "retry_count": 0,
            "max_retries": request.max_retries,
            "trace": [],
        }
    )
    latency_ms = (time.time() - t0) * 1000

    trace_id = str(uuid.uuid4())
    with get_engine().begin() as conn:
        conn.execute(
            _INSERT_TRACE,
            {
                "trace_id": trace_id,
                "member_id": request.member_id,
                "question": request.question,
                "answer": result.get("answer"),
                "citations": json.dumps(result.get("citations") or []),
                "groundedness_score": result.get("groundedness_score"),
                "groundedness_passed": result.get("groundedness_passed"),
                "retry_count": result.get("retry_count", 0),
                "low_confidence": bool(result.get("low_confidence", False)),
                "routed_model": result.get("routed_model"),
                "routing_reason": result.get("routing_reason"),
                "trace": json.dumps(result.get("trace") or []),
                "latency_ms": latency_ms,
            },
        )

    log_query_run(question=request.question, member_id=request.member_id, result=result, latency_ms=latency_ms)

    return QueryResponse(
        trace_id=trace_id,
        answer=result.get("answer") or "",
        citations=result.get("citations") or [],
        groundedness_score=result.get("groundedness_score", 0.0),
        groundedness_passed=bool(result.get("groundedness_passed", False)),
        retry_count=result.get("retry_count", 0),
        low_confidence=bool(result.get("low_confidence", False)),
        routed_model=result.get("routed_model", ""),
        routing_reason=result.get("routing_reason", ""),
        latency_ms=latency_ms,
    )
