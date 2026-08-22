from fastapi import APIRouter
from mlflow.tracking import MlflowClient

from api.schemas import EvalSummaryResponse
from llmops.mlflow.experiment import EXPERIMENT_NAME, MLFLOW_TRACKING_URI

router = APIRouter()


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


@router.get("/eval/summary", response_model=EvalSummaryResponse)
def eval_summary(limit: int = 100) -> EvalSummaryResponse:
    client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        return EvalSummaryResponse(
            num_query_runs=0, avg_groundedness=None, avg_latency_ms=None,
            num_eval_runs=0, avg_precision_at_5=None, avg_recall_at_5=None,
        )

    runs = client.search_runs([experiment.experiment_id], max_results=limit, order_by=["start_time DESC"])

    query_runs = [r for r in runs if "groundedness_score" in r.data.metrics]
    eval_runs = [r for r in runs if "precision_at_5" in r.data.metrics]

    return EvalSummaryResponse(
        num_query_runs=len(query_runs),
        avg_groundedness=_avg([r.data.metrics["groundedness_score"] for r in query_runs]),
        avg_latency_ms=_avg([r.data.metrics["latency_ms"] for r in query_runs]),
        num_eval_runs=len(eval_runs),
        avg_precision_at_5=_avg([r.data.metrics["precision_at_5"] for r in eval_runs]),
        avg_recall_at_5=_avg([r.data.metrics["recall_at_5"] for r in eval_runs]),
    )
