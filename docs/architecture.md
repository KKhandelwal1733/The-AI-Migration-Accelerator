# Architecture (MVP)

## Orchestration

The system uses a coordinator-driven graph with these stages:

1. `collect_metadata`
2. `normalize_schema`
3. `analyzer`
4. `llm_advisor` (Gemini via LangChain, optional)
5. `code_generator`
6. `infra_generator`
7. `executor`
8. `run_validation` or `gate_review`

## Agents

- **Ingestion Engine / Python Introspector**: uses SQLAlchemy `inspect` against source DB to discover tables, columns, PK/FK relationships, and sample rows.
- **Schema Context Builder**: transforms raw metadata into structured LLM context with table profiles and join graph.
- **Analyzer Agent**: infers business entities, join logic (`Customer` + `Orders` patterns), and embedding-candidate text columns (for example `order_notes`).
- **LLM Advisor Agent**: uses Gemini (`ChatGoogleGenerativeAI`) to refine join strategy and selected embedding column with deterministic fallback.
- **Code Generation Agent**: generates standalone `migrate.py` that performs joins, calls an embedding API, and pushes vectors to target PostgreSQL/pgvector.
- **Infra Generator Agent**: generates `Dockerfile` and `requirements.txt` for the generated script.
- **Execution Agent**: builds/runs the generated container (or simulates when runtime execution is disabled).
- **Validation Agent**: validates migration counts and confirms loss percentage target (0% for successful run).

## Runtime State & API Gateway

- FastAPI exposes control-plane endpoints for triggering and monitoring migration runs.
- Job state is persisted in an in-memory run store for MVP (`status`, `open_questions`, `generated_artifacts`, `execution_report`, `validation_report`).
- `/jobs` accepts direct source connection, embedding settings, and execution mode; then runs the full graph.
- `/artifacts/{run_id}` returns generated `migrate.py`, infra artifacts, and validation output.

## Policies

- LLM advisor is optional and metadata-only, enabled with `GOOGLE_API_KEY` and `llm_model`.
- FastAPI is the default generated runtime.
- PostgreSQL + pgvector is the primary target backend.
- Validation includes structural checks plus migration loss percentage checks from execution report.
