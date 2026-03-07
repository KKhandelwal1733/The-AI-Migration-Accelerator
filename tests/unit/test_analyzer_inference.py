from ai_migration_accelerator.agents.schema_analyzer import analyze_schema
from ai_migration_accelerator.models.state import RunContext, WorkflowState


def test_infers_customer_orders_join_and_order_notes_embedding_candidate():
    context = RunContext(
        source_type="postgresql",
        source_connection="postgresql+psycopg://u:p@localhost:5432/source",
        target_connection="postgresql+psycopg://u:p@localhost:5432/target",
    )
    state = WorkflowState(
        run_id="inference-test",
        context=context,
        schema_context={
            "table_profiles": [
                {
                    "name": "customers",
                    "columns": [
                        {"name": "id", "type": "integer"},
                        {"name": "name", "type": "varchar"},
                    ],
                },
                {
                    "name": "orders",
                    "columns": [
                        {"name": "id", "type": "integer"},
                        {"name": "customer_id", "type": "integer"},
                        {"name": "order_notes", "type": "text"},
                    ],
                },
            ],
            "join_graph": [],
        },
    )

    analyzed = analyze_schema(state)

    assert analyzed.mapping_plan["workflow_summary"]["inferred_join_count"] >= 1
    assert len(analyzed.mapping_plan["join_logic"]) >= 1
    candidates = analyzed.mapping_plan["embedding_candidates"]
    assert any(candidate["column"] == "order_notes" for candidate in candidates)


def test_selects_multiple_embedding_columns_from_same_table():
    context = RunContext(
        source_type="postgresql",
        source_connection="postgresql+psycopg://u:p@localhost:5432/source",
        target_connection="postgresql+psycopg://u:p@localhost:5432/target",
    )
    state = WorkflowState(
        run_id="multi-embedding-test",
        context=context,
        schema_context={
            "table_profiles": [
                {
                    "name": "tickets",
                    "columns": [
                        {"name": "id", "type": "integer"},
                        {"name": "title", "type": "varchar"},
                        {"name": "comments", "type": "text"},
                        {"name": "notes", "type": "text"},
                        {"name": "description", "type": "text"},
                    ],
                },
            ],
            "join_graph": [],
        },
    )

    analyzed = analyze_schema(state)
    selected_columns = analyzed.mapping_plan["selected_embedding_columns"]

    assert "comments" in selected_columns
    assert "notes" in selected_columns
    assert "description" in selected_columns
    assert analyzed.mapping_plan["workflow_summary"]["selected_embedding_column_count"] >= 3
