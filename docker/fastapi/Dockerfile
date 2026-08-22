# Shared image for both the fastapi and mcp services (docker-compose overrides
# `command:` per service) - they share the same requirements.txt and most of the
# same Python code (retrieval/, agent_graph/, model_routing/, llmops/).
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
# sentence-transformers pulls in torch, and a plain `pip install` on Linux defaults to
# the CUDA-enabled build (pulling several GB of unused nvidia-* packages) even though
# this container only ever does CPU inference for the MiniLM embedding model and
# Docker Desktop doesn't pass GPUs through anyway. Installing the CPU-only wheel first
# satisfies the dependency before requirements.txt would otherwise resolve the CUDA
# one - see CHALLENGES.md.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x docker/fastapi/entrypoint.sh

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["docker/fastapi/entrypoint.sh"]
CMD ["uvicorn", "api.fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]
