"""Integration tests against live infra - requires `docker compose up -d postgres
qdrant` plus `make ingest-qdrant ingest-bm25` to have been run first (see README)."""

from retrieval.bm25.retriever import BM25MemberRetriever
from retrieval.ensemble_retriever import build_ensemble_retriever
from retrieval.qdrant.retriever import QdrantMemberRetriever
from retrieval.sql_retriever.retriever import SQLMemberRetriever

MEMBER_ID = "M-00003"  # deterministic synthetic member with a diabetes cohort


def test_qdrant_and_bm25_return_results_for_known_member():
    assert QdrantMemberRetriever(member_id=MEMBER_ID, k=5).invoke("diabetes management")
    assert BM25MemberRetriever(member_id=MEMBER_ID, k=5).invoke("diabetes management")


def test_sql_retriever_classifies_intent_and_returns_rows():
    docs = SQLMemberRetriever(member_id=MEMBER_ID, k=5).invoke("what medications is this member on")
    assert docs
    assert docs[0].metadata["intent"] == "medication_list"


def test_ensemble_returns_fused_results_from_multiple_sources():
    docs = build_ensemble_retriever(MEMBER_ID, k=3).invoke(
        "how is this member managing diabetes and what medications are they on"
    )
    assert docs
    sources = {d.metadata.get("source") for d in docs}
    assert sources <= {"qdrant", "bm25", "sql"}
    assert len(sources) >= 2  # this query should pull from more than one retriever


def test_ensemble_is_scoped_to_the_requested_member_only():
    docs = build_ensemble_retriever(MEMBER_ID, k=5).invoke("diabetes")
    for doc in docs:
        assert doc.metadata.get("member_id", MEMBER_ID) == MEMBER_ID


def test_ensemble_weights_change_ranking():
    query = "diabetes management and medications"
    vector_heavy = build_ensemble_retriever(MEMBER_ID, k=5, weights=[0.9, 0.05, 0.05]).invoke(query)
    sql_heavy = build_ensemble_retriever(MEMBER_ID, k=5, weights=[0.05, 0.05, 0.9]).invoke(query)
    assert [d.page_content for d in vector_heavy] != [d.page_content for d in sql_heavy]
