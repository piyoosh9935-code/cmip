from retrieval.sql_retriever import templates


def get_member_claims(member_id: str, limit: int = 10) -> list[dict]:
    """Get a member's recent claims: diagnosis, procedure, billed amount, and provider."""
    return templates.claims_history(member_id, limit=limit)
