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

    assert analyzed.mapping_plan["workflow_summary"]["detected_customer_orders_flow"]
    assert len(analyzed.mapping_plan["join_logic"]) >= 1
    candidates = analyzed.mapping_plan["embedding_candidates"]
    assert any(candidate["column"] == "order_notes" for candidate in candidates)
