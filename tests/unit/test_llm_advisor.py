from types import SimpleNamespace

import ai_migration_accelerator.agents.llm_advisor_agent as llm_advisor_module
from ai_migration_accelerator.agents.llm_advisor_agent import run_llm_advisor
from ai_migration_accelerator.models.state import RunContext, WorkflowState


def test_llm_advisor_falls_back_without_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(
        llm_advisor_module,
        "get_settings",
        lambda: SimpleNamespace(google_api_key=None),
    )

    context = RunContext(
        source_type="postgresql",
        source_connection="postgresql+psycopg://u:p@localhost:5432/source",
        target_connection="postgresql+psycopg://u:p@localhost:5432/target",
        enable_llm_advisor=True,
    )
    state = WorkflowState(
        run_id="llm-fallback",
        context=context,
        schema_context={"table_profiles": [], "join_graph": []},
        mapping_plan={"selected_embedding_column": {"table": "orders", "column": "order_notes"}},
    )

    updated = run_llm_advisor(state)

    assert "advisor_notes.md" in updated.generated_artifacts
    assert any("GOOGLE_API_KEY" in message for message in updated.open_questions)
