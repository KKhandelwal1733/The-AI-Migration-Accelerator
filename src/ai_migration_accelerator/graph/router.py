from __future__ import annotations

from ai_migration_accelerator.models.state import WorkflowState


def should_validate(state: WorkflowState) -> str:
    if state.open_questions:
        return "gate_review"
    return "run_validation"
