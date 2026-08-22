import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.db import ensure_traces_table
from api.routers import eval, health, members, query, trace
from llmops.langsmith.tracing import maybe_enable_langsmith

CORS_ALLOW_ORIGINS = os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_traces_table()
    maybe_enable_langsmith()
    yield


app = FastAPI(title="CMIP API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(members.router)
app.include_router(query.router)
app.include_router(trace.router)
app.include_router(eval.router)
