from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from decimal import Decimal
from importlib import import_module

from ai_migration_accelerator.core.settings import get_settings
from ai_migration_accelerator.models.state import WorkflowState


def _json_default(value: object) -> object:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _extract_json_block(text: str) -> dict[str, object] | None:
    direct = text.strip()
    try:
        loaded = json.loads(direct)
        if isinstance(loaded, dict):
            return loaded
    except json.JSONDecodeError:
        pass

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced_match is None:
        return None

    try:
        loaded = json.loads(fenced_match.group(1))
        if isinstance(loaded, dict):
            return loaded
    except json.JSONDecodeError:
        return None
    return None


def _build_prompt(state: WorkflowState) -> str:
    table_profiles = state.schema_context.get("table_profiles", [])
    join_graph = state.schema_context.get("join_graph", [])
    current_selected = state.mapping_plan.get("selected_embedding_column", {})
    current_selected_columns = state.mapping_plan.get("selected_embedding_columns", [])

    prompt_payload = {
        "table_profiles": table_profiles,
        "join_graph": join_graph,
        "current_selected_embedding_column": current_selected,
        "requirements": {
            "goal": "Suggest best join strategy and best embedding candidate columns",
            "response_format": {
                "selected_embedding_column": {"table": "string", "column": "string"},
                "selected_embedding_columns": ["string"],
                "join_strategy": "string",
                "join_plan": [
                    {
                        "from": "string",
                        "to": "string",
                        "on": {
                            "from_columns": ["string"],
                            "to_columns": ["string"],
                        },
                    }
                ],
                "migration_notes": ["string"],
            },
        },
        "current_selected_embedding_columns": current_selected_columns,
    }
    return json.dumps(prompt_payload, indent=2, default=_json_default)


def _apply_llm_suggestions(state: WorkflowState, suggestions: dict[str, object]) -> None:
    selected = suggestions.get("selected_embedding_column")
    if isinstance(selected, dict):
        table = str(selected.get("table", "")).strip()
        column = str(selected.get("column", "")).strip()
        if table and column:
            state.mapping_plan["selected_embedding_column"] = {
                "table": table,
                "column": column,
            }

    selected_columns_payload = suggestions.get("selected_embedding_columns", [])
    if isinstance(selected_columns_payload, list):
        normalized_columns: list[str] = []
        for value in selected_columns_payload:
            column_name = str(value).strip()
            if not column_name or column_name in normalized_columns:
                continue
            normalized_columns.append(column_name)
        if normalized_columns:
            state.mapping_plan["selected_embedding_columns"] = normalized_columns

    current_selected = state.mapping_plan.get("selected_embedding_column", {})
    if isinstance(current_selected, dict):
        selected_column = str(current_selected.get("column", "")).strip()
        if selected_column:
            columns_list = state.mapping_plan.get("selected_embedding_columns", [])
            if not isinstance(columns_list, list):
                columns_list = []
            normalized_existing = [str(value).strip() for value in columns_list if str(value).strip()]
            if selected_column in normalized_existing:
                normalized_existing = [
                    selected_column,
                    *[value for value in normalized_existing if value != selected_column],
                ]
            else:
                normalized_existing = [selected_column, *normalized_existing]
            state.mapping_plan["selected_embedding_columns"] = normalized_existing

    join_strategy = suggestions.get("join_strategy")
    join_plan_payload = suggestions.get("join_plan", [])
    notes = suggestions.get("migration_notes")

    llm_join_plan: list[dict[str, object]] = []
    if isinstance(join_plan_payload, list):
        for edge in join_plan_payload:
            if not isinstance(edge, dict):
                continue
            from_table = str(edge.get("from", "")).strip()
            to_table = str(edge.get("to", "")).strip()
            on_payload = edge.get("on", {})
            if not isinstance(on_payload, dict):
                continue
            from_columns_payload = on_payload.get("from_columns", [])
            to_columns_payload = on_payload.get("to_columns", [])
            if not isinstance(from_columns_payload, list) or not isinstance(to_columns_payload, list):
                continue
            from_columns = [str(value).strip() for value in from_columns_payload if str(value).strip()]
            to_columns = [str(value).strip() for value in to_columns_payload if str(value).strip()]
            if not from_table or not to_table or not from_columns or not to_columns:
                continue
            llm_join_plan.append(
                {
                    "from": from_table,
                    "to": to_table,
                    "on": {
                        "from_columns": from_columns,
                        "to_columns": to_columns,
                    },
                }
            )

    if llm_join_plan:
        state.mapping_plan["llm_join_plan"] = llm_join_plan

    state.mapping_plan["llm_advice"] = {
        "model": state.context.llm_model,
        "join_strategy": str(join_strategy) if join_strategy is not None else "",
        "join_plan_edge_count": len(llm_join_plan),
        "migration_notes": notes if isinstance(notes, list) else [],
    }


def run_llm_advisor(state: WorkflowState) -> WorkflowState:
    if not state.context.enable_llm_advisor:
        return state

    settings = get_settings()
    api_key = os.getenv("GOOGLE_API_KEY") or settings.google_api_key
    if not api_key:
        state.open_questions.append(
            "LLM advisor enabled but GOOGLE_API_KEY is not set; using deterministic inference only."
        )
        state.generated_artifacts["advisor_notes.md"] = (
            "LLM advisor was requested but GOOGLE_API_KEY is not configured."
        )
        return state

    try:
        provider_module = import_module("langchain_google_genai")
        ChatGoogleGenerativeAI = provider_module.ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=state.context.llm_model,
            google_api_key=api_key,
            temperature=0.0,
        )
        response = llm.invoke(_build_prompt(state))
        response_text = str(getattr(response, "content", response))
        suggestions = _extract_json_block(response_text)

        if suggestions is None:
            state.open_questions.append(
                "LLM advisor returned non-JSON output; deterministic inference retained."
            )
            state.generated_artifacts["advisor_notes.md"] = response_text
            return state

        _apply_llm_suggestions(state, suggestions)
        state.generated_artifacts["advisor_notes.md"] = json.dumps(suggestions, indent=2)
        return state
    except Exception as exc:
        state.open_questions.append(
            f"LLM advisor execution failed; deterministic inference retained. Details: {exc}"
        )
        state.generated_artifacts["advisor_notes.md"] = (
            "LLM advisor failed at runtime; see open questions for details."
        )
        return state
