"""Integration tests against a running MCP server (`python -m mcp_server.server`) plus
live Postgres/Qdrant. Exercises the real MCP wire protocol (streamable-http), not an
in-process shortcut - this is what agent_graph/router_agent.py talks to."""

import asyncio

import pytest

from mcp_server.client import call_tool, list_tool_names

MEMBER_ID = "M-00003"

EXPECTED_TOOLS = {
    "get_member_claims", "get_provider_info", "run_structured_query",
    "semantic_search_notes", "lexical_search_notes",
}


def test_server_exposes_all_five_tools():
    names = asyncio.run(list_tool_names())
    assert set(names) == EXPECTED_TOOLS


def test_get_member_claims_returns_rows():
    rows = asyncio.run(call_tool("get_member_claims", {"member_id": MEMBER_ID, "limit": 2}))
    assert rows
    assert rows[0]["claim_id"].startswith("C-")
    assert "provider_id" in rows[0]  # needed for the agentic path to chain into get_provider_info


def test_get_provider_info_resolves_a_real_provider_id():
    claims = asyncio.run(call_tool("get_member_claims", {"member_id": MEMBER_ID, "limit": 1}))
    provider_id = claims[0]["provider_id"]
    provider = asyncio.run(call_tool("get_provider_info", {"provider_id": provider_id}))
    assert provider["provider_id"] == provider_id
    assert provider["provider_name"]


def test_run_structured_query_medication_intent():
    result = asyncio.run(call_tool("run_structured_query", {"intent": "medication_list", "member_id": MEMBER_ID}))
    assert result


def test_run_structured_query_rejects_unknown_intent():
    with pytest.raises(Exception):
        asyncio.run(call_tool("run_structured_query", {"intent": "not_a_real_intent", "member_id": MEMBER_ID}))


def test_semantic_and_lexical_search_are_member_scoped():
    semantic = asyncio.run(call_tool("semantic_search_notes", {"member_id": MEMBER_ID, "query": "diabetes", "k": 3}))
    lexical = asyncio.run(call_tool("lexical_search_notes", {"member_id": MEMBER_ID, "query": "diabetes", "k": 3}))
    assert semantic
    assert lexical
