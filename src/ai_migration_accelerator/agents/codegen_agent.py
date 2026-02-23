from __future__ import annotations

from ai_migration_accelerator.models.state import WorkflowState


def generate_code(state: WorkflowState) -> WorkflowState:
    column_count = len(state.mapping_plan.get("columns", []))
    state.generated_artifacts["pipeline_summary.md"] = (
        f"Generated migration pipeline for {column_count} mapped columns."
    )
    if state.context.enable_llm_advisor:
        state.generated_artifacts["advisor_notes.md"] = (
            "LLM advisor is enabled in metadata-only mode."
        )
    return state
