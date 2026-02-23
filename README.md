# AI Migration Accelerator

LangGraph-based multi-agent migration assistant for legacy schemas to vector-ready PostgreSQL (`pgvector`).

## Current MVP Bootstrap

- FastAPI control plane with job and artifact endpoints.
- LangGraph orchestration pipeline with specialized agents:
  - Ingestion (DDL-aware metadata collection)
  - Schema Analyzer (legacy-to-target mapping)
  - Code Generation (deterministic template rendering)
  - Validation (structural smoke checks)
- Podman local stack for app + Postgres/pgvector + Redis.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn ai_migration_accelerator.main:app --reload
```

## Run tests

```bash
pytest -q
```

## Podman

```bash
cd ops
podman compose -f podman-compose.yml up --build
```
