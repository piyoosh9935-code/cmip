"""Builds a per-member BM25Okapi index over gold.member_notes_index and pickles the
whole set to disk. LangChain's built-in BM25Retriever holds one global in-memory
corpus with no native per-member filtering - we build separate per-member sub-indexes
instead, since every retrieval call in CMIP is scoped by member_id (see README)."""

import os
import pickle
import re

from rank_bm25 import BM25Okapi
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://cmip:cmip123@localhost:5432/cmip")
INDEX_PATH = os.path.join(os.path.dirname(__file__), "index", "bm25_index.pkl")

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text_: str) -> list[str]:
    return _TOKEN_RE.findall(text_.lower())


def _fetch_notes() -> list[dict]:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                select note_id, member_id, note_type, note_date, note_text, cohort_tag,
                       provider_id, provider_name, provider_specialty
                from gold.member_notes_index
                """
            )
        ).mappings().all()
    return [dict(r) for r in rows]


def build() -> dict:
    notes = _fetch_notes()
    by_member: dict[str, list[dict]] = {}
    for note in notes:
        by_member.setdefault(note["member_id"], []).append(note)

    index: dict[str, dict] = {}
    for member_id, member_notes in by_member.items():
        corpus = [tokenize(n["note_text"]) for n in member_notes]
        index[member_id] = {
            "bm25": BM25Okapi(corpus),
            "notes": member_notes,
        }
    return index


def main() -> None:
    index = build()
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    with open(INDEX_PATH, "wb") as f:
        pickle.dump(index, f)
    total_notes = sum(len(v["notes"]) for v in index.values())
    print(f"Built BM25 sub-indexes for {len(index)} members ({total_notes} notes) -> {INDEX_PATH}")


if __name__ == "__main__":
    main()
