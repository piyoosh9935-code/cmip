"""LangSmith is strictly opt-in - see README "Tracing". LangChain's own SDK already
gates client initialization on these env vars (it does not initialize a LangSmith
client or make any network call unless both are set), so "enabling" tracing here is
mostly about making that behavior visible and logged, not implementing the gate
ourselves - duplicating it would risk drifting out of sync with LangChain's own logic."""

import os


def is_enabled() -> bool:
    return os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true" and bool(
        os.environ.get("LANGCHAIN_API_KEY") or os.environ.get("LANGSMITH_API_KEY")
    )


def maybe_enable_langsmith() -> bool:
    """Call once at startup. Returns whether tracing is active, and logs a one-line
    confirmation either way so it's never a silent, unverifiable state."""
    if is_enabled():
        project = os.environ.get("LANGCHAIN_PROJECT", "default")
        print(f"[langsmith] tracing ENABLED (project={project!r}) - traces will be sent to smith.langchain.com")
        return True
    print("[langsmith] tracing disabled (LANGCHAIN_TRACING_V2/LANGCHAIN_API_KEY not set) - no external calls will be made")
    return False
