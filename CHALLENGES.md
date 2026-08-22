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

## Phase 4 — MCP Server + Router Agent

**The MCP SDK doesn't serialize a `list[dict]` tool return as one JSON array — it
splits it into one text block per list item.** Calling `get_member_claims` (which
returns `list[dict]`) produced a `CallToolResult` with N separate `TextContent` blocks,
each one JSON object, not one block containing a JSON array. My first client
implementation joined blocks with `"\n"`, which produces syntactically invalid,
concatenated JSON for any multi-row result - caught immediately by an integration test
(`json.decoder.JSONDecodeError: Extra data`). **Fix**: use `result.structured_content`
instead (present alongside the text blocks, wrapped as `{"result": ...}`), which
carries the tool's actual return value as real structured data regardless of shape -
more robust than reconstructing from text blocks, and it's what the SDK generates the
tool's output schema from in the first place.

**Design tools for what an *agent* needs to chain, not just what a human wants to
read.** The `claims_history` template originally returned `provider_name` and
`provider_specialty` but not `provider_id` - fine for a human-readable claim summary,
but it meant an agent trying to chain "get a claim, then look up that claim's
provider" had no join key to pass to `get_provider_info`. This only surfaced by
actually running the agentic path end-to-end and watching a real tool-calling attempt
fail, not from reading the code. **Fix**: added `provider_id` to the `claims_history`
query. General lesson: a tool's return schema is part of the *agent's* interface
contract, not just a human-facing display concern - review it from "what would the
next tool call need" as well as "is this readable."

**Plain `llama3:latest` on Ollama doesn't support tool-calling at all.** Attempting to
run the agentic router path with `llama3` failed immediately with `ResponseError:
registry.ollama.ai/library/llama3:latest does not support tools (status code: 400)` -
the base Llama 3 chat template Ollama ships predates native function-calling support
(later variants and other model families do support it; `mistral` does). This is a
real constraint on the resume's "heuristic routing between Llama and Mistral" design:
the *deterministic* path (state_graph.py) never calls `.bind_tools()` so it works with
either model, but the *agentic* MCP path can only ever run on tool-calling-capable
models - documented here rather than only discovered by a confused user.

**Real, reproducible evidence that small local models are unreliable at genuine
multi-hop tool chaining - validating a trade-off the plan predicted in advance, not
just asserting it.** With `mistral` (which does support tool-calling) driving the
agentic path on "look up this member's most recent claim, then look up the provider
who submitted it": the model correctly issued the *first* tool call, but for the
second call passed the literal string `"[provider_id_from_previous_response]"` as the
`provider_id` argument - a template placeholder, not an extracted value - instead of
reading the actual id out of the first tool's JSON result. Strengthening the system
prompt with an explicit "copy the literal value, never a placeholder" instruction was
tried and made things *worse*: on the next run the model didn't attempt a second tool
call at all, instead narrating a pseudo-code plan as plain text. This is a known
failure mode for ~7B instruct models doing ReAct-style orchestration, and it's exactly
why the router agent's *default* path is the deterministic ensemble-retrieval flow
(state_graph.py), with the agentic MCP path reserved as an optional, explicitly
lower-reliability fallback for genuinely multi-hop questions a single retrieval call
can't answer - not the primary path. The underlying MCP protocol integration itself
(tool discovery, real streamable-http round trips, LangGraph `create_react_agent`
wiring) is solid and independently tested; the unreliable part is specifically small
local models' multi-step reasoning, which is a model-capability limit, not a wiring
bug - worth being precise about the difference in an interview.

## Phase 5 — MLflow Logging + Eval Set

**MLflow 3.x's server binds to `127.0.0.1` inside the container by default - a new
security default that silently breaks Docker port forwarding.** `docker compose up -d
mlflow` started cleanly and looked healthy in its own logs, but the container's
`mlflow server` process was listening on its own loopback interface, which Docker's
`ports: ["5001:5000"]` mapping forwards *to* the container's network interface, not
into its loopback - so nothing outside the container could ever reach it, with no
error on either side to point at why. **Fix**: added `--host 0.0.0.0` to the compose
command, matching what MLflow's own CLI help text calls out under "Exposed beyond
LAN." A reminder that a healthy-looking container log doesn't mean the port mapping
around it actually works - worth an explicit `curl` from outside the container as part
of the verification step, not just checking the container's own log output.

