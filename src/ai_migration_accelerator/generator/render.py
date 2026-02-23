from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from ai_migration_accelerator.models.state import WorkflowState


def render_fastapi_pipeline(state: WorkflowState) -> WorkflowState:
    template_path = (
        Path(__file__).parent / "templates" / "fastapi_pipeline.py.j2"
    )
    template = Template(template_path.read_text(encoding="utf-8"))
    rendered = template.render(columns=state.mapping_plan.get("columns", []))
    state.generated_artifacts["generated_pipeline.py"] = rendered
    return state
