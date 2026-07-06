"""
Resource Finder Agent.

Searches arXiv/YouTube/web for resources targeting a specific gap.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from tutor.config import MODEL_NAME
from tutor.mcp_server.connection import build_resource_mcp_toolset

RESOURCE_FINDER_INSTRUCTION = """
You are looking for learning resources that close ONE specific knowledge gap.
The gap and preferred source type are given below:

{gap_query}

Use the available tools (search_arxiv, search_youtube, search_web) to find 2-4 
candidate resources. Prefer the PREFERRED_SOURCE type from the gap query.

For each candidate, write a one-sentence relevance_note explaining why it 
addresses THIS gap (not just the general subtopic).

List your candidates as plain text, one per line:
TITLE | URL | SOURCE_TYPE | RELEVANCE_NOTE
"""

resource_finder_agent = LlmAgent(
    name="ResourceFinder",
    model=MODEL_NAME,
    description="Searches arXiv/YouTube/web for resources targeting a specific gap.",
    instruction=RESOURCE_FINDER_INSTRUCTION,
    tools=build_resource_mcp_toolset(["search_arxiv", "search_youtube", "search_web"]),
    output_key="candidate_resources",
)
