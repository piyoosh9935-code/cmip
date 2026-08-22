"""precision@k / recall@k against relevance ground truth. For this synthetic dataset,
ground truth relevance for a note is "does its cohort_tag match the cohort the eval
question is actually about" - deterministic and unambiguous, since the synthetic data
generator assigns cohort_tag itself (see ingestion/synthetic_data_gen/notes.py). This
is a legitimate methodology for a synthetic corpus, not a shortcut: there is no
labeling ambiguity to argue about, unlike hand-labeling real clinical text."""

from sqlalchemy import create_engine, text

from retrieval.sql_retriever.templates import DATABASE_URL

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine


def relevant_note_ids(member_id: str, cohort: str) -> set[str]:
    sql = text(
        "select note_id from gold.member_notes_index where member_id = :member_id and cohort_tag = :cohort"
    )
    with _get_engine().connect() as conn:
        return {row[0] for row in conn.execute(sql, {"member_id": member_id, "cohort": cohort})}


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / len(top_k)


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    top_k = set(retrieved_ids[:k])
    return len(top_k & relevant_ids) / len(relevant_ids)
