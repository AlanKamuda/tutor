"""
MCP connection builder for the Resource Finder and Curator agents.

Simplified version that works with standard MCP client + ADK tool integration.
"""

from __future__ import annotations

import sys
from typing import Any, Callable

from tutor.config import MCP_SERVER_URL


def build_resource_mcp_toolset(tool_names: list[str]) -> list[Callable]:
    """
    Returns a list of tool functions that agents can call.
    
    For now, we'll import the tools directly from the MCP server module
    rather than using a subprocess connection (simpler for MVP).
    
    Args:
        tool_names: subset of ["search_arxiv", "search_youtube", "search_web", "fetch_excerpt"]
    """
    # Import the actual tool functions from the MCP server
    from tutor.mcp_server import server
    
    tool_map = {
        "search_arxiv": server.search_arxiv,
        "search_youtube": server.search_youtube,
        "search_web": server.search_web,
        "fetch_excerpt": server.fetch_excerpt,
    }
    
    return [tool_map[name] for name in tool_names if name in tool_map]
