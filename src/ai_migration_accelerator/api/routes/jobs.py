from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from ai_migration_accelerator.graph.workflow import execute_workflow
from ai_migration_accelerator.models.contracts import (
    JobCreateRequest,
    JobCreateResponse,
    JobStatusResponse,
)
from ai_migration_accelerator.models.state import RunContext, RunStatus

router = APIRouter()

_RUN_STATUS: dict[str, RunStatus] = {}
_RUN_QUESTIONS: dict[str, list[str]] = {}


@router.post("", response_model=JobCreateResponse)
def create_job(request: JobCreateRequest) -> JobCreateResponse:
    run_id = str(uuid.uuid4())
    _RUN_STATUS[run_id] = RunStatus.running

    context = RunContext(
        source_type=request.source_type,
        source_connection=request.source_connection,
        target_connection=request.target_connection,
        ddl_text=request.ddl_text,
        enable_llm_advisor=request.enable_llm_advisor,
    )

    try:
        result = execute_workflow(run_id=run_id, context=context)
        _RUN_STATUS[run_id] = RunStatus.completed
        _RUN_QUESTIONS[run_id] = result.open_questions
    except Exception as exc:  # pragma: no cover - defensive surface for API
        _RUN_STATUS[run_id] = RunStatus.failed
        _RUN_QUESTIONS[run_id] = [str(exc)]

    return JobCreateResponse(run_id=run_id, status=_RUN_STATUS[run_id])


@router.get("/{run_id}", response_model=JobStatusResponse)
def get_job_status(run_id: str) -> JobStatusResponse:
    status = _RUN_STATUS.get(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        run_id=run_id,
        status=status,
        open_questions=_RUN_QUESTIONS.get(run_id, []),
    )
