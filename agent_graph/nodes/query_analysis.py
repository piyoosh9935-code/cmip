from model_routing.heuristic_router import route
from retrieval.ensemble_retriever import DEFAULT_WEIGHTS
from retrieval.sql_retriever.templates import classify_intent


def query_analysis(state: dict) -> dict:
    question = state["question"]
    retry_count = state.get("retry_count", 0)

    intent = classify_intent(question)
    model, reason = route(question, retry_count=retry_count)

    return {
        "query_intent": intent,
        "retrieval_weights": state.get("retrieval_weights") or list(DEFAULT_WEIGHTS),
        "retry_count": retry_count,
        "max_retries": state.get("max_retries", 3),
        "routed_model": model,
        "routing_reason": reason,
        "trace": state.get("trace", []) + [
            {"node": "query_analysis", "detail": f"intent={intent}, model={model} ({reason})"}
        ],
    }
