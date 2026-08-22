import os

import mlflow

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5001")
EXPERIMENT_NAME = os.environ.get("MLFLOW_EXPERIMENT_NAME", "cmip_rag_pipeline")

_configured = False


def ensure_configured() -> None:
    global _configured
    if not _configured:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(EXPERIMENT_NAME)
        _configured = True


def log_query_run(
    *,
    question: str,
    member_id: str,
    result: dict,
    latency_ms: float,
    precision: float | None = None,
    recall: float | None = None,
    k: int | None = None,
) -> None:
    """One MLflow run per pipeline query. `result` is the dict returned by
    agent_graph.state_graph.run_query."""
    ensure_configured()
    with mlflow.start_run():
        mlflow.log_param("question", question)
        mlflow.log_param("member_id", member_id)
        mlflow.log_param("routed_model", result.get("routed_model"))
        mlflow.log_param("routing_reason", result.get("routing_reason"))
        mlflow.log_param("retrieval_weights", result.get("retrieval_weights"))

        mlflow.log_metric("retry_count", result.get("retry_count", 0))
        mlflow.log_metric("groundedness_score", result.get("groundedness_score", 0.0))
        mlflow.log_metric("citation_count", len(result.get("citations") or []))
        mlflow.log_metric("low_confidence", int(bool(result.get("low_confidence"))))
        mlflow.log_metric("latency_ms", latency_ms)
        if precision is not None:
            mlflow.log_metric(f"precision_at_{k}", precision)
        if recall is not None:
            mlflow.log_metric(f"recall_at_{k}", recall)

        mlflow.log_dict({"trace": result.get("trace", [])}, "trace.json")
