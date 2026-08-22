from retrieval.sql_retriever import templates


def get_provider_info(provider_id: str) -> dict | None:
    """Look up a provider's name, specialty, and region by provider_id."""
    return templates.provider_info(provider_id)
