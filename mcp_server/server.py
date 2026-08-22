"""MCP tool server standardizing access to claims, provider, SQL, Qdrant, and BM25
retrieval for any MCP-speaking client - including the LangGraph agentic router path
(agent_graph/router_agent.py) via mcp_server/client.py."""

import os

from mcp.server.mcpserver import MCPServer

from .tools.bm25_tool import lexical_search_notes
from .tools.claims_tool import get_member_claims
from .tools.provider_tool import get_provider_info
from .tools.qdrant_tool import semantic_search_notes
from .tools.sql_tool import run_structured_query

MCP_HOST = os.environ.get("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.environ.get("MCP_PORT", "8100"))

mcp = MCPServer(
    "cmip-mcp",
    version="0.1.0",
    instructions=(
        "Tools for querying a single health plan member's claims, EHR, clinical notes, "
        "provider directory, and SDoH data. Every tool that takes a member_id only "
        "returns data for that member."
    ),
)

mcp.tool()(get_member_claims)
mcp.tool()(get_provider_info)
mcp.tool()(run_structured_query)
mcp.tool()(semantic_search_notes)
mcp.tool()(lexical_search_notes)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host=MCP_HOST, port=MCP_PORT)
