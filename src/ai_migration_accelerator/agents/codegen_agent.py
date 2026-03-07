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
        llm_join_plan=state.mapping_plan.get("llm_join_plan", []),
        business_filters=state.mapping_plan.get("business_filters", []),
        embedding_candidates=state.mapping_plan.get("embedding_candidates", []),
        selected_embedding_column=state.mapping_plan.get("selected_embedding_column", {}),
        selected_embedding_columns=state.mapping_plan.get("selected_embedding_columns", []),
        source_connection=state.context.source_connection,
        target_connection=state.context.target_connection,
        embedding_model=state.context.embedding_model,
        hf_token_env_var=state.context.hf_token_env_var,
        vector_table=state.context.vector_table,
    )

    state.generated_artifacts["migrate.py"] = rendered_script

    output_dir = Path(__file__).parents[3] / "generated_migrations" / state.run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "migrate.py"
    output_path.write_text(rendered_script, encoding="utf-8")
    state.generated_artifacts["migrate_script_path.txt"] = str(output_path)

    state.generated_artifacts["pipeline_summary.md"] = (
        f"Generated migrate.py for {len(state.mapping_plan.get('columns', []))} columns "
        f"across {len(state.mapping_plan.get('business_entities', []))} entities."
    )

    if state.context.enable_llm_advisor:
        state.generated_artifacts.setdefault(
            "advisor_notes.md",
            "LLM advisor enabled, but no advisor output was produced.",
        )
    return state
