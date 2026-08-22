from pydantic import BaseModel, Field

from retrieval.doc_id import get_doc_id


class GroundednessJudgement(BaseModel):
    score: float = Field(
        ge=0.0, le=1.0, description="Groundedness score from 0.0 (not grounded) to 1.0 (fully grounded)"
    )
    passed: bool = Field(description="Whether the answer is well grounded (score >= 0.7)")
    reasoning: str = Field(description="One short sentence explaining the judgement")


_GROUNDEDNESS_PROMPT = """Judge whether the answer below is fully supported by the given \
context, with no claims that go beyond it.

Context:
{context}

Answer: {answer}
"""


def make_verification_node(llm_factory):
    def verification(state: dict) -> dict:
        graded_docs = state.get("graded_docs") or []
        graded_ids = {get_doc_id(d) for d in graded_docs}
        cited_ids = set(state.get("citations") or [])

        # Cheap rule-based check first: do the cited ids actually exist in the graded
        # set? This short-circuits before the costlier LLM groundedness call below -
        # an answer citing an id we never retrieved is definitionally ungrounded.
        citations_valid = bool(cited_ids) and cited_ids.issubset(graded_ids)
        if not citations_valid:
            return {
                "groundedness_score": 0.0,
                "groundedness_passed": False,
                "trace": state.get("trace", []) + [
                    {
                        "node": "verification",
                        "detail": f"citation check failed: cited {cited_ids or '{}'} not subset of graded {graded_ids or '{}'}",
                    }
                ],
            }

        llm = llm_factory(state["routed_model"])
        structured_llm = llm.with_structured_output(GroundednessJudgement)
        context = "\n".join(d.page_content for d in graded_docs if get_doc_id(d) in cited_ids)
        judgement = structured_llm.invoke(
            _GROUNDEDNESS_PROMPT.format(context=context, answer=state.get("answer", ""))
        )

        return {
            "groundedness_score": judgement.score,
            "groundedness_passed": judgement.passed,
            "trace": state.get("trace", []) + [
                {
                    "node": "verification",
                    "detail": f"citations valid; groundedness={judgement.score:.2f} passed={judgement.passed} ({judgement.reasoning})",
                }
            ],
        }

    return verification
