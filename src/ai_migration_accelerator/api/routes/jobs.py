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

    context = RunContext(
        source_type=request.source_type,
        source_connection=request.source_connection,
        target_connection=request.target_connection,
        ddl_text=request.ddl_text,
        enable_llm_advisor=request.enable_llm_advisor,
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
