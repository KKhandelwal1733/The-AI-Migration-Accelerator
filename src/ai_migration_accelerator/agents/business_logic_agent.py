from __future__ import annotations

import json
import os
import re
from importlib import import_module
from typing import Any

from ai_migration_accelerator.core.settings import get_settings
from ai_migration_accelerator.models.state import WorkflowState


def _table_profiles(state: WorkflowState) -> list[dict[str, Any]]:
    profiles = state.schema_context.get("table_profiles", [])
    if not isinstance(profiles, list):
        return []
    return [item for item in profiles if isinstance(item, dict)]


def _extract_json_block(text: str) -> dict[str, object] | None:
    direct = text.strip()
    try:
        parsed = json.loads(direct)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced_match is None:
        return None

    try:
        parsed = json.loads(fenced_match.group(1))
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None
    return None


def _schema_payload(table_profiles: list[dict[str, Any]]) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for table in table_profiles:
        table_name = str(table.get("name", "")).strip()
        if not table_name:
            continue

        columns_payload = table.get("columns", [])
        columns: list[str] = []
        if isinstance(columns_payload, list):
            for column in columns_payload:
                if not isinstance(column, dict):
                    continue
                column_name = str(column.get("name", "")).strip()
                if column_name:
                    columns.append(column_name)

        sample_rows_payload = table.get("sample_rows", [])
        sample_rows: list[dict[str, object]] = []
        if isinstance(sample_rows_payload, list):
            sample_rows = [row for row in sample_rows_payload if isinstance(row, dict)][:3]

        payload.append(
            {
                "table": table_name,
                "columns": columns,
                "sample_rows": sample_rows,
            }
        )
    return payload


def _build_prompt(state: WorkflowState, table_profiles: list[dict[str, Any]]) -> str:
    payload = {
        "business_logic_prompt": state.context.business_logic_prompt,
        "schema": _schema_payload(table_profiles),
        "instructions": [
            "Infer concrete row-level filters required by the business logic prompt.",
            "Use only tables and columns that exist in schema.",
            "Return JSON only.",
        ],
        "response_format": {
            "filters": [
                {
                    "table": "string",
                    "column": "string",
                    "operator": "== or !=",
                    "value": "string",
                    "reason": "string",
                }
            ],
            "notes": ["string"],
        },
    }
    return json.dumps(payload, indent=2)


def _column_index(table_profiles: list[dict[str, Any]]) -> tuple[
    dict[str, dict[str, str]],
    dict[str, list[dict[str, str]]],
]:
    table_to_columns: dict[str, dict[str, str]] = {}
    global_column_index: dict[str, list[dict[str, str]]] = {}

    for table in table_profiles:
        table_name = str(table.get("name", "")).strip()
        if not table_name:
            continue

        columns_payload = table.get("columns", [])
        if not isinstance(columns_payload, list):
            continue

        column_map: dict[str, str] = {}
        for column in columns_payload:
            if not isinstance(column, dict):
                continue
            column_name = str(column.get("name", "")).strip()
            if not column_name:
                continue
            lowered = column_name.lower()
            column_map[lowered] = column_name
            global_column_index.setdefault(lowered, []).append(
                {"table": table_name, "column": column_name}
            )

        table_to_columns[table_name.lower()] = column_map

    return table_to_columns, global_column_index


def _normalize_operator(value: str) -> str | None:
    normalized = value.strip().lower()
    mapping = {
        "=": "==",
        "==": "==",
        "eq": "==",
        "equals": "==",
        "is": "==",
        "!=": "!=",
        "<>": "!=",
        "ne": "!=",
        "not_equals": "!=",
    }
    return mapping.get(normalized)


def _validate_filters(
    raw_filters: object,
    table_profiles: list[dict[str, Any]],
    source: str,
) -> list[dict[str, str]]:
    if not isinstance(raw_filters, list):
        return []

    table_to_columns, global_column_index = _column_index(table_profiles)
    validated: list[dict[str, str]] = []

    for item in raw_filters:
        if not isinstance(item, dict):
            continue

        table_name_raw = str(item.get("table", "")).strip()
        column_name_raw = str(item.get("column", "")).strip()
        value = str(item.get("value", "")).strip()
        operator = _normalize_operator(str(item.get("operator", "==")))

        if not column_name_raw or not value or operator is None:
            continue

        resolved_table = ""
        resolved_column = ""

        if table_name_raw:
            table_map = table_to_columns.get(table_name_raw.lower(), {})
            resolved_column = table_map.get(column_name_raw.lower(), "")
            if resolved_column:
                resolved_table = table_name_raw

        if not resolved_column:
            matches = global_column_index.get(column_name_raw.lower(), [])
            if len(matches) == 1:
                resolved_table = matches[0]["table"]
                resolved_column = matches[0]["column"]

        if not resolved_table or not resolved_column:
            continue

        validated.append(
            {
                "table": resolved_table,
                "column": resolved_column,
                "operator": operator,
                "value": value,
                "source": source,
            }
        )

    return validated


