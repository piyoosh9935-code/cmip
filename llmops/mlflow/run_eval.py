"""Runs tests/eval/golden_qa.jsonl through the hybrid retriever (not the full LangGraph
pipeline - this evaluates retrieval quality specifically, matching the resume's
"retrieval evaluation metrics (precision@k, recall@k)" wording), logs one MLflow run
per question, and prints summary averages."""

import json
import os
import time

from retrieval.doc_id import get_doc_id
from retrieval.ensemble_retriever import build_ensemble_retriever

from .experiment import ensure_configured
from .metrics import precision_at_k, recall_at_k, relevant_note_ids

import mlflow

GOLDEN_QA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "eval", "golden_qa.jsonl")
K = 5


def load_golden_qa() -> list[dict]:
    with open(GOLDEN_QA_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def evaluate_one(entry: dict) -> dict:
    retriever = build_ensemble_retriever(entry["member_id"], k=K)

    t0 = time.time()
    docs = retriever.invoke(entry["question"])
    latency_ms = (time.time() - t0) * 1000

    # ground truth is over notes specifically - filter the ensemble's mixed results
    # (which may include SQL rows) down to the note-retrieving legs
    note_doc_ids = [get_doc_id(d) for d in docs if d.metadata.get("source") in ("qdrant", "bm25")]
    relevant_ids = relevant_note_ids(entry["member_id"], entry["cohort"])
    # doc ids from Qdrant carry a ":chunk_index" suffix; note ids from ground truth don't
    normalized_ids = [doc_id.split(":")[0] for doc_id in note_doc_ids]

    return {
        "precision": precision_at_k(normalized_ids, relevant_ids, K),
        "recall": recall_at_k(normalized_ids, relevant_ids, K),
        "latency_ms": latency_ms,
        "num_retrieved": len(docs),
    }


def main() -> None:
    ensure_configured()
    entries = load_golden_qa()
    results = []

    for entry in entries:
        metrics = evaluate_one(entry)
        results.append(metrics)
        with mlflow.start_run(run_name=f"eval:{entry['member_id']}:{entry['cohort']}"):
            mlflow.log_param("member_id", entry["member_id"])
            mlflow.log_param("cohort", entry["cohort"])
            mlflow.log_param("question", entry["question"])
            mlflow.log_metric(f"precision_at_{K}", metrics["precision"])
            mlflow.log_metric(f"recall_at_{K}", metrics["recall"])
            mlflow.log_metric("latency_ms", metrics["latency_ms"])
        print(
            f"  {entry['member_id']} ({entry['cohort']}): "
            f"precision@{K}={metrics['precision']:.2f} recall@{K}={metrics['recall']:.2f} "
            f"latency={metrics['latency_ms']:.0f}ms"
        )

    avg_precision = sum(r["precision"] for r in results) / len(results)
    avg_recall = sum(r["recall"] for r in results) / len(results)
    avg_latency = sum(r["latency_ms"] for r in results) / len(results)
    print(f"\n{len(results)} questions evaluated")
    print(f"avg precision@{K}: {avg_precision:.3f}")
    print(f"avg recall@{K}:    {avg_recall:.3f}")
    print(f"avg latency:       {avg_latency:.0f}ms")


if __name__ == "__main__":
    main()
