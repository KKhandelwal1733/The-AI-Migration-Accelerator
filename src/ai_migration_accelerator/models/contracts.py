from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ai_migration_accelerator.models.state import RunStatus


class JobCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str = Field(pattern="^(oracle|postgresql)$")
    source_connection: str | None = None
    target_connection: str | None = None
    ddl_text: str | None = None
    business_logic_prompt: str | None = None
    enable_llm_advisor: bool | None = None
    include_sample_rows: bool | None = None
    sample_row_limit: int | None = Field(default=None, ge=0, le=50)
    run_containerized_migration: bool | None = None
    container_runtime: str | None = Field(default=None, pattern="^(podman|docker)$")


class JobCreateResponse(BaseModel):
    run_id: str
    status: RunStatus


class JobStatusResponse(BaseModel):
    run_id: str
    status: RunStatus
    open_questions: list[str] = Field(default_factory=list)
