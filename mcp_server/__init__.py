"""MCP server module for Knowledge Gap Tutor."""

from tutor.mcp_server.server import (
    search_arxiv,
    search_youtube,
    search_web,
    fetch_excerpt,
)

__all__ = [
    "search_arxiv",
    "search_youtube", 
    "search_web",
    "fetch_excerpt",
]
