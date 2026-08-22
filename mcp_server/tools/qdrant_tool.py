from retrieval.qdrant.retriever import QdrantMemberRetriever


def semantic_search_notes(member_id: str, query: str, k: int = 5) -> list[dict]:
    """Semantic (vector) search over a member's clinical notes."""
    docs = QdrantMemberRetriever(member_id=member_id, k=k).invoke(query)
    return [
        {"note_id": d.metadata.get("note_id"), "text": d.page_content, "score": d.metadata.get("score")}
        for d in docs
    ]
