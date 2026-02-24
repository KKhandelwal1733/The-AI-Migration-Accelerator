from __future__ import annotations

import re

from ai_migration_accelerator.connectors.sqlalchemy_introspector import introspect_source
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
        columns: list[dict[str, object]] = []
        for raw_column in columns_segment.split(","):
            parts = raw_column.strip().split()
            if len(parts) < 2:
                continue
            columns.append(
                {
                    "name": parts[0].strip('"'),
                    "type": parts[1].lower(),
                    "nullable": True,
                }
            )
        if columns:
            tables.append(
                {
                    "name": table_name,
                    "columns": columns,
                    "primary_key": [],
                    "foreign_keys": [],
                    "sample_rows": [],
                }
            )

    return tables


def _merge_tables(
    primary_tables: list[dict[str, object]],
    secondary_tables: list[dict[str, object]],
) -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {
        str(table["name"]).lower(): table for table in secondary_tables
    }
    for table in primary_tables:
        merged[str(table["name"]).lower()] = table
    return list(merged.values())


def collect_metadata(state: WorkflowState) -> WorkflowState:
    live_metadata, live_error = introspect_source(
        source_connection=state.context.source_connection,
        include_sample_rows=state.context.include_sample_rows,
        sample_row_limit=state.context.sample_row_limit,
    )

    ddl_tables = _parse_ddl_tables(state.context.ddl_text)
    merged_tables = _merge_tables(
        primary_tables=live_metadata.get("tables", []),
        secondary_tables=ddl_tables,
    )

    state.raw_metadata = {
        "tables": merged_tables,
        "constraints": live_metadata.get("constraints", []),
    }

    if live_error and not ddl_tables:
        state.open_questions.append(
            "Live SQLAlchemy introspection failed; using DDL/fallback metadata where available."
        )

    if not merged_tables:
        state.raw_metadata = {
            "tables": [
                {
                    "name": "sample_source",
                    "columns": [
                        {"name": "id", "type": "number", "nullable": False},
                        {"name": "content", "type": "varchar2", "nullable": True},
                    ],
                    "primary_key": ["id"],
                    "foreign_keys": [],
                    "sample_rows": [],
                }
            ],
            "constraints": [],
        }
        state.open_questions.append(
            "No live metadata or DDL tables found; fallback sample metadata injected."
        )

    return state
