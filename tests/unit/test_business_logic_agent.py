from types import SimpleNamespace

import ai_migration_accelerator.agents.business_logic_agent as business_logic_module
from ai_migration_accelerator.agents.business_logic_agent import analyze_business_logic
from ai_migration_accelerator.models.state import RunContext, WorkflowState


def test_business_logic_prompt_infers_filters_via_llm(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr(
        business_logic_module,
        "get_settings",
        lambda: SimpleNamespace(google_api_key="test-key"),
    )

    class FakeLLM:
        def __init__(self, **_: object) -> None:
            pass

        def invoke(self, _: str) -> object:
            return SimpleNamespace(
                content=(
                    '{"filters": ['
                    '{"table":"product_feedback","column":"status","operator":"==","value":"Resolved"},'
                    '{"table":"customers","column":"tier","operator":"==","value":"Premium"}'
                    '], "notes": ["Applied requested status and tier filters."]}'
                )
            )

    monkeypatch.setattr(
        business_logic_module,
        "import_module",
        lambda _: SimpleNamespace(ChatGoogleGenerativeAI=FakeLLM),
    )

    context = RunContext(
        source_type="postgresql",
        source_connection="postgresql+psycopg://u:p@localhost:5432/source",
        target_connection="postgresql+psycopg://u:p@localhost:5432/target",
        business_logic_prompt='Only migrate "Resolved" feedback from "Premium" customers.',
    )

    state = WorkflowState(
        run_id="business-logic-test",
        context=context,
        schema_context={
            "table_profiles": [
                {
                    "name": "customers",
                    "columns": [
                        {"name": "cust_id", "type": "integer"},
                        {"name": "name", "type": "varchar"},
                        {"name": "tier", "type": "varchar"},
                    ],
                    "sample_rows": [
                        {"cust_id": 1, "name": "A", "tier": "Premium"},
                        {"cust_id": 2, "name": "B", "tier": "Basic"},
                    ],
                },
                {
                    "name": "product_feedback",
                    "columns": [
                        {"name": "feedback_id", "type": "integer"},
                        {"name": "cust_id", "type": "integer"},
                        {"name": "comments", "type": "text"},
                        {"name": "status", "type": "varchar"},
                    ],
                    "sample_rows": [
                        {"feedback_id": 1, "cust_id": 1, "comments": "Great", "status": "Resolved"},
                        {"feedback_id": 2, "cust_id": 2, "comments": "Bad", "status": "Pending"},
                    ],
                },
            ]
        },
        mapping_plan={},
    )

    updated = analyze_business_logic(state)
    filters = updated.mapping_plan.get("business_filters", [])

    assert any(
        f.get("column", "").lower() == "status" and str(f.get("value", "")).lower() == "resolved"
        for f in filters
    )
    assert any(
        f.get("column", "").lower() == "tier" and str(f.get("value", "")).lower() == "premium"
        for f in filters
    )
    assert updated.mapping_plan["business_logic_summary"]["parsing_mode"] == "llm"
    assert "business_logic_notes.md" in updated.generated_artifacts


def test_business_logic_prompt_fallback_without_llm_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(
        business_logic_module,
        "get_settings",
        lambda: SimpleNamespace(google_api_key=None),
    )

    context = RunContext(
        source_type="postgresql",
        source_connection="postgresql+psycopg://u:p@localhost:5432/source",
        target_connection="postgresql+psycopg://u:p@localhost:5432/target",
        business_logic_prompt="Migrate rows where status = Resolved",
    )

    state = WorkflowState(
        run_id="business-logic-fallback-test",
        context=context,
        schema_context={
            "table_profiles": [
                {
                    "name": "product_feedback",
                    "columns": [
                        {"name": "feedback_id", "type": "integer"},
                        {"name": "status", "type": "varchar"},
                    ],
                    "sample_rows": [],
                },
            ]
        },
        mapping_plan={},
    )

    updated = analyze_business_logic(state)
    filters = updated.mapping_plan.get("business_filters", [])

    assert any(
        f.get("column", "").lower() == "status" and str(f.get("value", "")).lower() == "resolved"
        for f in filters
    )
    assert updated.mapping_plan["business_logic_summary"]["parsing_mode"] == "prompt_pattern"
