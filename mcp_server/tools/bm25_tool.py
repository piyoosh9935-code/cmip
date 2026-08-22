from retrieval.bm25.retriever import BM25MemberRetriever


def lexical_search_notes(member_id: str, query: str, k: int = 5) -> list[dict]:
    """Lexical (keyword/BM25) search over a member's clinical notes."""
    docs = BM25MemberRetriever(member_id=member_id, k=k).invoke(query)
    return [
        {"note_id": d.metadata.get("note_id"), "text": d.page_content, "score": d.metadata.get("score")}
        for d in docs
    ]
