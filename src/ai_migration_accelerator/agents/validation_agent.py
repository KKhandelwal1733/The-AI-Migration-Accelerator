from __future__ import annotations

from ai_migration_accelerator.validation.smoke import build_smoke_report
from ai_migration_accelerator.models.state import WorkflowState


def run_validation(state: WorkflowState) -> WorkflowState:
    state.validation_report = build_smoke_report(state)
    return state
