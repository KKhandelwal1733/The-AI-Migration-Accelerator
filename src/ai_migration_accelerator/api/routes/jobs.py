from __future__ import annotations

import json
import threading
import time
import uuid

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ai_migration_accelerator.api.run_store import (
    clear_logs,
    get_logs,
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


def _build_context(request: JobCreateRequest) -> RunContext:
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

    return RunContext(
        source_type=request.source_type,
        source_connection=source_connection,
        target_connection=target_connection,
        ddl_text=request.ddl_text,
        business_logic_prompt=request.business_logic_prompt,
        enable_llm_advisor=(
            request.enable_llm_advisor
            if request.enable_llm_advisor is not None
            else settings.enable_llm_advisor
        ),
        llm_model=settings.llm_model,
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
        embedding_model=settings.embedding_model,
        hf_token_env_var=settings.hf_token_env_var,
        vector_table=settings.vector_table,
        run_containerized_migration=(
            request.run_containerized_migration
            if request.run_containerized_migration is not None
            else settings.run_containerized_migration
        ),
        container_runtime=request.container_runtime or settings.container_runtime,
        container_network_mode=(
            request.container_network_mode
            if request.container_network_mode is not None
            else settings.container_network_mode
        ),
        container_network_name=(
            request.container_network_name
            if request.container_network_name is not None
            else settings.container_network_name
        ),
    )


def _run_job(run_id: str, context: RunContext) -> None:
    try:
        result = execute_workflow(run_id=run_id, context=context)
        set_status(run_id, RunStatus.completed)
        set_questions(run_id, result.open_questions)
        set_result(run_id, result)
    except Exception as exc:  # pragma: no cover - defensive surface for API
        set_status(run_id, RunStatus.failed)
        set_questions(run_id, [str(exc)])


@router.post("", response_model=JobCreateResponse)
def create_job(request: JobCreateRequest) -> JobCreateResponse:
    run_id = str(uuid.uuid4())
    set_status(run_id, RunStatus.running)
    clear_logs(run_id)

    context = _build_context(request)
    _run_job(run_id, context)

    status = get_status(run_id)
    if status is None:
        raise HTTPException(status_code=500, detail="Job status unavailable")
    return JobCreateResponse(run_id=run_id, status=status)


@router.post("/async", response_model=JobCreateResponse)
def create_job_async(request: JobCreateRequest) -> JobCreateResponse:
    run_id = str(uuid.uuid4())
    set_status(run_id, RunStatus.running)
    clear_logs(run_id)

    context = _build_context(request)
    threading.Thread(target=_run_job, args=(run_id, context), daemon=True).start()

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


@router.get("/{run_id}/logs")
def get_job_logs(
    run_id: str,
    tail: int = Query(default=200, ge=1, le=5000),
) -> dict[str, object]:
    status = get_status(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")

    logs = get_logs(run_id)
    if not logs:
        return {
            "run_id": run_id,
            "status": status,
            "log_lines": 0,
            "logs": [],
        }

    tailed = logs[-tail:]
    return {
        "run_id": run_id,
        "status": status,
        "log_lines": len(tailed),
        "logs": tailed,
    }


@router.get("/{run_id}/logs/stream")
def stream_job_logs(run_id: str) -> StreamingResponse:
    status = get_status(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")

    def event_stream():
        sent_idx = 0
        terminal_states = {RunStatus.completed, RunStatus.failed}
        while True:
            logs = get_logs(run_id)
            while sent_idx < len(logs):
                payload = {"line": logs[sent_idx], "index": sent_idx}
                yield f"data: {json.dumps(payload)}\n\n"
                sent_idx += 1

            current_status = get_status(run_id)
            if current_status in terminal_states and sent_idx >= len(logs):
                yield f"event: done\ndata: {json.dumps({'status': str(current_status)})}\n\n"
                break

            time.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
