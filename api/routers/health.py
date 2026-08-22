import httpx
from fastapi import APIRouter
from qdrant_client import QdrantClient
from sqlalchemy import text

from api.db import get_engine
from api.schemas import HealthResponse
from model_routing.ollama_client import check_models_available
from mcp_server.client import MCP_SERVER_URL
from retrieval.qdrant.schema import QDRANT_URL

router = APIRouter()


def _check_postgres() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("select 1"))
        return True
    except Exception:
        return False


def _check_qdrant() -> bool:
    try:
        QdrantClient(url=QDRANT_URL).get_collections()
        return True
    except Exception:
        return False


def _check_mcp_server() -> bool:
    try:
        base = MCP_SERVER_URL.rsplit("/mcp", 1)[0]
        resp = httpx.get(base, timeout=3)
        return resp.status_code < 500
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    postgres_ok = _check_postgres()
    qdrant_ok = _check_qdrant()
    ollama_status = check_models_available(["llama3", "mistral"])
    mcp_ok = _check_mcp_server()

    overall = "ok" if (postgres_ok and qdrant_ok and any(ollama_status.values())) else "degraded"
    return HealthResponse(status=overall, postgres=postgres_ok, qdrant=qdrant_ok, ollama=ollama_status, mcp_server=mcp_ok)
