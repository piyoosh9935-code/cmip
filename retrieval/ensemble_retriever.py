"""Combines Qdrant (semantic), BM25 (lexical), and SQL (structured) retrieval via
LangChain's EnsembleRetriever, fused with weighted reciprocal rank fusion:
    score = sum(weight_i / (c + rank_i))  for each retriever i, default c=60.
Every leg is scoped to a single member_id - see README "Why Hybrid Retrieval"."""

from langchain_classic.retrievers.ensemble import EnsembleRetriever

from .bm25.retriever import BM25MemberRetriever
from .qdrant.retriever import QdrantMemberRetriever
from .sql_retriever.retriever import SQLMemberRetriever

# vector / bm25 / sql - overridable by the Corrective-RAG retry loop (Phase 3)
DEFAULT_WEIGHTS = [0.5, 0.3, 0.2]


def build_ensemble_retriever(
    member_id: str, k: int = 5, weights: list[float] | None = None
) -> EnsembleRetriever:
    retrievers = [
        QdrantMemberRetriever(member_id=member_id, k=k),
        BM25MemberRetriever(member_id=member_id, k=k),
        SQLMemberRetriever(member_id=member_id, k=k),
    ]
    return EnsembleRetriever(retrievers=retrievers, weights=weights or DEFAULT_WEIGHTS)
