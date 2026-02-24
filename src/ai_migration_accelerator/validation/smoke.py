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

    has_migrate_script = "migrate.py" in state.generated_artifacts
    has_infra_files = (
        "Dockerfile" in state.generated_artifacts
        and "requirements.txt" in state.generated_artifacts
    )
    execution_report = state.execution_report
    source_count = int(execution_report.get("source_count", 0))
    target_count = int(execution_report.get("target_count", 0))
    loss_percentage = float(execution_report.get("loss_percentage", 100.0))
    execution_status = str(execution_report.get("status", "missing"))

    return {
        "passed": (
            table_count > 0
            and mapped_count > 0
            and coverage >= 0.9
            and has_migrate_script
            and has_infra_files
            and execution_status == "completed"
            and loss_percentage == 0.0
        ),
        "checks": {
            "table_count": f"{table_count}",
            "column_count": f"{total_columns}",
            "mapped_column_count": f"{mapped_count}",
            "mapping_coverage": f"{coverage:.2%}",
            "migrate_script": "present" if has_migrate_script else "missing",
            "infra_artifacts": "present" if has_infra_files else "missing",
            "execution_status": execution_status,
            "source_count": f"{source_count}",
            "target_count": f"{target_count}",
            "loss_percentage": f"{loss_percentage:.4f}",
            "schema_parity": "structural parity checks generated",
        },
    }
