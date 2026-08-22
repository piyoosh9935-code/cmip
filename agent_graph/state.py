from typing import TypedDict

from langchain_core.documents import Document


class TraceEvent(TypedDict):
    node: str
    detail: str


class PipelineState(TypedDict, total=False):
    question: str
    member_id: str

    query_intent: str
    rewritten_query: str | None
    retrieval_weights: list[float]

    retrieved_docs: list[Document]
    graded_docs: list[Document]

    answer: str | None
    citations: list[str]

    groundedness_score: float
    groundedness_passed: bool

    retry_count: int
    max_retries: int
    low_confidence: bool

    routed_model: str
    routing_reason: str

    trace: list[TraceEvent]
