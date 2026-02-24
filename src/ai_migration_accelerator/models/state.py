from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class RunContext(BaseModel):
    source_type: str = Field(description="oracle or postgresql")
    source_connection: str = Field(description="SQLAlchemy-compatible DSN")
    target_type: str = Field(default="postgresql+pgvector")
    target_connection: str = Field(description="Target SQLAlchemy-compatible DSN")
    ddl_text: str | None = None
    enable_llm_advisor: bool = False
    llm_model: str = "gemini-1.5-pro"
    include_sample_rows: bool = True
    sample_row_limit: int = 3
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    hf_token_env_var: str = "HF_TOKEN"
    vector_table: str = "rag_documents"
    run_containerized_migration: bool = False
    container_runtime: str = "podman"


class WorkflowState(BaseModel):
    run_id: str
    context: RunContext
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    schema_context: dict[str, Any] = Field(default_factory=dict)
    canonical_schema: dict[str, Any] = Field(default_factory=dict)
    mapping_plan: dict[str, Any] = Field(default_factory=dict)
    generated_artifacts: dict[str, str] = Field(default_factory=dict)
    execution_report: dict[str, Any] = Field(default_factory=dict)
    validation_report: dict[str, Any] = Field(default_factory=dict)
    open_questions: list[str] = Field(default_factory=list)
