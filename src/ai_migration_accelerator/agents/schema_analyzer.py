from __future__ import annotations

from typing import Any

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


def _infer_joins_from_conventions(
    table_profiles: list[dict[str, object]],
    join_logic: list[dict[str, object]],
) -> list[dict[str, object]]:
    inferred = list(join_logic)

    def _columns_from_edge(edge: dict[str, object], key: str) -> list[str]:
        on_payload = edge.get("on")
        if not isinstance(on_payload, dict):
            return []
        raw_columns = on_payload.get(key, [])
        if not isinstance(raw_columns, list):
            return []
        return [str(value).lower() for value in raw_columns]

    existing_signatures = {
        (
            str(edge.get("from", "")).lower(),
            str(edge.get("to", "")).lower(),
            tuple(_columns_from_edge(edge, "from_columns")),
            tuple(_columns_from_edge(edge, "to_columns")),
        )
        for edge in join_logic
    }

    tables_by_name = {
        str(table.get("name", "")).lower(): table
        for table in table_profiles
        if str(table.get("name", ""))
    }

    for table in table_profiles:
        from_table_name = str(table.get("name", ""))
        if not from_table_name:
            continue

        columns_payload = table.get("columns", [])
        if not isinstance(columns_payload, list):
            continue
        columns: list[dict[str, Any]] = [
            column for column in columns_payload if isinstance(column, dict)
        ]
        for column in columns:
            column_name = str(column.get("name", "")).lower()
            if not column_name.endswith("_id") or column_name == "id":
                continue

            candidate_root = column_name[:-3]
            target_candidates = [candidate_root, f"{candidate_root}s", f"{candidate_root}es"]

            for target_candidate in target_candidates:
                target_table = tables_by_name.get(target_candidate)
                if target_table is None:
                    continue

                target_table_name = str(target_table.get("name", ""))
                target_columns_payload = target_table.get("columns", [])
                if not isinstance(target_columns_payload, list):
                    continue
                target_columns = {
                    str(target_column.get("name", "")).lower()
                    for target_column in target_columns_payload
                    if isinstance(target_column, dict)
                }
                if "id" not in target_columns:
                    continue

                signature = (
                    from_table_name.lower(),
                    target_table_name.lower(),
                    (column_name,),
                    ("id",),
                )
                if signature in existing_signatures:
                    continue

                inferred.append(
                    {
                        "from": from_table_name,
                        "to": target_table_name,
                        "on": {"from_columns": [column_name], "to_columns": ["id"]},
                        "inferred": True,
                    }
                )
                existing_signatures.add(signature)
                break

    return inferred


def _embedding_candidates(table_profiles: list[dict[str, object]]) -> list[dict[str, str]]:
    keywords = {"note", "notes", "description", "comment", "summary", "text", "details"}
    candidates: list[dict[str, str]] = []
    for table in table_profiles:
        table_name = str(table.get("name", ""))
        columns_payload = table.get("columns", [])
        if not isinstance(columns_payload, list):
            continue
        for column in columns_payload:
            if not isinstance(column, dict):
                continue
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

    join_logic = _infer_joins_from_conventions(table_profiles, join_logic)
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
            "inferred_join_count": len(
                [edge for edge in join_logic if bool(edge.get("inferred"))]
            ),
            "join_count": len(join_logic),
            "embedding_candidate_count": len(embedding_candidates),
        },
    }
    return state
