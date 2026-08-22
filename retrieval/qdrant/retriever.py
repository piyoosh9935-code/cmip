"""Qdrant retriever, scoped mandatorily by member_id via a payload filter - queries
never search across members."""

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import PrivateAttr
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sentence_transformers import SentenceTransformer

from .schema import COLLECTION, EMBEDDING_MODEL, QDRANT_URL

_model_cache: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model_cache
    if _model_cache is None:
        _model_cache = SentenceTransformer(EMBEDDING_MODEL)
    return _model_cache


class QdrantMemberRetriever(BaseRetriever):
    member_id: str
    k: int = 5
    _client: QdrantClient = PrivateAttr()

    def __init__(self, member_id: str, k: int = 5, **kwargs):
        super().__init__(member_id=member_id, k=k, **kwargs)
        self._client = QdrantClient(url=QDRANT_URL)

    def _get_relevant_documents(self, query: str, *, run_manager) -> list[Document]:
        vector = _get_model().encode(query, normalize_embeddings=True).tolist()
        results = self._client.query_points(
            collection_name=COLLECTION,
            query=vector,
            query_filter=Filter(
                must=[FieldCondition(key="member_id", match=MatchValue(value=self.member_id))]
            ),
            limit=self.k,
        ).points
        return [
            Document(
                page_content=point.payload["text"],
                metadata={**point.payload, "score": point.score, "source": "qdrant"},
            )
            for point in results
        ]
