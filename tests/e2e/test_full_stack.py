"""Full end-to-end smoke test against a running `docker compose up -d` stack - unlike
tests/api/ (which uses FastAPI's in-process TestClient), this hits the containerized
FastAPI over real HTTP on localhost:8000, exactly as an external client would, so it
actually exercises the container networking (fastapi -> postgres/qdrant/mlflow/mcp,
and out to host.docker.internal for Ollama) rather than the app code directly."""

import time

import httpx

API_BASE_URL = "http://localhost:8000"
LATENCY_BUDGET_MS = 60_000
MEMBER_ID = "M-00003"


def test_health_endpoint_reports_all_dependencies_up():
    resp = httpx.get(f"{API_BASE_URL}/health", timeout=10)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["postgres"] is True
    assert body["qdrant"] is True
    assert body["mcp_server"] is True
    assert any(body["ollama"].values())


def test_full_query_through_the_containerized_stack_is_grounded_and_within_budget():
    t0 = time.time()
    resp = httpx.post(
        f"{API_BASE_URL}/query",
        json={
            "member_id": MEMBER_ID,
            "question": "What medications is this member currently taking?",
            "max_retries": 0,
        },
        timeout=90,
    )
    elapsed_ms = (time.time() - t0) * 1000

    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"]
    assert body["citations"]
    assert body["groundedness_passed"] is True
    assert elapsed_ms < LATENCY_BUDGET_MS

    trace_resp = httpx.get(f"{API_BASE_URL}/trace/{body['trace_id']}", timeout=10)
    assert trace_resp.status_code == 200
    trace = trace_resp.json()
    assert trace["member_id"] == MEMBER_ID
    assert len(trace["trace"]) >= 4  # query_analysis, retrieval, grading, generation, verification


def test_members_endpoint_reachable_through_the_container():
    resp = httpx.get(f"{API_BASE_URL}/members?limit=3", timeout=10)
    assert resp.status_code == 200
    assert len(resp.json()) == 3
