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

### Optional: enable Gemini LLM advisor

Set environment variables before starting the API:

```bash
export GOOGLE_API_KEY=<your_api_key>
export LLM_MODEL=gemini-1.5-pro
```

`POST /jobs` now resolves defaults from `.env` for these fields:
- `enable_llm_advisor`
- `llm_model`
- `include_sample_rows`
- `sample_row_limit`
- `embedding_model`
- `hf_token_env_var`
- `vector_table`
- `run_containerized_migration`
- `container_runtime`
- `source_connection` / `target_connection` (if provided in `.env`)

Only these are accepted in `POST /jobs` payload for runtime override:
- `source_type`
- `source_connection`
- `target_connection`
- `ddl_text`
- `enable_llm_advisor`
- `include_sample_rows`
- `sample_row_limit`
- `run_containerized_migration`
- `container_runtime`
- `container_network_mode` (`auto`, `host`, `compose`)
- `container_network_name` (required for `compose`; optional for `auto`)

When `run_containerized_migration=true`, `container_network_mode=auto` rewrites loopback hosts
(`localhost`, `127.0.0.1`, `::1`) to the runtime host bridge
(`host.containers.internal` for Podman, `host.docker.internal` for Docker).

For compose service discovery (`oracle`, `postgres` hostnames), use:
- `container_network_mode=compose`
- `container_network_name=<your_compose_network>` (for example `ops_default`)

### Embeddings via Hugging Face sentence-transformers

The generated `migrate.py` uses `sentence-transformers` and reads the token from `.env`.

```bash
export HF_TOKEN=<your_huggingface_token>
export EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
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

## Real integration demo (Oracle + PostgreSQL)

1. Start the stack:

```bash
cd ops
podman compose -f podman-compose.yml up -d --build
```

2. Wait for Oracle XE startup (first boot can take a few minutes).

3. Seed Oracle with one command:

PowerShell (Windows):

```powershell
./seed_oracle.ps1
```

Bash:

```bash
chmod +x seed_oracle.sh
./seed_oracle.sh
```

4. Trigger migration planning through API:

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "oracle",
    "source_connection": "oracle+oracledb://accelerator:accelerator@oracle:1521/XEPDB1",
    "target_connection": "postgresql+psycopg://accelerator:accelerator@postgres:5432/accelerator",
    "ddl_text": "CREATE TABLE customers (id NUMBER, full_name VARCHAR2(120), notes VARCHAR2(4000));",
    "enable_llm_advisor": true
  }'
```

5. Use returned `run_id` to inspect outputs:

```bash
curl http://127.0.0.1:8000/jobs/<run_id>
curl http://127.0.0.1:8000/artifacts/<run_id>
```

6. Verify pgvector extension in Postgres:

```bash
podman compose -f podman-compose.yml exec postgres psql -U accelerator -d accelerator -c "\dx"
```
