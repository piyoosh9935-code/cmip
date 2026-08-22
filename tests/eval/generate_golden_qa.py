"""Deterministically generates tests/eval/golden_qa.jsonl from the synthetic data
already in Postgres: for each cohort, picks members with at least 2 notes tagged with
that cohort (so precision/recall aren't trivially 1.0 or undefined) and pairs them with
a question template. Ground truth relevance = cohort_tag match (see
llmops/mlflow/metrics.py) - not hand-labeled, but unambiguous by construction."""

import json
import os

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://cmip:cmip123@localhost:5432/cmip")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "golden_qa.jsonl")

MEMBERS_PER_COHORT = 5
MIN_NOTES_FOR_COHORT = 2

QUESTION_TEMPLATES = {
    "diabetes": "Tell me about this member's diabetes management and blood sugar control.",
    "hypertension": "How is this member's blood pressure and hypertension being managed?",
    "chf": "What is this member's heart failure status and treatment?",
    "copd": "Summarize this member's COPD symptoms and respiratory treatment.",
    "depression": "How is this member doing with their depression and mental health treatment?",
}


def pick_members(engine) -> list[dict]:
    sql = text(
        """
        select member_id, cohort_tag, count(*) as note_count
        from gold.member_notes_index
        where cohort_tag = :cohort
        group by member_id, cohort_tag
        having count(*) >= :min_notes
        order by member_id
        limit :limit
        """
    )
    rows = []
    with engine.connect() as conn:
        for cohort in QUESTION_TEMPLATES:
            result = conn.execute(
                sql, {"cohort": cohort, "min_notes": MIN_NOTES_FOR_COHORT, "limit": MEMBERS_PER_COHORT}
            )
            for row in result.mappings():
                rows.append({"member_id": row["member_id"], "cohort": cohort, "note_count": row["note_count"]})
    return rows


def main() -> None:
    engine = create_engine(DATABASE_URL)
    entries = pick_members(engine)
    with open(OUTPUT_PATH, "w") as f:
        for entry in entries:
            f.write(
                json.dumps(
                    {
                        "member_id": entry["member_id"],
                        "cohort": entry["cohort"],
                        "question": QUESTION_TEMPLATES[entry["cohort"]],
                        "expected_relevant_note_count": entry["note_count"],
                    }
                )
                + "\n"
            )
    print(f"Wrote {len(entries)} golden QA pairs -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
