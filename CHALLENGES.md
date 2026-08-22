# CMIP — Challenges, Trade-offs, and Decisions

A running log of real problems hit while building this, the trade-offs behind
non-obvious design choices, and how each was resolved — kept phase by phase so it
doubles as interview prep: this is the "why," not just the "what," of the codebase.

## Phase 0 — Scaffolding

**Ecosystem version drift broke assumed APIs.** The LangChain/LangGraph/MCP/MLflow
stack shipped major version bumps in 2026 that changed import paths I'd normally take
for granted. Caught both by actually running an import smoke test right after `pip
install`, instead of trusting the plan's assumed API surface:
- `EnsembleRetriever` moved out of the main `langchain` package into a new
  `langchain-classic` package as part of langchain 1.x's package split (the main
  package now only ships agents/chat_models/embeddings/messages/tools).
- The MCP Python SDK's v2 rework renamed `FastMCP` to `MCPServer`
  (`mcp.server.mcpserver.MCPServer`); the decorator API (`@mcp.tool()`) is unchanged.
- **Fix**: added `langchain-classic` to `requirements.txt`, updated all MCP-related
  code/docs to the new import path, and documented both in the README so nobody
  re-discovers this the hard way.

**Python version choice.** The pre-existing `dbt/venv` had been built on system Python
3.14 (bleeding-edge, released within the year). Rather than discover mid-build that
some ML/dbt dependency lacked a 3.14 wheel, standardized every service on Python 3.12
up front, with dbt kept in its own isolated venv (its jinja2/click/protobuf pins
routinely conflict with the LangChain ecosystem's).

## Phase 1 — Synthetic Data + dbt

**dbt's default schema naming would have mismatched the schemas Python already
created.** dbt's default `generate_schema_name` macro produces `<target_schema>_bronze`
for a model with `+schema: bronze`, not `bronze` itself — that would silently create a
*fourth* schema (`dev_bronze`) instead of writing into the `bronze` schema the Postgres
loader and `init_extensions.sql` already populate. **Fix**: overrode
`generate_schema_name` in `macros/get_custom_schema.sql` to use the custom schema name
verbatim.

**Deterministic incremental data generation without a state file.** The synthetic data
generator needs to support `--batch 2`, `--batch 3`, ... runs that each add only *new*
rows (new members + a trickle of new activity on existing members), and be safely
re-runnable. Rather than persist a state file tracking "who exists already" (extra
failure mode, extra thing to keep in sync), every entity's identity and attributes
(e.g. `cohorts_for_member(index)`) are derived from a pure function of
`(global seed, member index)` — a member's cohort assignment is identical whether it's
computed while generating batch 1 or looked up while generating batch 5's incremental
activity for that member. Batch membership ranges are similarly computed from config
alone (`member_index_range_for_batch`), so the whole generator is stateless and
idempotent per batch.

**Docker Desktop's VM disk was completely full — not a project problem, but it blocked
one.** `docker compose up postgres` failed with `initdb: error: could not create
directory ... No space left on device`. The host Mac had disk free; the problem was
Docker Desktop's *own* virtual disk (a fixed-size file, 58.4GB cap) sitting at 100%
from unrelated prior work — mostly 6 dangling, untagged images (~34.6GB) from 17
months ago plus ~40GB of pure build cache. Diagnosed with `docker system df` and a
`docker run --rm alpine df -h /` (to see the VM's own filesystem, not the host's).
**Trade-off**: freeing this required deleting things outside this project's scope —
handled by explicitly separating "safe to remove" (dangling/untagged images tied to
long-exited containers, pure build cache — always reconstructable) from "leave alone"
(the user's other tagged images: pgadmin, spark-iceberg, ai-model, etc.), and getting
explicit go-ahead before each removal rather than a blanket `docker system prune -a`.

**Pre-existing bug in the starter `docker-compose.yml`.** `postgres:15` was combined
with a `command: postgres -c shared_preload_libraries=pgvector` override — but that
plain image has no pgvector extension, so the container would fail at startup.
**Fix**: switched to `pgvector/pgvector:pg15`, which ships the extension, and added a
healthcheck so dependent services (adminer, later fastapi/mcp) wait for real readiness
instead of a fixed sleep.

**dbt test deprecation.** The `relationships` test's `to`/`field` arguments generated a
`MissingArgumentsPropertyInGenericTestDeprecation` warning under dbt-core 1.12 —
current syntax nests them under an `arguments:` key. Fixed across all three usages in
`models/silver/_schema.yml` rather than leaving a warning in a clean build.

## Phase 2 — Hybrid Retrieval

**BM25's IDF term goes negative on tiny per-member corpora — a real bug, not a
hypothetical.** Per-member BM25 sub-indexes are often only 2-4 documents. BM25's IDF
formula, `log((N - n + 0.5) / (n + 0.5))`, goes negative once a term appears in more
than half the documents in a small corpus — completely normal for, say, a 2-note
corpus where a query word matches both notes. The retriever's first version filtered
`score > 0`, which silently discarded *good* matches whenever a member had very few
notes. Caught by testing a real query end-to-end and getting an empty result list for
an obviously-relevant search. **Fix**: dropped the positivity filter and return top-k
unconditionally — relative ranking within a member's own corpus is still meaningful
even when the absolute score is negative, and reasoned that relevance *filtering* is
correctly the grading node's job (Phase 3), not the retriever's; a retriever's contract
is to return candidates, not to pre-judge relevance.

**LangChain's built-in `BM25Retriever` doesn't fit a multi-tenant-by-member design.**
It holds one global in-memory corpus with no native per-member filtering or
persistence. **Trade-off**: built custom per-member `BM25Okapi` sub-indexes instead
(via `rank_bm25` directly), pickled to a single dict-of-indexes on disk, wrapped in a
small custom `BaseRetriever` subclass — more code than reusing the built-in, but every
retrieval call in this system is member-scoped by design (see README), and the
built-in retriever can't express that without hacks.

**`EnsembleRetriever` calls every wrapped retriever with the same plain query string —
but the SQL leg needs structured intent.** LangChain's ensemble mechanism has no
concept of "pass this retriever a different, structured input." **Fix**: gave
`SQLMemberRetriever` its own self-contained keyword-based intent classifier
(`classify_intent`) so it still honors the standard `BaseRetriever.invoke(query: str)`
contract and plugs into `EnsembleRetriever` like any other retriever, while internally
routing to the right parameterized template. (Phase 3's `query_analysis` node will do
more precise LLM-based intent classification for the graph's own routing decisions;
this classifier is deliberately simpler and self-sufficient so the retriever works
standalone too.)

**Text-to-SQL was considered and rejected.** A local, CPU-bound Ollama model
generating raw SQL against a real schema is a genuine reliability and safety risk
(hallucinated columns/tables, no guardrail against destructive statements, inconsistent
output shape across runs — all worse on a small model than on GPT-4-class ones).
**Trade-off accepted**: a fixed set of intents mapped to parameterized SQLAlchemy
templates is far less flexible (can't answer an arbitrary ad hoc structured question)
but deterministic, safe, and fast — the right trade for a local-model system, and a
concrete, defensible answer to "why not text-to-SQL" in an interview.

## Phase 3 — LangGraph Self-RAG / Corrective-RAG Pipeline

**The README's own directory names shadowed the real packages they depend on.** The
documented structure calls for top-level `langgraph/` and `mcp/` directories — but
`langgraph` and `mcp` are also the exact names of the installed pip packages this code
needs to `import`. As soon as either directory has an `__init__.py` (i.e. becomes a
real Python package) and the repo root is on `sys.path` (true for `python -m ...`,
`pytest`, and most app entry points), `import langgraph` / `import mcp` resolves to
*our own empty package* instead of the library — breaking `from langgraph.graph import
StateGraph` from inside code that lives in a directory literally named `langgraph/`.
Caught proactively by testing the import in isolation *before* writing any real code
into either directory, rather than discovering it mid-implementation. **Fix**: renamed
to `agent_graph/` and `mcp_server/` — same content and purpose, no collision with any
installed package (verified via `importlib.util.find_spec`), documented inline in the
README's repo tree so the deviation from the originally-planned names is explained
rather than silently different.

**Testing the graph's wiring against real Ollama models surfaced two genuinely
different problems that looked identical from the outside** (both showed up as "failed
groundedness check, escalate and retry"):

1. *A real bug*: llama3's structured `AnswerWithCitations.citations` output routinely
   echoed the `[id]` bracket characters shown in the generation prompt's context
   formatting back into the citation string itself — e.g. returning
   `"[medication:MD-...]"` instead of `"medication:MD-..."`. The rule-based citation
   check (`cited_ids.issubset(graded_ids)`) then failed on a pure string-formatting
   mismatch, not a real grounding problem, needlessly burning a retry (and, with
   `mistral` not pulled yet at the time, actually erroring out entirely once escalation
   tried to reach it). **Fix**: added `clean_citation_ids()` in
   `agent_graph/nodes/generation.py`, normalizing every citation the moment it comes
   back from the model, so every downstream consumer (verification, later the API and
   UI) only ever sees clean ids.
2. *Not a bug — the safety mechanism working as designed*: after fixing (1), the same
   question ("what medications is this member on and what condition are they for")
   still correctly failed groundedness and exhausted all 3 retries, because the
   synthetic data model genuinely never links a medication to the condition it treats —
   `gold.member_medications_current` has no indication field, and the co-occurring
   diabetes notes only establish correlation, not an explicit stated link. Both llama3
   and mistral (after escalation) correctly refused to assert that connection rather
   than infer it, and the system correctly gave up with `low_confidence=True` instead
   of hallucinating an answer. This is worth stating plainly in an interview: strict
   citation-grounding here deliberately trades "helpfulness" (a human reading the same
   context would obviously connect the dots) for "safety" (never assert a clinical
   relationship that isn't explicitly documented) — the right trade for a healthcare
   system, and proof the retry loop's termination behavior is doing real work, not just
   passing synthetic tests.

**A small local model returned an internally-inconsistent structured output.** In the
same debugging session, `GroundednessJudgement.score` came back as `2.0` (outside the
documented 0.0-1.0 range) on one call, while `passed` was still correctly `False` -
i.e. the model didn't even self-consistently apply its own stated rubric ("passed if
score >= 0.7"). The original Pydantic field only had a `description`, not a value
constraint, so this would have silently propagated. **Fix**: added `ge=0.0, le=1.0` to
the `score` field so out-of-range values raise a validation error instead of silently
passing through - a small but real example of why structured output from small local
models needs schema-level guardrails, not just type hints, and a concrete answer to
"how do you handle small-model reliability" in an interview.

---

*(Phase 4 onward will be appended here as it's built.)*
