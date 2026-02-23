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


def analyze_schema(state: WorkflowState) -> WorkflowState:
    mapped_columns: list[dict[str, str]] = []
    for table in state.canonical_schema.get("tables", []):
        for column in table.get("columns", []):
            mapped_columns.append(
                {
                    "table": table["name"],
                    "column": column["name"],
                    "source_type": column["type"],
                    "target_type": map_type(column["type"]),
                }
            )
    state.mapping_plan = {"columns": mapped_columns}
    return state