**Artifact logging failed with `Read-only file system: '/mlflow'` - the exact minio/S3
gap the plan had already flagged for Phase 8, just discovered earlier than expected.**
`mlflow.log_param`/`log_metric` worked fine (they go over the tracking HTTP API), but
`mlflow.log_dict(...)` (used to persist each run's full pipeline trace as an artifact)
tried to write directly to the literal path `/mlflow/...` - which exists inside the
mlflow container, not on the host machine actually running this Python client. Root
cause: the compose command used `--default-artifact-root /mlflow`, a bare filesystem
path, which makes MLflow hand every experiment a literal `/mlflow/...` artifact URI
that only a co-located (or volume-shared) client can write to - the wrong assumption
for a client running on the host talking to a server in a container. **Fix**: switched
to `--artifacts-destination /mlflow` instead (MLflow's own artifact-serving *proxy*
target, distinct from `--default-artifact-root`) with `--serve-artifacts` left at its
default-on state, so new experiments get the proxied `mlflow-artifacts:/` scheme and
every artifact read/write is routed through the tracking server's HTTP API instead of
requiring direct filesystem access. Verified both directions explicitly (not just "no
exception raised"): logged a trace artifact from the host, then used
`MlflowClient.download_artifacts` to pull it back and confirmed the content matched.
This also meant wiping the `mlflow_data` volume, since the experiment created under the
old (broken) config had its bad artifact root baked into its metadata permanently -
not something a server restart alone fixes, only acceptable here because it was dev
data from earlier in the same session, not anything worth preserving.

**Ground truth for precision@k/recall@k comes from the synthetic generator's own
cohort assignment, not hand-labeling.** For a real clinical corpus, "is this note
relevant to this question" is a judgment call needing a human or an LLM judge. Here,
the synthetic data generator (`ingestion/synthetic_data_gen/notes.py`) already stamps
every note with an unambiguous `cohort_tag` at creation time - so `tests/eval/
golden_qa.jsonl` (generated deterministically by
`tests/eval/generate_golden_qa.py`, not hand-authored) uses "does this note's
cohort_tag match the cohort the eval question is about" as ground truth. This is a
legitimate methodology specifically *because* the corpus is synthetic and the labels
are generated, not inferred - worth stating plainly rather than implying it's
equivalent to hand-labeled real clinical text. Result against the current corpus:
avg precision@5 = 0.976, avg recall@5 = 0.962 across 25 questions spanning all 5
cohorts - strong, but expected, since cohort-scoped questions on cohort-tagged
synthetic notes is close to retrieval's easiest case; a genuinely adversarial eval set
(ambiguous or cross-cohort questions) would be a natural next iteration.

## Phase 6 — FastAPI Service

The cleanest phase so far - no new bugs surfaced, which is itself worth noting rather
than skipping: every endpoint (`/health`, `/members`, `/members/{id}`, `/query`,
`/trace/{id}`, `/eval/summary`) is a thin wrapper over code already built and
integration-tested in Phases 1-5 (`retrieval/sql_retriever/templates.py`,
`agent_graph/state_graph.py`, `llmops/mlflow/experiment.py`), so there was very little
genuinely new surface area for bugs to hide in. One deliberate design note worth
stating: `/query`'s route handler is a synchronous `def`, not `async def`, and the
compiled LangGraph app (`_app = build_graph(get_chat_model)`) is built once at module
import time and reused across requests rather than rebuilt per call. Starlette runs
sync path operations in a thread pool, and the actual per-node work is either a
network call to Ollama/Qdrant/Postgres (I/O-bound, releases the GIL while waiting) or
cheap local computation - so concurrent requests are not serialized behind a single
in-process LLM call the way a naive read might suggest. Verified end-to-end with a
live `curl` against every endpoint (not just the pytest suite) before considering the
phase done, including the two failure paths that matter most for a healthcare API:
an unknown member_id (`/members/{id}` returns 404; `/query` degrades to
`low_confidence: true` with an honest "not enough information" answer rather than
crashing or hallucinating) and an unknown trace_id (404).

---

## Phase 7 — Next.js Frontend

**Current Next.js requires Node ≥20.9.0; the machine's system Node was 18.18.0.**
`npx create-next-app` scaffolded the project but then failed on its post-install
`next typegen` step with `You are using Node.js 18.18.0. For Next.js, Node.js version
">=20.9.0" is required.` Installed `node@22` via Homebrew (LTS, actively supported, vs.
the also-available `node@20` which is deprecated upstream and scheduled for removal in
~2 months) as a keg-only formula and used it via explicit `PATH` prepending for
frontend commands specifically - the existing system Node at `/usr/local/bin/node`
(potentially relied on by other projects on this machine) was left untouched.

**A stale first `npm install` (run under the too-old Node before the fix above)
corrupted the platform-native dependency resolution in a way a second `npm install`
alone didn't fix.** `next dev` failed with `Cannot find module
'@tailwindcss/oxide-darwin-arm64'` - a known class of npm bug where optional
platform-specific native dependencies don't resolve correctly, often after an
engine-mismatched install. Deleting `node_modules` and `package-lock.json` and
reinstalling with Node 22's npm fixed the dependency itself (confirmed present on
disk afterward), but the *exact same error* persisted on the next `next dev` - because
Turbopack's `.next/` build cache still referenced the broken pre-fix module graph.
Clearing `.next/` in addition to reinstalling was what actually fixed it. Lesson
carried over from the MLflow/Postgres debugging earlier in this project: when a fix
doesn't take effect, check for a *cache* still holding the old broken state before
assuming the fix itself is wrong.

**Tailwind v4's CSS-based dark-mode default silently made the UI unreadable.**
`create-next-app`'s generated `globals.css` follows `prefers-color-scheme: dark` and
swaps to a dark background automatically - but every component written for this
project uses light-mode-only Tailwind utility classes (`text-neutral-900`, `bg-white`,
...) with no `dark:` variants. On a system in dark mode, the result was dark gray text
on a near-black background - technically rendering, but nearly unreadable, and not
something a static code review would have caught (the components' JSX is correct
light-mode markup; the bug was purely in the unrelated CSS file's media query). Caught
only by actually taking a screenshot of the running page, not by reading the code.
**Fix**: removed the `prefers-color-scheme: dark` block, documented inline in
`globals.css` why - full dark-mode support was out of scope for this phase and doing
it properly means adding `dark:` variants throughout every component, not just
patching the root CSS variables.

**Verification wasn't "does it compile" - it was an actual browser walkthrough.**
`npm run build` (production build + TypeScript check) and `npm run lint` both passed
clean the entire time these three issues existed, because none of them are type or
lint errors - a missing native binary is a runtime module-resolution failure, and
unreadable dark-on-dark text is a rendering/CSS issue. All three were only caught by
opening the app in a real browser and looking at it (and, for the module error,
reading the actual dev-server error overlay). Verified end-to-end afterward: member
picker with cohort filtering, navigating into a Member 360 page, asking a question via
both a suggestion chip and free-text input, and watching a real multi-retry pipeline
run (routed to mistral, weights shifting) render correctly in the trace panel.

---

*(Phase 8 onward will be appended here as it's built.)*
