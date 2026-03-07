from types import SimpleNamespace
from datetime import datetime

import ai_migration_accelerator.agents.llm_advisor_agent as llm_advisor_module
from ai_migration_accelerator.agents.llm_advisor_agent import _build_prompt, run_llm_advisor
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


def test_build_prompt_serializes_datetime_in_schema_context():
    context = RunContext(
        source_type="postgresql",
        source_connection="postgresql+psycopg://u:p@localhost:5432/source",
        target_connection="postgresql+psycopg://u:p@localhost:5432/target",
    )
    state = WorkflowState(
        run_id="llm-prompt-datetime",
        context=context,
        schema_context={
            "table_profiles": [
                {
                    "name": "events",
                    "columns": [{"name": "created_at", "type": "timestamp"}],
                    "sample_rows": [{"created_at": datetime(2026, 3, 7, 12, 30, 45)}],
                }
            ],
            "join_graph": [],
        },
        mapping_plan={"selected_embedding_column": {"table": "events", "column": "created_at"}},
    )

    prompt = _build_prompt(state)

    assert "2026-03-07T12:30:45" in prompt
