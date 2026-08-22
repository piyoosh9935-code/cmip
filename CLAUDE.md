# CMIP — Project Context for Claude

CMIP (Clinical Member Intelligence Platform) is a portfolio project built to match a
specific resume bullet word-for-word, for tech interview prep. Built across 8 phases,
all complete. Full narrative (every bug, trade-off, and decision, with reasoning) is in
[CHALLENGES.md](./CHALLENGES.md); architecture and setup are in [README.md](./README.md);
one git commit per phase has the detailed change log.

**Read this file before modifying anything below** — it's a change-impact map, not an
architecture description. The point is knowing what else breaks before you touch
something, not re-deriving the whole dependency graph from scratch every session.

## Change-impact map

**Synthetic data generator** (`ingestion/synthetic_data_gen/*.py`)
→ `ingestion/postgres/load_raw_to_bronze.py` and dbt's `models/bronze/stg_*.sql`
(hardcoded column lists per table) both expect exact column names/table names matching
the `<table>_batch<N>.csv` convention. Adding/renaming a generator output column means
updating the matching `stg_*.sql` SELECT list too.

**dbt gold layer** (`models/gold/*.sql`, especially `member_notes_index`,
`member_claims_fact`, `member_summary`, `member_medications_current`)
→ read directly via raw SQL (no ORM, nothing type-checks this) by
`retrieval/qdrant/ingest.py`, `retrieval/bm25/build_index.py`, and
`retrieval/sql_retriever/templates.py`. Renaming/removing a gold column silently
breaks whichever Python file's SQL selects it — grep `retrieval/` and
`api/routers/members.py` for the column name before changing a gold schema.
Specific coupling: `claims_history()` depends on `member_claims_fact.provider_id`
being present — added specifically so the MCP agentic path can chain a claim lookup
into a provider lookup (Phase 4). Don't drop it.

**`retrieval/doc_id.py`** (`get_doc_id()`) — the one place citation IDs get assigned,
branching on `metadata["source"]` (qdrant/bm25/sql) and `metadata["intent"]` for sql.
→ `agent_graph/nodes/generation.py` (citation prompt), `verification.py` (checks
cited ids ⊆ graded ids), `llmops/mlflow/run_eval.py` (strips qdrant's
`note_id:chunk_index` back to bare `note_id` for eval comparison). Changing the ID
format for any source without updating all three breaks citation grounding *silently*
— the rule-based check just always fails, so every query exhausts its retries and
returns `low_confidence`, with no obvious error pointing at the real cause.

**`agent_graph/state.py`** (`PipelineState`) — the highest blast-radius component in
the system.
→ every node in `agent_graph/nodes/*.py`, `corrective_rag.py`,
`api/routers/query.py` (maps state keys to `QueryResponse` + the `pipeline_traces`
SQL insert), `frontend/lib/api.ts` (TS types), `frontend/components/PipelineTrace.tsx`
(renders specific keys). Adding or renaming one field touches 5+ files across two
languages.

**`model_routing/heuristic_router.py`** (`route()`)
→ `agent_graph/nodes/query_analysis.py` (initial routing) and
`corrective_rag.py`'s `prepare_retry` (escalation routing). Gotcha: the deterministic
graph path never calls `.bind_tools()` so any Ollama chat model works, but
`agent_graph/router_agent.py`'s agentic path does via `create_react_agent` —
**plain `llama3:latest` does not support Ollama tool-calling** (confirmed: 400 error).
Adding a new model to the routing pool requires checking tool-calling support before
it can ever be used on the agentic path.

**Directory naming** — `agent_graph/` and `mcp_server/` must never be renamed to
`langgraph/` or `mcp/` (or anything matching an installed pip package name). The
moment such a directory has an `__init__.py` and the repo root is on `sys.path`, it
silently shadows the real package, breaking every `from langgraph.graph import ...` /
`from mcp... import ...` with a confusing internal-import error. Hit this once
already in Phase 3 — don't reintroduce it to match the original README plan's literal
names.

**BM25 index** (`retrieval/bm25/index/bm25_index.pkl`) — gitignored/dockerignored,
generated, **not live**. Built once via `make ingest-bm25` (host) or
`docker/fastapi/entrypoint.sh` (container startup). If new data batches load into
Postgres while `fastapi`/`mcp` containers are already running, they must be
force-recreated to pick up the new notes — no live reload. Qdrant doesn't have this
problem (its data lives server-side).

**MLflow `--allowed-hosts`** (`docker-compose.yml`) — every hostname:port combination
that will ever address it must be listed explicitly; setting this flag at all
*replaces* the sensible default rather than extending it, and apparently matches
including the port. Adding a new service/script that logs to MLflow under a new
hostname means adding it here, or every write from it silently 403s.

**Docker Compose startup order** — `fastapi`/`mcp` need Postgres *populated*
(dbt gold layer built), not just *healthy* (accepting connections — true even when
empty). Bring up `postgres adminer qdrant mlflow` first, run the ingestion steps
(`make data`, `make dbt-run`, `make ingest-qdrant`), *then*
`docker compose up -d mcp fastapi`. A blanket `docker compose up -d` on a fresh clone
starts fastapi/mcp against an empty dataset.

**Python package pins are load-bearing, not arbitrary.** `langchain-classic` is
required for `EnsembleRetriever` (moved out of `langchain` in its 1.x package split);
`mcp.server.mcpserver.MCPServer` is the current name for what used to be `FastMCP`;
`docker/fastapi/Dockerfile` installs CPU-only `torch` before `requirements.txt` or the
image balloons from 1.93GB to 5.95GB with unused CUDA packages. Don't "clean up" these
without re-checking against currently-installed versions first (`pip show <pkg>`).

## Before making a change

1. Check the map above for the component you're touching.
2. Read the relevant phase section in `CHALLENGES.md` — it usually explains the
   non-obvious constraint that produced the current design, so you don't re-discover
   the same bug fixing it "back" to the naive version.
3. After changing something with downstream dependents, update all of them in the same
   change, then re-run the affected tests under `tests/` (organized to mirror the repo
   structure — `tests/agent_graph/`, `tests/retrieval/`, etc.) before considering it done.
4. Append a new finding to `CHALLENGES.md` (same phase if it's a continuation, a new
   dated section if not) if you hit anything non-obvious — that's what keeps this file
   and that one useful instead of stale.
