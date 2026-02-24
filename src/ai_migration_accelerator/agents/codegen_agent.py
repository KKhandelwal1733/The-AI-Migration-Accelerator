from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from ai_migration_accelerator.models.state import WorkflowState


def generate_code(state: WorkflowState) -> WorkflowState:
    template_path = Path(__file__).parents[1] / "generator" / "templates" / "migrate.py.j2"
    template = Template(template_path.read_text(encoding="utf-8"))

    rendered_script = template.render(
        columns=state.mapping_plan.get("columns", []),
        entities=state.mapping_plan.get("business_entities", []),
        joins=state.mapping_plan.get("join_logic", []),
        embedding_candidates=state.mapping_plan.get("embedding_candidates", []),
        selected_embedding_column=state.mapping_plan.get("selected_embedding_column", {}),
        source_connection=state.context.source_connection,
        target_connection=state.context.target_connection,
        embedding_api_url=state.context.embedding_api_url,
        embedding_model=state.context.embedding_model,
        vector_table=state.context.vector_table,
    )

    state.generated_artifacts["migrate.py"] = rendered_script
    state.generated_artifacts["pipeline_summary.md"] = (
        f"Generated migrate.py for {len(state.mapping_plan.get('columns', []))} columns "
        f"across {len(state.mapping_plan.get('business_entities', []))} entities."
    )

    if state.context.enable_llm_advisor:
        state.generated_artifacts["advisor_notes.md"] = (
            "LLM advisor is enabled in metadata-only mode for template hints."
        )
    return state
