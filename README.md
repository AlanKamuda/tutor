# Knowledge Gap Tutor 🎓

An adaptive multi-agent learning pipeline that diagnoses your exact knowledge gaps and finds the specific resource that closes them — built on Google ADK for the Kaggle 5-Day AI Agents Intensive Vibe Coding Capstone.

**Track:** Agents for Good | **Course Concepts:** Multi-agent (ADK), MCP Server, Security, Deployability, Agent Skills

---

## The Problem

Search "backpropagation tutorial" and you get a hundred overviews. None of them find the specific thing you're misunderstanding. Most self-directed learners already know 80% of a topic — what they need is not more content, but a diagnosis of the precise 20% that's missing or wrong, and then the one resource that closes exactly that gap.

A search engine can't do this. A single LLM prompt can't do this. You need a pipeline that quizzes you, evaluates *why* you're wrong (not just *that* you're wrong), formulates a targeted search query from that classification, executes live searches, and retrieves only the relevant excerpt from what it finds.

---

## Architecture

Six `LlmAgent` instances in Google ADK 2.3, communicating via session state:

```
Topic
  ↓
CurriculumMapper    →  3-5 ordered subtopics (output_schema: CurriculumMap)
  ↓
QuizGenerator       →  3 questions per subtopic: recall / applied / conceptual
  ↓
[Human answers]
  ↓
Evaluator           →  is_correct + gap_type per answer (MISCONCEPTION / MISSING_KNOWLEDGE / SLIP)
  ↓ (if not mastered)
GapAnalyzer         →  ONE targeted search query + preferred source type
  ↓
ResourceFinder      →  MCP: search_arxiv / search_youtube / search_web
  ↓
Curator             →  MCP: fetch_excerpt → 1-2 resources with specific excerpt
  ↓
[Human studies, then re-quiz — up to 3 attempts per subtopic]
```

Agents 4-6 form a `SequentialAgent` (RemediationPipeline) that only activates when mastery is not achieved. The outer loop in `main.py` drives human-in-the-loop control, which is the correct ADK pattern for workflows that require genuine human steps between agent turns.

### Agent Responsibilities

| Agent | File | Role |
|---|---|---|
| CurriculumMapper | `tutor/agents/curriculum_mapper.py` | Decomposes topic into ordered subtopics with prerequisites |
| QuizGenerator | `tutor/agents/quiz_generator.py` | Writes 3 questions at mixed difficulty levels |
| Evaluator | `tutor/agents/evaluator.py` | Grades answers and classifies gap type |
| GapAnalyzer | `tutor/agents/gap_analyzer.py` | Converts gap classification into a targeted search query |
| ResourceFinder | `tutor/agents/resource_finder.py` | Searches arXiv/YouTube/web via MCP server |
| Curator | `tutor/agents/curator.py` | Picks best resources and fetches targeted excerpts |

### MCP Server Tools

| Tool | Description | API Key Required |
|---|---|---|
| `search_arxiv` | Academic papers on the gap topic | None |
| `search_youtube` | Video resources for visual/intuition gaps | `YOUTUBE_API_KEY` |
| `search_web` | Blog/article resources for plain-language gaps | `WEB_SEARCH_API_KEY` |
| `fetch_excerpt` | Fetches a URL and extracts the relevant window of text | None |

ResourceFinder and Curator each get a `tool_filter`-scoped `McpToolset` — each agent can only call the tools it actually needs (least-privilege).

---

## Course Concepts

| Concept | Where |
|---|---|
| Multi-agent system (ADK) | `tutor/agents/` — 6 `LlmAgent` + 1 `SequentialAgent` |
| MCP Server | `tutor/mcp_server/server.py` — FastMCP with 4 tools |
| Security features | `tutor/security/sanitize.py` — injection defense, secret handling; `main.py` — 429 retry with backoff |
| Deployability | `deploy/Dockerfile` — Cloud Run; `MCP_SERVER_URL` env var switches local↔deployed |
| Agent skills (CLI) | `adk web tutor`, `python -m tutor.cli`, `python -m tutor.debug` |

---

## Security

- **Prompt injection defense:** all content fetched from external URLs is sanitized by `sanitize_external_text()` — strips injection patterns, wraps in `<untrusted_external_content>` tags, capped at 4,000 characters
- **Secret handling:** `require_env()` fails loudly on missing keys (name only, never value); `redact_for_logging()` masks secrets in logs
- **Rate-limit resilience:** `run_agent()` retries on 429 RESOURCE_EXHAUSTED, parsing `retryDelay` from Google's response to wait exactly the right amount

---

## Project Structure

