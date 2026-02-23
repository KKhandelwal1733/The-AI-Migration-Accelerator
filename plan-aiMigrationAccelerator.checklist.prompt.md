## Plan: AI Migration Accelerator Multi-Agent MVP (DRAFT)

This plan implements your LangGraph-driven multi-agent system with ODI-style orchestration, Oracle/PostgreSQL source introspection, and PostgreSQL + pgvector as the primary target. Based on your decisions, MVP generation is Python FastAPI only, coordinator context sent to Gemini is metadata-only, and validation is structural smoke testing (record counts + schema parity). The design keeps deterministic template generation as the default artifact path while allowing optional advisory LLM assistance under strict schema-validated contracts.

## Steps (Checklist)
- [ ] Define project skeleton and module boundaries in [src/api](src/api), [src/graph](src/graph), [src/agents](src/agents), [src/connectors](src/connectors), [src/models](src/models), [src/generator](src/generator), [src/validation](src/validation), [ops](ops), and [tests](tests), with generator isolated as deterministic core.
- [ ] Create canonical state and contract models in [src/models/state.py](src/models/state.py), [src/models/contracts.py](src/models/contracts.py), and [src/models/artifacts.py](src/models/artifacts.py) for run context, metadata payloads, canonical schema, mapping plan, generation spec, validation report, and open-questions log.
- [ ] Implement ingestion interfaces in [src/connectors/oracle](src/connectors/oracle) and [src/connectors/postgres](src/connectors/postgres) for live metadata extraction plus DDL input parsing, then normalize both into a single canonical schema snapshot with provenance and extraction warnings.
- [ ] Build LangGraph workflow in [src/graph/workflow.py](src/graph/workflow.py) and [src/graph/router.py](src/graph/router.py) with nodes: CollectMetadata, NormalizeSchema, AnalyzeMappings, GenerateCode, RunValidation, and GateReview; include conditional retries and escalation path for unresolved mappings.
- [ ] Implement Schema Analyzer Agent in [src/agents/schema_analyzer.py](src/agents/schema_analyzer.py) using LangChain + Pydantic-validated rules to map legacy source types and constraints to PostgreSQL/pgvector-compatible target types and flags for lossy conversions.
- [ ] Implement Code Generation Agent in [src/agents/codegen_agent.py](src/agents/codegen_agent.py) and [src/generator/templates](src/generator/templates) to render FastAPI migration/chunking pipeline artifacts from mapping plans; keep deterministic templates primary and optional advisory LLM suggestions behind a feature flag.
- [ ] Implement Validation Agent in [src/agents/validation_agent.py](src/agents/validation_agent.py) and [src/validation/smoke.py](src/validation/smoke.py) for per-table record count checks, schema parity checks (columns/types/nullability), and machine-readable pass/fail reports.
- [ ] Expose orchestration APIs in [src/api/routes/jobs.py](src/api/routes/jobs.py) and [src/api/routes/artifacts.py](src/api/routes/artifacts.py) for run submission, status, artifact retrieval, and validation report retrieval.
- [ ] Add Podman runtime in [Containerfile](Containerfile) and [ops/podman-compose.yml](ops/podman-compose.yml) for app, worker, redis, and postgres/pgvector services, plus optional Oracle-connected integration profile.
- [ ] Document operational policy and constraints in [README.md](README.md) and [docs/architecture.md](docs/architecture.md), including metadata-only LLM policy, unsupported object handling, deterministic output guarantees, and escalation semantics.

## Verification (Checklist)
- [ ] Unit tests for contracts, normalization, mapping rules, and deterministic rendering in tests under [tests/unit](tests/unit).
- [ ] Integration tests for API + worker + graph execution + pgvector pipeline in [tests/integration](tests/integration) using Podman services.
- [ ] Oracle/PostgreSQL source connector smoke tests with controlled fixtures in [tests/e2e](tests/e2e).
- [ ] Reproducibility check: same input snapshot and config must produce identical artifact manifests.
- [ ] Validation acceptance check: generated reports must include table-level counts, schema parity results, and unresolved-item list.

## Decisions
- Coordinator orchestration uses LangGraph with Gemini as planner and metadata-only context.
- MVP generated runtime is FastAPI (Go deferred).
- Validation depth is structural smoke testing only.
- Primary target is PostgreSQL + pgvector with ODI-style staged pipeline artifacts.