def _fallback_prompt_filters(prompt: str, table_profiles: list[dict[str, Any]]) -> list[dict[str, str]]:
    pattern = re.compile(
        r"(?:\b([A-Za-z_][\w]*)\.)?([A-Za-z_][\w]*)\s*(=|==|!=|<>|is|equals?)\s*['\"]?([^,'\".;\n]+)['\"]?",
        flags=re.IGNORECASE,
    )

    raw_filters: list[dict[str, str]] = []
    for match in pattern.finditer(prompt):
        table_name = (match.group(1) or "").strip()
        column_name = (match.group(2) or "").strip()
        operator = (match.group(3) or "").strip()
        value = (match.group(4) or "").strip()
        if not column_name or not value:
            continue
        raw_filters.append(
            {
                "table": table_name,
                "column": column_name,
                "operator": operator,
                "value": value,
            }
        )

    return _validate_filters(raw_filters, table_profiles, source="prompt_pattern")


def _llm_filters(state: WorkflowState, table_profiles: list[dict[str, Any]]) -> tuple[list[dict[str, str]], list[str]]:
    settings = get_settings()
    api_key = os.getenv("GOOGLE_API_KEY") or settings.google_api_key
    if not api_key:
        return [], [
            "Business logic prompt provided but GOOGLE_API_KEY is not set; using prompt-pattern fallback."
        ]

    try:
        provider_module = import_module("langchain_google_genai")
        ChatGoogleGenerativeAI = provider_module.ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=state.context.llm_model,
            google_api_key=api_key,
            temperature=0.0,
        )

        response = llm.invoke(_build_prompt(state, table_profiles))
        response_text = str(getattr(response, "content", response))
        parsed = _extract_json_block(response_text)
        if parsed is None:
            return [], [
                "Business logic LLM returned non-JSON output; using prompt-pattern fallback."
            ]

        notes_payload = parsed.get("notes", [])
        notes = [str(item) for item in notes_payload] if isinstance(notes_payload, list) else []
        return _validate_filters(parsed.get("filters", []), table_profiles, source="llm_business_logic"), notes
    except Exception as exc:
        return [], [
            f"Business logic LLM parsing failed; using prompt-pattern fallback. Details: {exc}"
        ]


def _dedupe_filters(filters: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for item in filters:
        key = (
            str(item.get("table", "")).strip().lower(),
            str(item.get("column", "")).strip().lower(),
            str(item.get("operator", "==")).strip(),
            str(item.get("value", "")).strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped


def analyze_business_logic(state: WorkflowState) -> WorkflowState:
    table_profiles = _table_profiles(state)
    prompt = (state.context.business_logic_prompt or "").strip()

    filters: list[dict[str, str]] = []
    llm_notes: list[str] = []
    parsing_mode = "none"
    if prompt:
        filters, llm_notes = _llm_filters(state, table_profiles)
        if filters:
            parsing_mode = "llm"
        else:
            filters = _fallback_prompt_filters(prompt, table_profiles)
            parsing_mode = "prompt_pattern" if filters else "none"
            if not filters:
                state.open_questions.append(
                    "Business logic prompt was provided but no schema-aligned filters were inferred."
                )

    filters = _dedupe_filters(filters)
    state.mapping_plan["business_filters"] = filters
    state.mapping_plan["business_logic_summary"] = {
        "prompt_provided": bool(prompt),
        "applied_filter_count": len(filters),
        "parsing_mode": parsing_mode,
        "llm_notes": llm_notes,
    }

    for note in llm_notes:
        state.open_questions.append(note)

    if filters:
        rendered_lines = ["# Business Logic Filters", ""]
        rendered_lines.append(f"- Parsing mode: {parsing_mode}")
        if llm_notes:
            rendered_lines.append("- LLM notes:")
            for note in llm_notes:
                rendered_lines.append(f"  - {note}")
        rendered_lines.append("")
        for item in filters:
            rendered_lines.append(
                f"- {item['table']}.{item['column']} {item['operator']} {item['value']} ({item['source']})"
            )
        state.generated_artifacts["business_logic_notes.md"] = "\n".join(rendered_lines)

    return state
