from __future__ import annotations

from pydantic import BaseModel, Field

from ai_migration_accelerator.models.state import RunStatus


class JobCreateRequest(BaseModel):
    source_type: str = Field(pattern="^(oracle|postgresql)$")
    source_connection: str
    target_connection: str
    ddl_text: str | None = None
    enable_llm_advisor: bool = False
    llm_model: str = "gemini-1.5-pro"
    include_sample_rows: bool = True
    sample_row_limit: int = Field(default=3, ge=0, le=50)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    hf_token_env_var: str = "HF_TOKEN"
    vector_table: str = "rag_documents"
    run_containerized_migration: bool = False
    container_runtime: str = Field(default="podman", pattern="^(podman|docker)$")


class JobCreateResponse(BaseModel):
    run_id: str
    status: RunStatus


class JobStatusResponse(BaseModel):
    run_id: str
    status: RunStatus
    open_questions: list[str] = Field(default_factory=list)
