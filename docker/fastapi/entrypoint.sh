#!/bin/sh
# The BM25 index (retrieval/bm25/index/bm25_index.pkl) is a client-side pickle built
# from Postgres data - it's gitignored/dockerignored as a generated artifact, so it
# never ships in the image. Build it fresh at container startup instead of requiring a
# host bind-mount, so `docker compose up` is self-sufficient as long as Postgres
# already has gold-layer data (true by the time this runs, per the documented setup
# order - ingestion/dbt happen before `docker compose up` brings up fastapi/mcp).
set -e
echo "Building BM25 index from Postgres..."
python -m retrieval.bm25.build_index

exec "$@"
