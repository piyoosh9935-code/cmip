from pydantic import BaseModel, Field

from retrieval.doc_id import get_doc_id


class AnswerWithCitations(BaseModel):
    answer: str = Field(description="The answer to the question, grounded only in the given context")
    citations: list[str] = Field(
        description="The bracketed [id] tags of the context pieces actually used to compose the answer"
    )


_GENERATION_PROMPT = """Answer the question using ONLY the numbered context below. Every \
claim in your answer must be traceable to at least one piece of context. Cite the \
bracketed ids of every piece of context you relied on - do not invent ids that are not \
shown below, and do not answer from outside knowledge.

Context:
{context}

Question: {question}
"""


def clean_citation_ids(citations: list[str]) -> list[str]:
    """Small local models routinely echo the "[id]" bracket characters shown in the
    prompt's context formatting back into the citation string itself (e.g.
    "[medication:MD-...]" instead of "medication:MD-..."). Normalize once here so
    every downstream consumer (verification, the API, the UI) sees clean ids."""
    return [c.strip("[] \t") for c in citations]


def make_generation_node(llm_factory):
    def generation(state: dict) -> dict:
        docs = state.get("graded_docs") or []
        if not docs:
            return {
                "answer": "I don't have enough grounded information in this member's record to answer that.",
                "citations": [],
                "trace": state.get("trace", []) + [
                    {"node": "generation", "detail": "no graded documents available, skipped generation"}
                ],
            }

        llm = llm_factory(state["routed_model"])
        structured_llm = llm.with_structured_output(AnswerWithCitations)

        context = "\n".join(f"[{get_doc_id(d)}] {d.page_content}" for d in docs)
        result = structured_llm.invoke(_GENERATION_PROMPT.format(context=context, question=state["question"]))

        clean_citations = clean_citation_ids(result.citations)

        return {
            "answer": result.answer,
            "citations": clean_citations,
            "trace": state.get("trace", []) + [
                {"node": "generation", "detail": f"generated answer citing {len(result.citations)} source(s)"}
            ],
        }

    return generation
