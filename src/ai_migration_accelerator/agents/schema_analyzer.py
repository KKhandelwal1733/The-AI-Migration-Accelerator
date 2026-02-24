from __future__ import annotations

from ai_migration_accelerator.models.state import WorkflowState


def map_type(source_type: str) -> str:
    normalized = source_type.lower()
    mapping = {
        "varchar": "text",
        "varchar2": "text",
        "number": "numeric",
        "blob": "vector_embedding",
    }
    return mapping.get(normalized, "text")


def _find_table(table_profiles: list[dict[str, object]], keyword: str) -> dict[str, object] | None:
    for table in table_profiles:
        table_name = str(table.get("name", "")).lower()
        if keyword in table_name:
            return table
    return None


def _infer_customer_orders_join(
    table_profiles: list[dict[str, object]],
    join_logic: list[dict[str, object]],
) -> list[dict[str, object]]:
    inferred = list(join_logic)
    customers = _find_table(table_profiles, "customer")
    orders = _find_table(table_profiles, "order")
    if customers is None or orders is None:
        return inferred

    existing = any(
        str(edge.get("from", "")).lower() in {str(customers.get("name", "")).lower(), str(orders.get("name", "")).lower()}
        and str(edge.get("to", "")).lower() in {str(customers.get("name", "")).lower(), str(orders.get("name", "")).lower()}
        for edge in join_logic
    )
    if existing:
        return inferred

    order_columns = [str(column.get("name", "")).lower() for column in orders.get("columns", [])]
    join_column = "customer_id" if "customer_id" in order_columns else "id"
    inferred.append(
        {
            "from": orders.get("name"),
            "to": customers.get("name"),
            "on": {"from_columns": [join_column], "to_columns": ["id"]},
            "inferred": True,
        }
    )
    return inferred


def _embedding_candidates(table_profiles: list[dict[str, object]]) -> list[dict[str, str]]:
    keywords = {"note", "notes", "description", "comment", "summary", "text", "details"}
    candidates: list[dict[str, str]] = []
    for table in table_profiles:
        table_name = str(table.get("name", ""))
        for column in table.get("columns", []):
            column_name = str(column.get("name", ""))
            lowered = column_name.lower()
            if any(keyword in lowered for keyword in keywords):
                candidates.append({"table": table_name, "column": column_name})
    return candidates


def analyze_schema(state: WorkflowState) -> WorkflowState:
    table_profiles = state.schema_context.get("table_profiles", [])
    join_graph = state.schema_context.get("join_graph", [])

    mapped_columns: list[dict[str, str]] = []
    business_entities: list[dict[str, object]] = []

    for table in table_profiles:
        table_name = table.get("name", "unknown")
        columns = table.get("columns", [])

        business_entities.append(
            {
                "entity": str(table_name).replace("_", " ").title(),
                "table": table_name,
                "attributes": [column.get("name") for column in columns],
            }
        )

        for column in columns:
            mapped_columns.append(
                {
                    "table": str(table_name),
                    "column": str(column.get("name")),
                    "source_type": str(column.get("type", "text")),
                    "target_type": map_type(str(column.get("type", "text"))),
                }
            )

    join_logic = [
        {
            "from": edge.get("from_table"),
            "to": edge.get("to_table"),
            "on": {
                "from_columns": edge.get("from_columns", []),
                "to_columns": edge.get("to_columns", []),
            },
        }
        for edge in join_graph
    ]

    join_logic = _infer_customer_orders_join(table_profiles, join_logic)
    embedding_candidates = _embedding_candidates(table_profiles)

    if not embedding_candidates:
        state.open_questions.append(
            "No obvious text-like column found for embedding; using first text-compatible column fallback."
        )

    target_candidate = embedding_candidates[0] if embedding_candidates else {"table": "", "column": ""}

    state.mapping_plan = {
        "columns": mapped_columns,
        "business_entities": business_entities,
        "join_logic": join_logic,
        "embedding_candidates": embedding_candidates,
        "selected_embedding_column": target_candidate,
        "workflow_summary": {
            "detected_customer_orders_flow": bool(_find_table(table_profiles, "customer") and _find_table(table_profiles, "order")),
            "join_count": len(join_logic),
            "embedding_candidate_count": len(embedding_candidates),
        },
    }
    return state
