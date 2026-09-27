.PHONY: venv install dbt-venv data dbt-run dbt-test ingest-qdrant ingest-bm25 api ui up down test hc-up hc-down learn-push

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

venv:
	python3.12 -m venv $(VENV)

install: venv
	$(PIP) install -r requirements-dev.txt

dbt-venv:
	cd ingestion/dbt_project && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Phase 1
data:
	$(PY) ingestion/synthetic_data_gen/generate.py

dbt-run:
	cd ingestion/dbt_project && .venv/bin/dbt run --profiles-dir .

dbt-test:
	cd ingestion/dbt_project && .venv/bin/dbt test --profiles-dir .

load-bronze:
	$(PY) ingestion/postgres/load_raw_to_bronze.py

# Phase 2
ingest-qdrant:
	$(PY) retrieval/qdrant/ingest.py

ingest-bm25:
	$(PY) retrieval/bm25/build_index.py

# Phase 4
mcp-server:
	$(PY) -m mcp_server.server

# Phase 5
golden-qa:
	$(PY) tests/eval/generate_golden_qa.py

eval:
	$(PY) -m llmops.mlflow.run_eval

# Phase 6
api:
	$(PY) -m uvicorn api.fastapi_app:app --reload --port 8000

# Phase 7
ui:
	cd frontend && npm run dev

# Phase 8
up:
	docker compose up -d

down:
	docker compose down

test:
	$(VENV)/bin/pytest tests/ -v

# Healthcare learning track
HC_COMPOSE := docker compose -f docker-compose.yml -f docker-compose.healthcare.yml

hc-up:
	$(HC_COMPOSE) up -d hapi-fhir oie

hc-down:
	$(HC_COMPOSE) stop hapi-fhir oie

# Commit + tag the day's session notes and lab code, then push to GitHub
learn-push:
	./learning/push.sh
