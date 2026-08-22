"""The agentic MCP tool-calling path: for multi-hop questions, exposes the 5 MCP
tools to the routed model via a LangGraph ReAct agent that calls the real MCP server
over the wire (mcp_server/client.py), bounded to ~3 tool calls. This is the second of
the router agent's two paths - the first (default) path is the deterministic
ensemble-retrieval flow in state_graph.py, used for everything else. Trading a slower,
less predictable agentic loop for genuine multi-hop tool composition is only worth it
when a single ensemble retrieval call can't answer the question - see README."""

import json

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from mcp_server.client import call_tool

MAX_TOOL_CALLS = 3
# Each tool-call round trip is 2 graph super-steps (agent -> tools); +1 for the final
# agent turn with no further tool calls. This is a practical proxy for "bound to N
# tool calls", not an exact count LangGraph enforces natively.
_RECURSION_LIMIT = 2 * MAX_TOOL_CALLS + 1


async def get_member_claims(member_id: str, limit: int = 10) -> str:
    """Get a member's recent claims: diagnosis, procedure, billed amount, and provider."""
    return json.dumps(await call_tool("get_member_claims", {"member_id": member_id, "limit": limit}))


async def get_provider_info(provider_id: str) -> str:
    """Look up a provider's name, specialty, and region by provider_id."""
    return json.dumps(await call_tool("get_provider_info", {"provider_id": provider_id}))


async def run_structured_query(intent: str, member_id: str) -> str:
    """Run a structured query against a member's record. Valid intents:
    claims_history, medication_list, recent_encounters, sdoh_profile, member_summary."""
    return json.dumps(await call_tool("run_structured_query", {"intent": intent, "member_id": member_id}))


async def semantic_search_notes(member_id: str, query: str, k: int = 5) -> str:
    """Semantic (vector) search over a member's clinical notes."""
    return json.dumps(await call_tool("semantic_search_notes", {"member_id": member_id, "query": query, "k": k}))


async def lexical_search_notes(member_id: str, query: str, k: int = 5) -> str:
    """Lexical (keyword/BM25) search over a member's clinical notes."""
    return json.dumps(await call_tool("lexical_search_notes", {"member_id": member_id, "query": query, "k": k}))


MCP_TOOLS = [get_member_claims, get_provider_info, run_structured_query, semantic_search_notes, lexical_search_notes]

_SYSTEM_PROMPT = """You are answering a question about health plan member {member_id} using \
the available tools. Always pass member_id="{member_id}" to every tool call - never a \
different member. Use as few tool calls as you need (at most {max_calls}) and then give \
a final answer summarizing what you found."""


def build_agentic_app(llm):
    return create_react_agent(model=llm, tools=MCP_TOOLS)


async def run_agentic_query(question: str, member_id: str, llm) -> dict:
    app = build_agentic_app(llm)
    result = await app.ainvoke(
        {
            "messages": [
                ("system", _SYSTEM_PROMPT.format(member_id=member_id, max_calls=MAX_TOOL_CALLS)),
                ("user", question),
            ]
        },
        config={"recursion_limit": _RECURSION_LIMIT},
    )

    messages = result["messages"]
    tool_calls = [
        {"tool": m.name, "content": m.content[:200]} for m in messages if isinstance(m, ToolMessage)
    ]
    final = next((m.content for m in reversed(messages) if isinstance(m, AIMessage) and m.content), "")

    return {"answer": final, "tool_calls": tool_calls, "num_tool_calls": len(tool_calls)}
