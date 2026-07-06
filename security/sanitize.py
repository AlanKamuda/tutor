"""
Security helpers for the Knowledge Gap Tutor.

Two threat surfaces matter most for this project:
1. Untrusted web content flowing INTO the agent
2. Secrets handling - API keys must never be hardcoded, logged, or echoed
"""

from __future__ import annotations

import os
import re

# Patterns that indicate a scraped document is trying to address the LLM
# directly rather than being content about the topic
_INJECTION_PATTERNS = [
    r"ignore (all|any|previous|the) (instructions|prompts?)",
    r"system prompt",
    r"you are now",
    r"disregard (all|any|previous) (instructions|rules)",
    r"act as (if|though) you (are|were)",
    r"\bDAN\b",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

MAX_EXCERPT_CHARS = 4000


def sanitize_external_text(text: str, *, source_url: str = "") -> str:
    """
    Clean text pulled from an external resource before it's placed in agent context.
    
    - Truncates to hard length cap
    - Redacts lines that look like prompt-injection attempts
    - Wraps result so model knows this is untrusted data
    """
    if not text:
        return ""
    
    truncated = text[:MAX_EXCERPT_CHARS]
    cleaned_lines = []
    
    for line in truncated.splitlines():
        if _INJECTION_RE.search(line):
            cleaned_lines.append("[redacted: line removed by content sanitizer]")
        else:
            cleaned_lines.append(line)
    
    cleaned = "\n".join(cleaned_lines)
    
    return (
        f'<untrusted_external_content source="{source_url}">\n'
        f"{cleaned}\n"
        f"</untrusted_external_content>"
    )


def require_env(var_name: str) -> str:
    """
    Fetch a required environment variable or raise with a clear message.
    Never put the key's value in logs or exceptions.
    """
    value = os.environ.get(var_name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {var_name}. "
            f"Set it in your .env file (see .env.example) -- never hardcode it."
        )
    return value


def redact_for_logging(value: str, keep: int = 4) -> str:
    """Return a safe-to-log version of a secret, e.g. 'sk-ab12...wxyz'."""
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}...{value[-keep:]}"
