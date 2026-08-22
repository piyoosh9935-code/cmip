"""Pure heuristics, no LLM call decides the routing - matches the resume's "heuristic
model-routing" wording exactly. Picks llama3 (default, general questions) vs mistral
(multi-hop/aggregation questions), logging a human-readable reason for the UI trace
panel and for LangSmith/MLflow."""

_MULTIHOP_KEYWORDS = [
    "compare", "trend", "over time", "correlate", "correlation", "history of",
    "across", "combine", "relationship between", "how has", "change since",
]

_SOURCE_KEYWORDS = {
    "claims": ["claim", "billed", "paid amount", "procedure", "cost of"],
    "notes": ["note", "documented", "clinician", "provider wrote", "diagnosed"],
    "sdoh": ["housing", "food insecurity", "transportation", "income", "social determinant"],
    "medication": ["medication", "drug", "prescri"],
}

LONG_QUESTION_WORD_THRESHOLD = 25
COMPLEXITY_SCORE_THRESHOLD = 2


def route(question: str, retry_count: int = 0) -> tuple[str, str]:
    """Returns (model_name, human_readable_reason)."""
    if retry_count > 0:
        return "mistral", f"escalated to mistral: this is retry #{retry_count} after a failed groundedness check"

    q = question.lower()
    score = 0
    reasons: list[str] = []

    word_count = len(question.split())
    if word_count > LONG_QUESTION_WORD_THRESHOLD:
        score += 1
        reasons.append(f"long question ({word_count} words)")

    if any(kw in q for kw in _MULTIHOP_KEYWORDS):
        score += 2
        reasons.append("multi-hop/aggregation language detected")

    sources_mentioned = [name for name, kws in _SOURCE_KEYWORDS.items() if any(kw in q for kw in kws)]
    if len(sources_mentioned) >= 2:
        score += 2
        reasons.append(f"spans multiple data sources ({', '.join(sources_mentioned)})")

    if score >= COMPLEXITY_SCORE_THRESHOLD:
        return "mistral", "; ".join(reasons)

    reason = "; ".join(reasons) + " (below complexity threshold)" if reasons else "straightforward single-source question"
    return "llama3", reason
