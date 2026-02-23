from __future__ import annotations

import re

from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError

from ai_migration_accelerator.models.state import WorkflowState


def _parse_ddl_tables(ddl_text: str | None) -> list[dict[str, object]]:
    if not ddl_text:
        return []

    pattern = re.compile(
        r"create\s+table\s+([\w\"\.]+)\s*\((.*?)\)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    tables: list[dict[str, object]] = []

    for match in pattern.finditer(ddl_text):
        table_name = match.group(1).strip(' "')
        columns_segment = match.group(2)
        columns: list[dict[str, str]] = []
        for raw_column in columns_segment.split(","):
            parts = raw_column.strip().split()
            if len(parts) < 2:
                continue
            columns.append({"name": parts[0].strip('"'), "type": parts[1].lower()})
        if columns:
            tables.append({"name": table_name, "columns": columns})

    return tables


def _safe_type_name(raw_type: object) -> str:
    if raw_type is None:
        return "text"
    return str(raw_type).lower()


def _introspect_live_tables(source_connection: str) -> tuple[list[dict[str, object]], str | None]:
    engine = create_engine(source_connection)

    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        live_tables: list[dict[str, object]] = []
        for table_name in table_names:
            live_columns = inspector.get_columns(table_name)
            live_tables.append(
                {
                    "name": table_name,
                    "columns": [
                        {
                            "name": column["name"],
                            "type": _safe_type_name(column.get("type")),
                        }
                        for column in live_columns
                    ],
                }
            )
        return live_tables, None
    except (SQLAlchemyError, Exception) as exc:
        return [], str(exc)
    finally:
        engine.dispose()


def _merge_tables(
    ddl_tables: list[dict[str, object]], live_tables: list[dict[str, object]]
) -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {table["name"]: table for table in ddl_tables}
    for table in live_tables:
        merged[table["name"]] = table
    return list(merged.values())


def collect_metadata(state: WorkflowState) -> WorkflowState:
    ddl_tables = _parse_ddl_tables(state.context.ddl_text)
    live_tables: list[dict[str, object]] = []
    live_error: str | None = None

    if not ddl_tables:
        live_tables, live_error = _introspect_live_tables(state.context.source_connection)

    tables = _merge_tables(ddl_tables, live_tables)

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

    if live_error and not ddl_tables:
        state.open_questions.append(
            "Live source introspection failed and DDL did not provide usable table definitions."
        )
    if not tables:
        state.open_questions.append(
            "No CREATE TABLE statements found in DDL; used fallback sample metadata."
        )
    return state
