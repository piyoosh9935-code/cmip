# CMIP — Clinical Member Intelligence Platform

An end-to-end, local-first healthcare AI system: agentic retrieval-augmented generation
over synthetic claims, EHR, clinical notes, and SDoH data, built with LangChain,
LangGraph, Qdrant, MCP, and local Ollama models.

> **Data disclaimer**: all data in this project is synthetically generated
> (`ingestion/synthetic_data_gen/`), seeded and offline — no real patient data of any
> kind is used, stored, or downloaded.

**Build status**: in progress, built phase by phase. See the phase table below.

## Project Overview

CMIP performs agentic RAG over a member's combined health record to answer questions
like *"Summarize this member's diabetes history using claims + clinical notes."* — with
hybrid retrieval, citation-grounded generation, and automatic self-correction when the
answer isn't well-grounded in retrieved evidence.

Stack:

- **LangChain / LangGraph** — retrieval orchestration and agentic StateGraph workflow
- **Qdrant** — vector search over clinical notes
- **BM25** (`rank_bm25`) — lexical search over clinical notes
- **SQL retriever** — parameterized, template-based structured queries over claims/EHR
- **EnsembleRetriever** (`langchain-classic`) — weighted reciprocal rank fusion across
  the three retrievers above
- **MCP** (official `mcp` Python SDK) — standardized tool server for claims, provider,
  SQL, Qdrant, and BM25 access
- **Ollama** — local `llama3` / `mistral`, heuristically routed by query complexity
- **MLflow** — retrieval + pipeline evaluation metrics (precision@k, recall@k,
  groundedness, latency)
