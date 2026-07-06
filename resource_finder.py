"""
Resource Finder Agent.

This is the agent that actually calls out to the MCP server (see
tutor/mcp_server/server.py) for search_arxiv / search_youtube / search_web.
It receives the targeted gap_query from the Gap Analyzer and decides which
tool(s) to call and how many results to keep as candidates -- the Curator
agent does the final ranking/excerpting.

See tutor/mcp_server/connection.py for how the connection is chosen
(local stdio subprocess by default, streamable-http when MCP_SERVER_URL
is set for a deployed server) -- this agent's code is identical either way.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from tutor.config import MODEL_NAME
from tutor.mcp_server.connection import build_resource_mcp_toolset

RESOURCE_FINDER_INSTRUCTION = """
You are looking for learning resources that close ONE specific knowledge
gap, not the general topic. The gap and preferred source type are given
below:

{gap_query}

Use the available tools (search_arxiv, search_youtube, search_web) to find
2-4 candidate resources. Prefer the PREFERRED_SOURCE type from the gap
query, but it's fine to also check another type if the preferred one
returns nothing useful or returns an "error" result (e.g. missing API
key) -- in that case, silently fall back and don't mention the error to
the learner.

For each candidate you keep, write a one-sentence relevance_note
explaining specifically why it addresses THIS gap (not just the general
subtopic). Discard anything that's clearly about the broad topic but not
the specific gap.

List your candidates as plain text, one per line, in the form:
TITLE | URL | SOURCE_TYPE | RELEVANCE_NOTE
"""

resource_finder_agent = LlmAgent(
    name="ResourceFinder",
    model=MODEL_NAME,
    description="Searches arXiv/YouTube/web (via MCP) for resources targeting a specific gap.",
    instruction=RESOURCE_FINDER_INSTRUCTION,
    tools=[build_resource_mcp_toolset(["search_arxiv", "search_youtube", "search_web"])],
    output_key="candidate_resources",
)