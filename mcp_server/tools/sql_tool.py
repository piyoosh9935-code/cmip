from retrieval.sql_retriever import templates

_INTENTS = {
    "claims_history": templates.claims_history,
    "medication_list": templates.medication_list,
    "recent_encounters": templates.recent_encounters,
    "sdoh_profile": templates.sdoh_profile,
    "member_summary": templates.member_summary,
}


def run_structured_query(intent: str, member_id: str) -> list[dict] | dict | None:
    """Run a structured query against a member's record. Valid intents:
    claims_history, medication_list, recent_encounters, sdoh_profile, member_summary."""
    fn = _INTENTS.get(intent)
    if fn is None:
        raise ValueError(f"unknown intent {intent!r}, expected one of {sorted(_INTENTS)}")
    return fn(member_id)
