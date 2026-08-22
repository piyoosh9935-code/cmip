"""Fast, deterministic tests of the graph's wiring - the retry loop, model escalation,
weight reallocation, and terminal states - using the stub LLM (agent_graph/stub_llm.py)
instead of a real Ollama call. Requires live Postgres/Qdrant/BM25 index (retrieval
still runs for real - only the LLM calls are stubbed)."""

from agent_graph.nodes.generation import clean_citation_ids
from agent_graph.state_graph import run_query
from agent_graph.stub_llm import stub_llm_factory

MEMBER_ID = "M-00003"


def test_happy_path_ends_without_retry():
    result = run_query("what medications is this member taking", MEMBER_ID, stub_llm_factory())
    assert result["retry_count"] == 0
    assert result["groundedness_passed"] is True
    assert not result.get("low_confidence")
    assert result["answer"]


def test_forced_ungrounded_retries_exactly_to_the_bound_then_stops():
    result = run_query(
        "compare claims and clinical notes trends over time", MEMBER_ID,
        stub_llm_factory(force_ungrounded=True), max_retries=3,
    )
    assert result["retry_count"] == 3
    assert result["low_confidence"] is True
    assert result["groundedness_passed"] is False


def test_retry_escalates_model_to_mistral():
    result = run_query(
        "how has this member's condition changed", MEMBER_ID,
        stub_llm_factory(force_ungrounded=True), max_retries=1,
    )
    assert result["routed_model"] == "mistral"
    assert "retry" in result["routing_reason"]


def test_retry_reweights_toward_bm25_and_sql():
    result = run_query(
        "compare across all sources", MEMBER_ID, stub_llm_factory(force_ungrounded=True), max_retries=1
    )
    vector, bm25, sql = result["retrieval_weights"]
    assert bm25 > 0.3  # default bm25 weight is 0.3 - a retry should push it up
    assert vector < 0.5  # default vector weight is 0.5 - a retry should pull it down


def test_zero_max_retries_stops_immediately_on_failure():
    result = run_query(
        "compare claims and notes", MEMBER_ID, stub_llm_factory(force_ungrounded=True), max_retries=0
    )
    assert result["retry_count"] == 0
    assert result["low_confidence"] is True


def test_clean_citation_ids_strips_brackets_and_whitespace():
    assert clean_citation_ids(["[medication:MD-1]", " claim:C-1 ", "encounter:E-1"]) == [
        "medication:MD-1",
        "claim:C-1",
        "encounter:E-1",
    ]
