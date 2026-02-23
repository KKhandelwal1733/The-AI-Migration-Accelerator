from __future__ import annotations

from pydantic import BaseModel, Field

from ai_migration_accelerator.models.state import RunStatus


class JobCreateRequest(BaseModel):
    source_type: str = Field(pattern="^(oracle|postgresql)$")
    source_connection: str
    target_connection: str
    ddl_text: str | None = None
    enable_llm_advisor: bool = False


class JobCreateResponse(BaseModel):
    run_id: str
    status: RunStatus


class JobStatusResponse(BaseModel):
    run_id: str
    status: RunStatus
    open_questions: list[str] = Field(default_factory=list)
