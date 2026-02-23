from __future__ import annotations

from ai_migration_accelerator.models.state import RunStatus, WorkflowState

_RUN_STATUS: dict[str, RunStatus] = {}
_RUN_QUESTIONS: dict[str, list[str]] = {}
_RUN_RESULTS: dict[str, WorkflowState] = {}


def set_status(run_id: str, status: RunStatus) -> None:
    _RUN_STATUS[run_id] = status


def get_status(run_id: str) -> RunStatus | None:
    return _RUN_STATUS.get(run_id)


def set_questions(run_id: str, open_questions: list[str]) -> None:
    _RUN_QUESTIONS[run_id] = open_questions


def get_questions(run_id: str) -> list[str]:
    return _RUN_QUESTIONS.get(run_id, [])


def set_result(run_id: str, result: WorkflowState) -> None:
    _RUN_RESULTS[run_id] = result


def get_result(run_id: str) -> WorkflowState | None:
    return _RUN_RESULTS.get(run_id)
