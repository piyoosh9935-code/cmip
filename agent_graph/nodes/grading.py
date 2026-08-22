from pydantic import BaseModel, Field


class GradeDecision(BaseModel):
    relevant: bool = Field(description="Whether this document is relevant to answering the question")
    reasoning: str = Field(description="One short sentence explaining the decision")


_GRADE_PROMPT = """You are grading whether a retrieved document is relevant to a question \
about a specific health plan member. Answer strictly based on whether the document \
would help answer the question - not whether it is well-written.

Question: {question}

Document:
{document}
"""


def make_grading_node(llm_factory):
    def grading(state: dict) -> dict:
        llm = llm_factory(state["routed_model"])
        structured_llm = llm.with_structured_output(GradeDecision)

        graded = []
        decisions = []
        for doc in state["retrieved_docs"]:
            decision = structured_llm.invoke(
                _GRADE_PROMPT.format(question=state["question"], document=doc.page_content)
            )
            decisions.append(decision.relevant)
            if decision.relevant:
                graded.append(doc)

        return {
            "graded_docs": graded,
            "trace": state.get("trace", []) + [
                {
                    "node": "grading",
                    "detail": f"{len(graded)}/{len(state['retrieved_docs'])} documents kept relevant",
                }
            ],
        }

    return grading
