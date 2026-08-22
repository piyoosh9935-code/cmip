"""The Self-RAG / Corrective-RAG retry loop: if verification fails, rewrite the query,
reweight the retrievers toward whichever leg is likely underserved, escalate the routed
model, and loop back to retrieval - bounded at state["max_retries"] (3 by default, per
the resume wording)."""

from model_routing.heuristic_router import route

_REWRITE_PROMPT = """The following question did not retrieve well-grounded evidence from \
a member's health record on the first attempt. Rewrite it to be more specific and more \
likely to match clinical documentation, claims, or structured fields (keep it a single \
question, do not add commentary).

Original question: {question}
"""


def route_after_verification(state: dict) -> str:
    if state.get("groundedness_passed"):
        return "end"
    if state.get("retry_count", 0) >= state.get("max_retries", 3):
        return "end_low_confidence"
    return "retry"


def _reweight(weights: list[float]) -> list[float]:
    # verification failed - shift weight away from vector search and toward the more
    # literal BM25/SQL legs, on the theory that a semantic miss is more likely than a
    # keyword or structured-data miss for narrowly-scoped clinical questions
    vector, bm25, sql = weights
    new = [max(0.1, vector - 0.15), min(0.6, bm25 + 0.10), min(0.6, sql + 0.05)]
    total = sum(new)
    return [w / total for w in new]


def make_prepare_retry_node(llm_factory):
    def prepare_retry(state: dict) -> dict:
        new_retry_count = state.get("retry_count", 0) + 1
        model, reason = route(state["question"], retry_count=new_retry_count)

        llm = llm_factory(model)
        rewritten = llm.invoke(_REWRITE_PROMPT.format(question=state["question"])).content

        new_weights = _reweight(state.get("retrieval_weights") or [0.5, 0.3, 0.2])

        return {
            "retry_count": new_retry_count,
            "rewritten_query": rewritten,
            "retrieval_weights": new_weights,
            "routed_model": model,
            "routing_reason": reason,
            "trace": state.get("trace", []) + [
                {
                    "node": "prepare_retry",
                    "detail": f"retry #{new_retry_count}: rewrote query, weights->{[round(w, 2) for w in new_weights]}, model={model} ({reason})",
                }
            ],
        }

    return prepare_retry
