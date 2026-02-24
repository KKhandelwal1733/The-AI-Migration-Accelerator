from __future__ import annotations


def build_schema_context(raw_metadata: dict[str, object]) -> dict[str, object]:
    tables = raw_metadata.get("tables", [])
    constraints = raw_metadata.get("constraints", [])

    table_profiles: list[dict[str, object]] = []
    join_edges: list[dict[str, object]] = []

    for table in tables:
        table_name = table.get("name", "unknown")
        columns = table.get("columns", [])
        sample_rows = table.get("sample_rows", [])

        table_profiles.append(
            {
                "name": table_name,
                "column_count": len(columns),
                "columns": columns,
                "sample_rows": sample_rows,
            }
        )

        for foreign_key in table.get("foreign_keys", []):
            join_edges.append(
                {
                    "from_table": table_name,
                    "from_columns": foreign_key.get("constrained_columns", []),
                    "to_table": foreign_key.get("referred_table"),
                    "to_columns": foreign_key.get("referred_columns", []),
                }
            )

    return {
        "summary": {
            "table_count": len(tables),
            "constraint_count": len(constraints),
            "join_edge_count": len(join_edges),
        },
        "table_profiles": table_profiles,
        "join_graph": join_edges,
    }
