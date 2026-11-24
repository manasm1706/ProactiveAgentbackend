"""Official MCP Python client wrapper using Streamable HTTP."""
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from app.config import settings

ALLOWED_TOOLS = {
    "get_customer_profile", "get_behavioral_signals", "get_recent_transactions",
    "get_engagement_history", "get_latest_ai_decision", "get_customer_summary",
}


def _content_to_text(result):
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return json.dumps(structured, default=str)
    pieces = []
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            pieces.append(text)
    return "\n".join(pieces) or "{}"


async def discover_tools():
    """Discover tools from the running MCP server using MCP list_tools."""
    async with streamablehttp_client(settings.mcp_server_url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            return [tool for tool in result.tools if tool.name in ALLOWED_TOOLS]


async def call_customer_tool(tool_name: str, arguments: dict, selected_customer_id: str):
    """Execute a discovered MCP tool, binding access to the selected customer."""
    if tool_name not in ALLOWED_TOOLS:
        raise ValueError("Requested MCP tool is not permitted")
    safe_args = dict(arguments or {})
    # The selected customer ID comes from the trusted FastAPI route, never from model arguments.
    safe_args["customer_id"] = selected_customer_id
    async with streamablehttp_client(settings.mcp_server_url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, safe_args)
            if getattr(result, "isError", False):
                raise RuntimeError(_content_to_text(result))
            return _content_to_text(result)
