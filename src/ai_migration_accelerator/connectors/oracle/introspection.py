from __future__ import annotations

from ai_migration_accelerator.models.state import WorkflowState


def _parse_ddl_tables(ddl_text: str | None) -> list[dict[str, object]]:
    if not ddl_text:
        return []

    tables: list[dict[str, object]] = []
    for raw_line in ddl_text.splitlines():
        line = raw_line.strip().lower()
        if line.startswith("create table"):
            table_name = line.replace("create table", "").split("(")[0].strip(' "')
            tables.append(
                {
                    "name": table_name,
                    "columns": [
                        {"name": "id", "type": "number"},
                        {"name": "payload", "type": "varchar2"},
                    ],
                }
            )
    return tables


def collect_metadata(state: WorkflowState) -> WorkflowState:
    tables = _parse_ddl_tables(state.context.ddl_text)
    state.raw_metadata = {
        "tables": tables or [
            {
                "name": "sample_source",
                "columns": [
                    {"name": "id", "type": "number"},
                    {"name": "content", "type": "varchar2"},
                ],
            }
        ],
        "constraints": [],
    }
    if not tables:
        state.open_questions.append(
            "No CREATE TABLE statements found in DDL; used fallback sample metadata."
        )
    return state