```
knowledge-gap-tutor/
├── tutor/
│   ├── agents/
│   │   ├── curriculum_mapper.py   # Step 1: topic decomposition
│   │   ├── quiz_generator.py      # Step 2: question generation
│   │   ├── evaluator.py           # Step 3: answer grading + gap classification
│   │   ├── gap_analyzer.py        # Step 4: search query formulation
│   │   ├── resource_finder.py     # Step 5: MCP-based resource search
│   │   ├── curator.py             # Step 6: excerpt retrieval + ranking
│   │   └── orchestrator.py        # SequentialAgent + root_agent for adk web
│   ├── mcp_server/
│   │   ├── server.py              # FastMCP server with 4 tools
│   │   └── connection.py          # stdio (local) / HTTP (deployed) connection
│   ├── models/
│   │   └── schemas.py             # Pydantic data contracts for all agent I/O
│   ├── security/
│   │   └── sanitize.py            # Injection defense, secret handling
│   ├── main.py                    # Orchestration + human-in-the-loop loop
│   ├── cli.py                     # Async CLI session runner
│   ├── agent.py                   # adk web / adk run entry point
│   └── config.py                  # Model name, thresholds, env loading
├── tests/
│   └── test_schemas_and_security.py  # No API key required
├── deploy/
│   └── Dockerfile                 # Cloud Run deployment for MCP server
├── .env.example
├── requirements.txt
└── README.md
```

---

## Setup

### Requirements

- Python 3.12+
- A Google Gemini API key ([get one here](https://aistudio.google.com/apikey))

### Install

```bash
git clone <repo-url>
cd knowledge-gap-tutor
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env`:

```
GOOGLE_API_KEY=your-key-here          # required
YOUTUBE_API_KEY=                       # optional: enables video search
WEB_SEARCH_API_KEY=                    # optional: enables blog/article search (Tavily)
```

If `YOUTUBE_API_KEY` or `WEB_SEARCH_API_KEY` are absent, the ResourceFinder silently falls back to arXiv / whatever sources are available — the pipeline still works.

### Run

**Interactive study session (recommended for demo):**
```bash
python -m tutor.main "backpropagation in neural networks"
```

**ADK conversational web UI:**
```bash
adk web tutor
```

**Test a single agent without a full session:**
```bash
python -m tutor.debug curriculum_mapper '{"topic": "gradient descent"}'
python -m tutor.debug quiz_generator '{"current_subtopic": "the chain rule"}'
```

**Run tests (no API key needed):**
```bash
pytest tests/
```

---

## Deployment (MCP Server on Cloud Run)

The MCP server can be deployed standalone so the agents connect to it over HTTP instead of spawning it as a local subprocess.

```bash
cd deploy
docker build -f Dockerfile -t knowledge-gap-tutor-mcp ..
docker run -p 8080:8080 \
  -e YOUTUBE_API_KEY=your-key \
  -e WEB_SEARCH_API_KEY=your-key \
  knowledge-gap-tutor-mcp --transport streamable-http
```

Then set in your `.env`:
```
MCP_SERVER_URL=http://localhost:8080/mcp
```

No agent code changes are needed — `tutor/mcp_server/connection.py` detects `MCP_SERVER_URL` and switches from stdio to HTTP automatically. For Cloud Run, deploy with secrets set as Cloud Run secret environment variables (never as plain env vars).

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_API_KEY` | — | Required. Gemini API key |
| `TUTOR_MODEL` | `gemini-2.5-flash` | Model for all agents |
| `TUTOR_MASTERY_THRESHOLD` | `0.75` | Fraction correct to count as mastered |
| `TUTOR_MAX_REMEDIATION_LOOPS` | `3` | Max re-quiz attempts per subtopic |
| `YOUTUBE_API_KEY` | — | Optional. Enables YouTube search |
| `WEB_SEARCH_API_KEY` | — | Optional. Enables web search (Tavily) |
| `MCP_SERVER_URL` | — | Optional. Points agents at a deployed MCP server |

---

## Example Output

```
════════════════════════════════════════════════════════════
🎓 Knowledge Gap Tutor
════════════════════════════════════════════════════════════

📚 Building curriculum map for: backpropagation in neural networks
   ✓ Found 4 subtopics
     - The forward pass and loss computation
     - The chain rule and partial derivatives
     - Backpropagation algorithm (weight updates)
     - Gradient descent and learning rate

────────────────────────────────────────────────────────────
📖 Subtopic: The chain rule and partial derivatives (attempt 1/3)
────────────────────────────────────────────────────────────

📝 Quiz time! (3 questions)

Q1 [recall]: What does the chain rule say about the derivative of f(g(x))?
Your answer: ...

📊 Score: 1/3 (33%) – needs review ✗

🔍 Analyzing 2 gap(s)...
   Gap query: why chain rule applies term-by-term in backpropagation composition
   Preferred source: arxiv

🌐 Searching for resources...
📚 Curating best resources...
   ✓ Selected 1 resource(s):
     [arxiv] Calculus on Computational Graphs: Backpropagation
       https://arxiv.org/abs/...
       → Directly addresses the term-by-term chain rule application...
```

---

## Notes on Free-Tier Rate Limits

Gemini 2.5 Flash on the free tier allows 5 requests/minute. A full study session burns several requests per subtopic (quiz generation, evaluation per question, gap analysis, resource finding, curation). `run_agent()` handles 429 errors with automatic retry + backoff, so you won't lose work — but waits of 20-30s are normal on the free tier. To avoid this entirely, enable billing on your Google Cloud project (the paid tier is 1,000 RPM for Gemini 2.5 Flash) or switch `TUTOR_MODEL` to `gemini-2.5-flash-lite` for higher free-tier limits.
