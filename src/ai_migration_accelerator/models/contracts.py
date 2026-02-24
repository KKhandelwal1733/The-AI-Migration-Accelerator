from __future__ import annotations

from pydantic import BaseModel, Field

from ai_migration_accelerator.models.state import RunStatus


class JobCreateRequest(BaseModel):
    source_type: str = Field(pattern="^(oracle|postgresql)$")
    source_connection: str | None = None
    target_connection: str | None = None
    ddl_text: str | None = None
    enable_llm_advisor: bool | None = None
    llm_model: str | None = None
    include_sample_rows: bool | None = None
    sample_row_limit: int | None = Field(default=None, ge=0, le=50)
    embedding_model: str | None = None
    hf_token_env_var: str | None = None
    vector_table: str | None = None
    run_containerized_migration: bool | None = None
    container_runtime: str | None = Field(default=None, pattern="^(podman|docker)$")


class JobCreateResponse(BaseModel):
    run_id: str
    status: RunStatus


class JobStatusResponse(BaseModel):
    run_id: str
    status: RunStatus
    open_questions: list[str] = Field(default_factory=list)
