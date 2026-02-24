from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from ai_migration_accelerator.api.run_store import (
    get_questions,
    get_status,
    set_questions,
    set_result,
    set_status,
)
from ai_migration_accelerator.core.settings import get_settings
from ai_migration_accelerator.graph.workflow import execute_workflow
from ai_migration_accelerator.models.contracts import (
    JobCreateRequest,
    JobCreateResponse,
    JobStatusResponse,
)
from ai_migration_accelerator.models.state import RunContext, RunStatus

router = APIRouter()


@router.post("", response_model=JobCreateResponse)
def create_job(request: JobCreateRequest) -> JobCreateResponse:
    run_id = str(uuid.uuid4())
    set_status(run_id, RunStatus.running)

    settings = get_settings()

    source_connection = request.source_connection or settings.source_connection
    target_connection = request.target_connection or settings.target_connection
    if source_connection is None or target_connection is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "source_connection and target_connection are required in request "
                "or must be configured in .env"
            ),
        )

    context = RunContext(
        source_type=request.source_type,
        source_connection=source_connection,
        target_connection=target_connection,
        ddl_text=request.ddl_text,
        enable_llm_advisor=(
            request.enable_llm_advisor
            if request.enable_llm_advisor is not None
            else settings.enable_llm_advisor
        ),
        llm_model=request.llm_model or settings.llm_model,
        include_sample_rows=(
            request.include_sample_rows
            if request.include_sample_rows is not None
            else settings.include_sample_rows
        ),
        sample_row_limit=(
            request.sample_row_limit
            if request.sample_row_limit is not None
            else settings.sample_row_limit
        ),
        embedding_model=request.embedding_model or settings.embedding_model,
        hf_token_env_var=request.hf_token_env_var or settings.hf_token_env_var,
        vector_table=request.vector_table or settings.vector_table,
        run_containerized_migration=(
            request.run_containerized_migration
            if request.run_containerized_migration is not None
            else settings.run_containerized_migration
        ),
        container_runtime=request.container_runtime or settings.container_runtime,
    )

    try:
        result = execute_workflow(run_id=run_id, context=context)
        set_status(run_id, RunStatus.completed)
        set_questions(run_id, result.open_questions)
        set_result(run_id, result)
    except Exception as exc:  # pragma: no cover - defensive surface for API
        set_status(run_id, RunStatus.failed)
        set_questions(run_id, [str(exc)])

    status = get_status(run_id)
    if status is None:
        raise HTTPException(status_code=500, detail="Job status unavailable")
    return JobCreateResponse(run_id=run_id, status=status)


@router.get("/{run_id}", response_model=JobStatusResponse)
def get_job_status(run_id: str) -> JobStatusResponse:
    status = get_status(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        run_id=run_id,
        status=status,
        open_questions=get_questions(run_id),
    )
