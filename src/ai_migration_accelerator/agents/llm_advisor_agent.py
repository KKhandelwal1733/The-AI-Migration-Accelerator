from __future__ import annotations

import json
import os
import re
from importlib import import_module

from ai_migration_accelerator.core.settings import get_settings
from ai_migration_accelerator.models.state import WorkflowState


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

    prompt_payload = {
        "table_profiles": table_profiles,
        "join_graph": join_graph,
        "current_selected_embedding_column": current_selected,
        "requirements": {
            "goal": "Suggest best join strategy and best embedding candidate column",
            "response_format": {
                "selected_embedding_column": {"table": "string", "column": "string"},
                "join_strategy": "string",
                "migration_notes": ["string"],
            },
        },
    }
    return json.dumps(prompt_payload, indent=2)


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

    join_strategy = suggestions.get("join_strategy")
    notes = suggestions.get("migration_notes")

    state.mapping_plan["llm_advice"] = {
        "model": state.context.llm_model,
        "join_strategy": str(join_strategy) if join_strategy is not None else "",
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
