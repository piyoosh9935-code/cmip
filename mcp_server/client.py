"""Thin async client used by the LangGraph agentic router path (agent_graph/router_agent.py)
to discover and call the MCP server's tools over the real streamable-http MCP protocol -
not an in-process shortcut."""

import os
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8100/mcp")


@asynccontextmanager
async def mcp_session():
    async with streamable_http_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def list_tool_names() -> list[str]:
    async with mcp_session() as session:
        result = await session.list_tools()
        return [t.name for t in result.tools]


async def call_tool(name: str, arguments: dict):
    """Returns the tool's actual return value (list/dict/scalar), not a raw text blob.

    The MCP SDK serializes a `list[dict]` return as one TextContent block *per list
    item* rather than a single JSON array, so naively joining `result.content` text
    blocks produces invalid, concatenated JSON. `structured_content` (wrapped as
    `{"result": ...}`) carries the real structured payload and is used instead."""
    async with mcp_session() as session:
        result = await session.call_tool(name, arguments)
        if result.is_error:
            message = "\n".join(b.text for b in result.content if hasattr(b, "text"))
            raise RuntimeError(f"MCP tool {name!r} failed: {message}")
        if result.structured_content is not None:
            return result.structured_content.get("result", result.structured_content)
        return "\n".join(b.text for b in result.content if hasattr(b, "text"))
