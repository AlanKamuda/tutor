"""
MCP server for the Knowledge Gap Tutor.

Exposes a small set of resource-discovery tools that the Resource Finder
agent calls via MCPToolset (see tutor/agents/resource_finder.py):

    - search_arxiv       free, no API key, good for rigorous/academic gaps
    - search_youtube      requires YOUTUBE_API_KEY, good for visual/intuitive gaps
    - search_web          requires a search API key (Tavily/Serper-style), blogs/articles
    - fetch_excerpt       given a URL + a gap description, pull just the relevant
                           excerpt (page range for PDFs, paragraph for HTML) instead
                           of dumping the whole document into the agent's context

Run standalone for local testing:
    python -m tutor.mcp_server.server

In production this is registered with the agent via MCPToolset pointing at
this process's stdio or a deployed HTTP endpoint (see deploy/README.md).
"""

from __future__ import annotations

import io
import os
import xml.etree.ElementTree as ET

import requests
from mcp.server.fastmcp import FastMCP

from tutor.security import redact_for_logging, sanitize_external_text

mcp = FastMCP("knowledge-gap-tutor-resources")

REQUEST_TIMEOUT = 10  # seconds -- never let a slow/hostile server hang the agent


@mcp.tool()
def search_arxiv(query: str, max_results: int = 5) -> list[dict]:
    """
    Search arXiv for papers relevant to `query`. No API key required.
    Best for: rigorous/conceptual gaps where a primary source helps
    (e.g. "why does the Krein space inner product allow negative norms").

    Returns a list of {title, url, summary} dicts.
    """
    resp = requests.get(
        "http://export.arxiv.org/api/query",
        params={"search_query": f"all:{query}", "max_results": max_results},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.text)
    results = []
    for entry in root.findall("atom:entry", ns):
        title = entry.findtext("atom:title", default="", namespaces=ns).strip()
        summary = entry.findtext("atom:summary", default="", namespaces=ns).strip()
        link = entry.findtext("atom:id", default="", namespaces=ns).strip()
        results.append({"title": title, "url": link, "summary": summary[:500]})
    return results


@mcp.tool()
def search_youtube(query: str, max_results: int = 5) -> list[dict]:
    """
    Search YouTube for videos relevant to `query`. Requires YOUTUBE_API_KEY
    in the environment. Best for: intuition-building gaps where seeing an
    animation/visualization closes the gap faster than reading text
    (e.g. "how a descent-stage engine throttles down for lunar landing").

    Returns a list of {title, url, channel} dicts, or a single
    {"error": ...} dict if the key is missing/invalid -- callers should
    check for "error" and fall back to search_web / search_arxiv.
    """
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return [{"error": "YOUTUBE_API_KEY not configured; skipping video search."}]

    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "part": "snippet",
            "q": query,
            "maxResults": max_results,
            "type": "video",
            "key": api_key,
        },
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code != 200:
        return [{"error": f"YouTube API error: {resp.status_code}"}]

    items = resp.json().get("items", [])
    return [
        {
            "title": it["snippet"]["title"],
            "url": f"https://www.youtube.com/watch?v={it['id']['videoId']}",
            "channel": it["snippet"]["channelTitle"],
        }
        for it in items
    ]


@mcp.tool()
def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    General web search (blogs, articles, explainers) for `query`. Requires
    WEB_SEARCH_API_KEY (Tavily-compatible endpoint) in the environment.
    Best for: plain-language explainers that fill a gap without requiring
    the rigor of a paper or the production value of a video.

    Returns a list of {title, url, snippet} dicts, or {"error": ...}.
    """
    api_key = os.environ.get("WEB_SEARCH_API_KEY")
    if not api_key:
        return [{"error": "WEB_SEARCH_API_KEY not configured; skipping web search."}]

    resp = requests.post(
        "https://api.tavily.com/search",
        json={"api_key": api_key, "query": query, "max_results": max_results},
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code != 200:
        return [{"error": f"Web search API error: {resp.status_code}"}]

    results = resp.json().get("results", [])
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")[:500]}
        for r in results
    ]


@mcp.tool()
def fetch_excerpt(url: str, gap_description: str, max_chars: int = 2000) -> dict:
    """
    Fetch a URL (HTML page or PDF) and return only the excerpt most relevant
    to `gap_description`, rather than the full document. This keeps the
    Curator agent's context small and on-target, and is the main defense
    against the "find a video, dump the whole transcript" failure mode.

    All fetched content is passed through sanitize_external_text before
    being returned -- the page is treated as untrusted data, not as
    instructions, regardless of what it contains.

    Returns {"excerpt": str, "source_url": str} or {"error": str}.
    """
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return {"error": f"Could not fetch {url}: {exc}"}

    content_type = resp.headers.get("Content-Type", "")

    if "pdf" in content_type or url.lower().endswith(".pdf"):
        text = _extract_pdf_text(resp.content)
    else:
        text = _extract_html_text(resp.text)

    excerpt = _find_relevant_window(text, gap_description, max_chars)
    sanitized = sanitize_external_text(excerpt, source_url=url)
    return {"excerpt": sanitized, "source_url": url}


def _extract_pdf_text(raw_bytes: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_html_text(html: str) -> str:
    # Lightweight tag-strip; swap for readability/trafilatura if you want
    # better main-content extraction in production.
    import re

    text = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _find_relevant_window(text: str, gap_description: str, max_chars: int) -> str:
    """Naive keyword-window search: find the densest cluster of gap keywords
    and return a window around it. Good enough for an MVP; the Curator agent
    re-ranks/cleans this further with the LLM."""
    keywords = [w.lower() for w in gap_description.split() if len(w) > 3]
    if not keywords or not text:
        return text[:max_chars]

    lower = text.lower()
    best_idx, best_score = 0, -1
    window = 500
    for i in range(0, max(len(lower) - window, 1), window // 2):
        chunk = lower[i : i + window]
        score = sum(chunk.count(k) for k in keywords)
        if score > best_score:
            best_score, best_idx = score, i

    start = max(best_idx - max_chars // 4, 0)
    return text[start : start + max_chars]


def run() -> None:
    """
    Entry point for `python -m tutor.mcp_server.server [--transport stdio|streamable-http]`.

    - stdio (default): used by resource_finder.py / curator.py for local
      development -- ADK spawns this as a subprocess and talks to it over
      stdin/stdout, no network exposure at all.
    - streamable-http: used when this server is deployed standalone (see
      deploy/Dockerfile + deploy/README.md); agents then connect via
      StreamableHTTPConnectionParams(url=...) instead of spawning a
      subprocess.
    """
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    args = parser.parse_args()

    if args.transport == "streamable-http":
        port = int(os.environ.get("PORT", "8080"))
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = port
    mcp.run(transport=args.transport)



__all__ = ["search_arxiv", "search_youtube", "search_web", "fetch_excerpt", "run"]


if __name__ == "__main__":
    run()