- **LangSmith** — optional, **off by default** (see [Tracing](#tracing))
- **dbt + Postgres** — Bronze → Silver → Gold ingestion, incremental loading
- **FastAPI** — serving layer
- **Next.js** — "Member 360" frontend (member profile + agent chat/trace panel)
- **Docker Compose** — reproducible local infrastructure

## Architecture

```
 Synthetic Data Gen (Faker, seeded, offline)
              │
              ▼
 dbt + Postgres: Bronze → Silver → Gold  (incremental)
              │
              ▼
 Hybrid Retrieval: Qdrant | BM25 | SQL templates
   → EnsembleRetriever (weighted RRF)
              │
              ▼
 LangGraph StateGraph (Self-RAG / Corrective-RAG)
   query_analysis → retrieval → grading → generation → verification
   └── bounded retry loop (≤3): rewrite query / reweight retrievers
              │
              ▼
 MCP Tool Server + Router Agent
   deterministic path (default)  |  agentic tool-calling path (multi-hop)
              │
              ▼
 Model Routing (Ollama): llama3 ↔ mistral, heuristic on query complexity
              │
              ▼
 Observability: MLflow (always on)  +  LangSmith (opt-in)
              │
              ▼
 FastAPI  →  Next.js Member 360 UI (profile + chat + pipeline trace)
```

## Repository Structure

```
cmip/
├── ingestion/
│   ├── synthetic_data_gen/   # seeded synthetic members/claims/EHR/notes/SDoH
│   ├── postgres/             # raw → bronze loader, extension init
│   └── dbt_project/          # bronze/silver/gold dbt models (own venv)
├── retrieval/
│   ├── qdrant/  bm25/  sql_retriever/
│   └── ensemble_retriever.py
├── langgraph/
│   ├── state.py  state_graph.py  router_agent.py  corrective_rag.py
│   └── nodes/                # query_analysis, retrieval, grading, generation, verification
├── mcp/
│   ├── server.py
│   └── tools/                # claims, provider, sql, qdrant, bm25
├── model_routing/            # heuristic_router.py, ollama_client.py
├── llmops/
│   ├── langsmith/            # opt-in tracing
│   └── mlflow/               # experiment + metrics logging
├── api/                      # FastAPI app + routers
├── frontend/                 # Next.js Member 360 dashboard
├── tests/                    # per-component + e2e tests
├── docker-compose.yml
└── docker/fastapi/           # shared image for fastapi + mcp services
```

## Why Hybrid Retrieval

Healthcare questions vary in kind: clinical notes need semantic search, claims/EHR
lookups need structured queries, and code/term mentions need exact lexical match. A
single retriever under-serves at least one of these, so CMIP combines all three with
weighted reciprocal rank fusion via `EnsembleRetriever`, and lets the Corrective-RAG
retry loop reweight them when grading finds the initial mix insufficient.

Every retrieval call — vector, lexical, and SQL — is scoped by `member_id`. This is a
deliberate design choice, not an afterthought: in a real system this is the boundary
that prevents one member's data from leaking into another member's answer.

The SQL retriever intentionally uses parameterized query templates rather than
text-to-SQL: a local, CPU-bound Ollama model generating raw SQL against a real schema is
an unreliable and unsafe pattern (hallucinated columns, injection risk). Query intent is
classified into a fixed set and mapped to a safe, parameterized SQLAlchemy query instead.

## LangGraph Pipeline (Self-RAG / Corrective-RAG)

`query_analysis → retrieval → grading → generation → verification`, with a bounded
retry loop (max 3) back to retrieval when verification fails: rewrite the query and/or
reweight the retrievers, then re-grade and regenerate. Verification runs a cheap
rule-based citation-existence check (do the cited chunk IDs exist in the retrieved set?)
before a costlier LLM groundedness judge, to short-circuit obviously invalid answers
without an extra model call.

## Model Routing

`model_routing/heuristic_router.py` is pure heuristics — no LLM call decides the
routing. Question length, an aggregation/multi-hop keyword list, multi-source mentions,
and any active retry all factor into a llama3-vs-mistral choice, logged with a
human-readable reason for the UI trace panel.

## MCP Tool Server

Built on the official `mcp` Python SDK (`mcp.server.mcpserver.MCPServer` — the SDK's
v2 rework renamed `FastMCP`; decorator API is unchanged), streamable-http transport,
its own container. Exposes `claims`, `provider`, `sql`, `qdrant`, and `bm25` tools. The
router agent has two paths: a deterministic path (intent → `ensemble_retriever`
directly, used by the main graph) and an agentic MCP path for multi-hop questions
(LangGraph tool-calling agent over the 5 tools, bounded to 3 calls).

## Observability

**MLflow** (always on): one run per query, logging routed model + reason, retrieval
weights, retry count, precision@k/recall@k against a hand-labeled eval set, groundedness
score, and per-node latency.

## Tracing

**LangSmith is opt-in and off by default.** It is a third-party SaaS product, not a
local service — the project deliberately does not send anything there unless you
provide your own account. To enable it, set both in `.env`:

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-key
```

With neither set, no LangSmith client is initialized and no network call is made.

## Local Development Setup

**Prerequisites**: Docker + Compose, Python 3.12, Node 18+, [Ollama](https://ollama.com)
running natively on the host with `llama3` and `mistral` pulled.

```bash
# 1. Python env (repo services)
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

# 2. dbt env (isolated on purpose — its pins conflict with LangChain's)
cd ingestion/dbt_project && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ../..

# 3. Ollama models
ollama pull llama3
ollama pull mistral

# 4. Infra
docker compose up -d

# 5. Synthetic data → dbt Bronze/Silver/Gold
make data
make dbt-run

# 6. Retrieval indexes
make ingest-qdrant
make ingest-bm25

# 7. API
make api

# 8. Frontend
cd frontend && npm install && npm run dev
```

## Example Query

```
POST /query
{
  "member_id": "M-0231",
  "question": "Summarize this member's diabetes history using claims + clinical notes."
}
```

Response includes the answer, citations, groundedness score, retry count, routed model
+ reason, and a `trace_id` for `GET /trace/{trace_id}` — the same data the frontend's
pipeline trace panel renders.

## Challenges, Trade-offs, and Decisions

See [CHALLENGES.md](./CHALLENGES.md) for a running, phase-by-phase log of real problems
hit during the build, the trade-offs behind non-obvious design choices, and how each
was resolved — kept specifically so every design decision here has a concrete "why"
behind it, not just a "what."

## Build Phases

| # | Phase | Status |
|---|---|---|
| 0 | Scaffolding, dependency pins, venvs | ✅ done |
| 1 | Synthetic data, dbt Bronze/Silver/Gold, Postgres | ✅ done |
| 2 | Qdrant + BM25 + ensemble retrieval | ✅ done |
| 3 | LangGraph Self-RAG/Corrective-RAG pipeline | ⏳ next |
| 4 | MCP server + router agent | not started |
| 5 | Model routing + MLflow + eval set | not started |
| 6 | FastAPI service | not started |
| 7 | Next.js Member 360 frontend | not started |
| 8 | Full Docker Compose integration + e2e test | not started |

## Notes on Tooling Versions

This project pins dependencies deliberately (not "latest") because the LangChain/
LangGraph/MCP/MLflow ecosystem shipped major version bumps in 2026 with real breaking
changes — e.g. `EnsembleRetriever` moved out of the main `langchain` package into
`langchain-classic`, and the MCP SDK's `FastMCP` was renamed `MCPServer`. See
`requirements.txt` for exact ranges and the reasoning inline.
