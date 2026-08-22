import os
import pickle

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import PrivateAttr

from .build_index import INDEX_PATH, tokenize

_index_cache: dict | None = None


def _get_index() -> dict:
    global _index_cache
    if _index_cache is None:
        if not os.path.exists(INDEX_PATH):
            raise FileNotFoundError(
                f"BM25 index not found at {INDEX_PATH} - run `python -m retrieval.bm25.build_index` first"
            )
        with open(INDEX_PATH, "rb") as f:
            _index_cache = pickle.load(f)
    return _index_cache


class BM25MemberRetriever(BaseRetriever):
    member_id: str
    k: int = 5
    _entry: dict | None = PrivateAttr(default=None)

    def __init__(self, member_id: str, k: int = 5, **kwargs):
        super().__init__(member_id=member_id, k=k, **kwargs)
        self._entry = _get_index().get(member_id)

    def _get_relevant_documents(self, query: str, *, run_manager) -> list[Document]:
        if not self._entry:
            return []
        bm25 = self._entry["bm25"]
        notes = self._entry["notes"]
        # Per-member corpora are tiny (often 2-4 notes), so BM25's IDF term routinely
        # goes negative for a query word that appears in most of a member's notes -
        # a `score > 0` filter would silently drop good matches. Relative ranking
        # within the member's own corpus is still meaningful even when the absolute
        # score is negative, so we keep top-k unconditionally and let the ensemble's
        # RRF fusion (which only cares about rank, not raw score) handle the rest.
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        scores = bm25.get_scores(query_tokens)
        ranked = sorted(zip(scores, notes), key=lambda pair: pair[0], reverse=True)
        return [
            Document(
                page_content=note["note_text"],
                metadata={**note, "score": float(score), "source": "bm25"},
            )
            for score, note in ranked[: self.k]
        ]
