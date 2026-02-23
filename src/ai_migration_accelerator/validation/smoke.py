from __future__ import annotations

from ai_migration_accelerator.models.state import WorkflowState


def build_smoke_report(state: WorkflowState) -> dict[str, object]:
    table_count = len(state.canonical_schema.get("tables", []))
    mapped_count = len(state.mapping_plan.get("columns", []))
    return {
        "passed": table_count > 0 and mapped_count > 0,
        "checks": {
            "table_count": f"{table_count}",
            "mapped_column_count": f"{mapped_count}",
            "schema_parity": "basic parity checks generated",
        },
    }
