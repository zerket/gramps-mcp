"""Register all MCP tools from individual modules."""

from mcp.server.fastmcp import FastMCP

from gramps_mcp.tools.search import register_search_tools
from gramps_mcp.tools.create import register_create_tools
from gramps_mcp.tools.read import register_read_tools
from gramps_mcp.tools.update import register_update_tools
from gramps_mcp.tools.delete import register_delete_tools
from gramps_mcp.tools.convenience import register_convenience_tools
from gramps_mcp.tools.analysis import register_analysis_tools
from gramps_mcp.tools.tags import register_tags_tools


def register_all_tools(mcp: FastMCP) -> None:
    """Register all tool categories with the FastMCP server."""
    register_search_tools(mcp)
    register_create_tools(mcp)
    register_read_tools(mcp)
    register_update_tools(mcp)
    register_delete_tools(mcp)
    register_convenience_tools(mcp)
    register_analysis_tools(mcp)
    register_tags_tools(mcp)
