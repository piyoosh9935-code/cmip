from pydantic import BaseModel


class QueryRequest(BaseModel):
    member_id: str
    question: str
    max_retries: int = 3


class QueryResponse(BaseModel):
    trace_id: str
    answer: str
    citations: list[str]
    groundedness_score: float
    groundedness_passed: bool
    retry_count: int
    low_confidence: bool
    routed_model: str
    routing_reason: str
    latency_ms: float


class TraceResponse(BaseModel):
    trace_id: str
    member_id: str
    question: str
    answer: str | None
    citations: list[str] | None
    groundedness_score: float | None
    groundedness_passed: bool | None
    retry_count: int | None
    low_confidence: bool | None
    routed_model: str | None
    routing_reason: str | None
    trace: list[dict] | None
    latency_ms: float | None
    created_at: str


class MemberListItem(BaseModel):
    member_id: str
    first_name: str
    last_name: str
    age: int
    plan_type: str
    cohorts: str | None


class MemberDetail(BaseModel):
    summary: dict
    recent_claims: list[dict]
    medications: list[dict]
    recent_encounters: list[dict]
    sdoh: dict | None


class HealthResponse(BaseModel):
    status: str
    postgres: bool
    qdrant: bool
    ollama: dict[str, bool]
    mcp_server: bool


class EvalSummaryResponse(BaseModel):
    num_query_runs: int
    avg_groundedness: float | None
    avg_latency_ms: float | None
    num_eval_runs: int
    avg_precision_at_5: float | None
    avg_recall_at_5: float | None
