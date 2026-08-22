"""Integration tests against live infra via FastAPI's TestClient (in-process, but still
needs live Postgres/Qdrant/Ollama/MCP server - same pattern as the rest of this
project's tests, see README)."""

from fastapi.testclient import TestClient

from api.fastapi_app import app

client = TestClient(app)

MEMBER_ID = "M-00003"


def test_health_reports_all_dependencies_up():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["postgres"] is True
    assert body["qdrant"] is True
    assert body["mcp_server"] is True


def test_list_members_returns_rows():
    resp = client.get("/members?limit=5")
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 5
    assert {"member_id", "first_name", "last_name", "age", "plan_type"} <= members[0].keys()


def test_list_members_filters_by_cohort():
    resp = client.get("/members?cohort=diabetes&limit=50")
    assert resp.status_code == 200
    members = resp.json()
    assert members
    assert all("diabetes" in (m["cohorts"] or "") for m in members)


def test_get_member_detail_includes_all_sections():
    resp = client.get(f"/members/{MEMBER_ID}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["summary"]["member_id"] == MEMBER_ID
    assert "recent_claims" in detail
    assert "medications" in detail
    assert "recent_encounters" in detail
    assert "sdoh" in detail


def test_get_member_detail_404_for_unknown_member():
    resp = client.get("/members/M-99999")
    assert resp.status_code == 404


def test_query_returns_grounded_answer_and_persists_trace():
    resp = client.post(
        "/query",
        json={"member_id": MEMBER_ID, "question": "What medications is this member currently taking?", "max_retries": 0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"]
    assert body["trace_id"]

    trace_resp = client.get(f"/trace/{body['trace_id']}")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()
    assert trace["question"] == "What medications is this member currently taking?"
    assert trace["member_id"] == MEMBER_ID
    assert len(trace["trace"]) >= 4  # query_analysis, retrieval, grading, generation, verification


def test_query_on_unknown_member_does_not_crash_and_reports_low_confidence():
    resp = client.post(
        "/query", json={"member_id": "M-99999", "question": "What medications is this member taking?", "max_retries": 0}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["low_confidence"] is True
    assert body["citations"] == []


def test_trace_404_for_unknown_id():
    resp = client.get("/trace/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_eval_summary_reflects_the_golden_qa_run():
    resp = client.get("/eval/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["num_eval_runs"] >= 25
    assert 0.0 <= body["avg_precision_at_5"] <= 1.0
