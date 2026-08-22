"""Deterministic stand-in for a LangChain chat model - just enough surface area
(.invoke, .with_structured_output) for the graph's nodes to run against, so the
StateGraph's wiring (edges, the bounded retry loop) can be validated fast and
deterministically before ever calling a real Ollama model. See CHALLENGES.md."""

import re


class _StubMessage:
    def __init__(self, content: str):
        self.content = content


class _StructuredStub:
    def __init__(self, resolver):
        self._resolver = resolver

    def invoke(self, prompt):
        return self._resolver(prompt if isinstance(prompt, str) else str(prompt))


class StubChatModel:
    def __init__(self, force_ungrounded: bool = False):
        self.force_ungrounded = force_ungrounded

    def invoke(self, prompt):
        text = prompt if isinstance(prompt, str) else str(prompt)
        return _StubMessage(f"stub rewritten query based on: {text[:80]}")

    def with_structured_output(self, schema):
        def resolver(prompt_text: str):
            name = schema.__name__
            if name == "GradeDecision":
                return schema(relevant=True, reasoning="stub: always relevant")
            if name == "AnswerWithCitations":
                ids = re.findall(r"\[([^\]]+)\]", prompt_text)
                answer = "Stub answer synthesized from retrieved context." if ids else "No grounded context available."
                return schema(answer=answer, citations=ids)
            if name == "GroundednessJudgement":
                if self.force_ungrounded:
                    return schema(score=0.2, passed=False, reasoning="stub: forced ungrounded to exercise the retry loop")
                return schema(score=0.92, passed=True, reasoning="stub: passes")
            raise ValueError(f"StubChatModel has no behavior defined for schema {name}")

        return _StructuredStub(resolver)


def stub_llm_factory(force_ungrounded: bool = False):
    def factory(model_name: str) -> StubChatModel:
        return StubChatModel(force_ungrounded=force_ungrounded)

    return factory
