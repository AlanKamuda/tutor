"""
Gap Analyzer Agent.

Takes failed evaluations and produces a targeted gap query for the Resource Finder.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from tutor.config import MODEL_NAME

GAP_ANALYZER_INSTRUCTION = """
You are analyzing a learner's performance on a subtopic quiz. They did NOT reach mastery.
Here are the evaluations of their incorrect answers:

{failed_evaluations}

For the MOST SIGNIFICANT gap, write a targeted search query that the Resource Finder 
agent can use to find a resource that fills THAT SPECIFIC GAP.

Also choose a PREFERRED_SOURCE:
  - "youtube" if this is a conceptual misconception needing visual explanation
  - "arxiv" or "pdf" if this needs rigorous/technical treatment
  - "blog" if this just needs a clear plain-language explainer

Output format (plain text, one line):
PREFERRED_SOURCE: <source>
QUERY: <your targeted query>

Example:
PREFERRED_SOURCE: youtube
QUERY: why does the gradient point in the direction of steepest ascent, visual intuition
"""

gap_analyzer_agent = LlmAgent(
    name="GapAnalyzer",
    model=MODEL_NAME,
    description="Converts failed quiz evaluations into a targeted resource search query.",
    instruction=GAP_ANALYZER_INSTRUCTION,
    output_key="gap_query_raw",
)


def parse_gap_query(raw: str) -> dict:
    """Parse gap analyzer output into {preferred_source, query}."""
    lines = [ln.strip() for ln in raw.strip().split("\n") if ln.strip()]
    result = {"preferred_source": "blog", "query": ""}
    for line in lines:
        if line.startswith("PREFERRED_SOURCE:"):
            result["preferred_source"] = line.split(":", 1)[1].strip().lower()
        elif line.startswith("QUERY:"):
            result["query"] = line.split(":", 1)[1].strip()
    return result
