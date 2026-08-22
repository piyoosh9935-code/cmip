import os

from llmops.langsmith.tracing import is_enabled


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    assert is_enabled() is False


def test_disabled_if_flag_set_but_no_key(monkeypatch):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    assert is_enabled() is False


def test_disabled_if_key_set_but_flag_not_true(monkeypatch):
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.setenv("LANGCHAIN_API_KEY", "fake-key")
    assert is_enabled() is False


def test_enabled_only_when_both_flag_and_key_present(monkeypatch):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "fake-key")
    assert is_enabled() is True


def test_repo_env_actually_has_no_langsmith_vars_set():
    """This is the real-world check that matters: as checked out, with no .env
    sourced, tracing must be off - not just off in a mocked test."""
    assert os.environ.get("LANGCHAIN_TRACING_V2", "").lower() != "true" or not (
        os.environ.get("LANGCHAIN_API_KEY") or os.environ.get("LANGSMITH_API_KEY")
    )
