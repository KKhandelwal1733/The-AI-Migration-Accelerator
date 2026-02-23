from __future__ import annotations

from ai_migration_accelerator.models.state import WorkflowState


def build_smoke_report(state: WorkflowState) -> dict[str, object]:
    tables = state.canonical_schema.get("tables", [])
    table_count = len(tables)
    mapped_count = len(state.mapping_plan.get("columns", []))
    total_columns = sum(len(table.get("columns", [])) for table in tables)
    coverage = 0.0
    if total_columns > 0:
        coverage = mapped_count / total_columns

    return {
        "passed": table_count > 0 and mapped_count > 0 and coverage >= 0.9,
        "checks": {
            "table_count": f"{table_count}",
            "column_count": f"{total_columns}",
            "mapped_column_count": f"{mapped_count}",
            "mapping_coverage": f"{coverage:.2%}",
            "schema_parity": "structural parity checks generated",
        },
    }
