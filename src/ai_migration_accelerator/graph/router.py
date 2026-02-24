from __future__ import annotations

from ai_migration_accelerator.models.state import WorkflowState


def should_validate(state: WorkflowState) -> str:
    if state.execution_report.get("status") == "failed":
        return "gate_review"
    return "run_validation"
