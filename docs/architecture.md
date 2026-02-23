# Architecture (MVP)

## Orchestration

The system uses a coordinator-driven graph with these stages:

1. `collect_metadata`
2. `normalize_schema`
3. `analyze_mappings`
4. `generate_code`
5. `render_artifacts`
6. `run_validation` or `gate_review`

## Agents

- **Ingestion Engine**: parses DDL and prepares source metadata payloads.
- **Schema Analyzer Agent**: maps source types to PostgreSQL/pgvector-compatible target types.
- **Code Generation Agent**: renders deterministic FastAPI migration pipeline artifacts from templates.
- **Validation Agent**: performs structural smoke checks for migration readiness.

## Policies

- LLM advisor is optional and metadata-only for MVP.
- FastAPI is the default generated runtime.
- PostgreSQL + pgvector is the primary target backend.
- Validation scope is structural parity and row-count smoke checks.
