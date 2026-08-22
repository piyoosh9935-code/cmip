import os

import httpx
from langchain_ollama import ChatOllama

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

_clients: dict[str, ChatOllama] = {}


def get_chat_model(model_name: str, temperature: float = 0.0) -> ChatOllama:
    key = f"{model_name}:{temperature}"
    if key not in _clients:
        _clients[key] = ChatOllama(model=model_name, base_url=OLLAMA_BASE_URL, temperature=temperature)
    return _clients[key]


def check_models_available(models: list[str]) -> dict[str, bool]:
    """Fail-fast check against /api/tags rather than letting a missing model surface
    as a confusing timeout deep inside a graph run."""
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        available = {m["name"].split(":")[0] for m in resp.json().get("models", [])}
    except Exception:
        return {m: False for m in models}
    return {m: m in available for m in models}
