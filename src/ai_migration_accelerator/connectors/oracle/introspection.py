from __future__ import annotations

import re

from ai_migration_accelerator.connectors.sqlalchemy_introspector import introspect_source
from ai_migration_accelerator.models.state import WorkflowState


def _split_top_level_columns(columns_segment: str) -> list[str]:
    chunks: list[str] = []
    start = 0
    depth = 0
    for index, char in enumerate(columns_segment):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            part = columns_segment[start:index].strip()
            if part:
                chunks.append(part)
            start = index + 1

    tail = columns_segment[start:].strip()
    if tail:
        chunks.append(tail)
    return chunks


def _extract_create_table_blocks(ddl_text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    pattern = re.compile(r"create\s+table\s+([\w\"\.]+)", flags=re.IGNORECASE)

    for match in pattern.finditer(ddl_text):
        table_name = match.group(1).strip(' "')
        cursor = match.end()
        while cursor < len(ddl_text) and ddl_text[cursor].isspace():
            cursor += 1
        if cursor >= len(ddl_text) or ddl_text[cursor] != "(":
            continue

        depth = 0
        start = cursor + 1
        end = -1
        for index in range(cursor, len(ddl_text)):
            char = ddl_text[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    end = index
                    break

        if end == -1:
            continue

        blocks.append((table_name, ddl_text[start:end]))

    return blocks


def _parse_ddl_tables(ddl_text: str | None) -> list[dict[str, object]]:
    if not ddl_text:
        return []

    tables: list[dict[str, object]] = []

    for table_name, columns_segment in _extract_create_table_blocks(ddl_text):
        columns: list[dict[str, object]] = []
        for raw_column in _split_top_level_columns(columns_segment):
            lowered = raw_column.strip().lower()
            if lowered.startswith(("constraint", "primary key", "foreign key", "unique", "check")):
                continue

            parts = raw_column.strip().split()
            if len(parts) < 2:
                continue
            columns.append(
                {
                    "name": parts[0].strip('"'),
                    "type": " ".join(parts[1:]).lower(),
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
    live_tables_payload = live_metadata.get("tables", [])
    live_tables = live_tables_payload if isinstance(live_tables_payload, list) else []
    merged_tables = _merge_tables(
        primary_tables=live_tables,
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
