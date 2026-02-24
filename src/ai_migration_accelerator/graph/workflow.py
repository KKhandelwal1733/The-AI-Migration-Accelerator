from __future__ import annotations

from importlib import import_module

from ai_migration_accelerator.agents.codegen_agent import generate_code
from ai_migration_accelerator.agents.execution_agent import execute_migration
from ai_migration_accelerator.agents.infra_generator_agent import generate_infra
from ai_migration_accelerator.agents.llm_advisor_agent import run_llm_advisor
from ai_migration_accelerator.agents.schema_analyzer import analyze_schema
from ai_migration_accelerator.agents.validation_agent import run_validation
from ai_migration_accelerator.control_plane.schema_context_builder import (
    build_schema_context,
)
from ai_migration_accelerator.connectors.oracle.introspection import collect_metadata
from ai_migration_accelerator.graph.router import should_validate
from ai_migration_accelerator.models.state import RunContext, WorkflowState


def normalize_schema(state: WorkflowState) -> WorkflowState:
    state.canonical_schema = {
        "tables": state.raw_metadata.get("tables", []),
        "constraints": state.raw_metadata.get("constraints", []),
    }
    state.schema_context = build_schema_context(state.raw_metadata)
    return state


def gate_review(state: WorkflowState) -> WorkflowState:
    if not state.open_questions:
        state.open_questions.append("No blocking issues detected.")
    return state


def build_workflow():
    try:
        graph_module = import_module("langgraph.graph")
    except ModuleNotFoundError:
        return None

    StateGraph = graph_module.StateGraph
    START = graph_module.START
    END = graph_module.END

    graph = StateGraph(WorkflowState)
    graph.add_node("collect_metadata", collect_metadata)
    graph.add_node("normalize_schema", normalize_schema)
    graph.add_node("analyzer", analyze_schema)
    graph.add_node("llm_advisor", run_llm_advisor)
    graph.add_node("code_generator", generate_code)
    graph.add_node("infra_generator", generate_infra)
    graph.add_node("executor", execute_migration)
    graph.add_node("run_validation", run_validation)
    graph.add_node("gate_review", gate_review)

    graph.add_edge(START, "collect_metadata")
    graph.add_edge("collect_metadata", "normalize_schema")
    graph.add_edge("normalize_schema", "analyzer")
    graph.add_edge("analyzer", "llm_advisor")
    graph.add_edge("llm_advisor", "code_generator")
    graph.add_edge("code_generator", "infra_generator")
    graph.add_edge("infra_generator", "executor")
    graph.add_conditional_edges(
        "executor",
        should_validate,
        {"run_validation": "run_validation", "gate_review": "gate_review"},
    )
    graph.add_edge("run_validation", END)
    graph.add_edge("gate_review", END)
    return graph.compile()


def execute_workflow(run_id: str, context: RunContext) -> WorkflowState:
    app = build_workflow()
    initial_state = WorkflowState(run_id=run_id, context=context)
    if app is None:
        state = collect_metadata(initial_state)
        state = normalize_schema(state)
        state = analyze_schema(state)
        state = run_llm_advisor(state)
        state = generate_code(state)
        state = generate_infra(state)
        state = execute_migration(state)
        if should_validate(state) == "run_validation":
            return run_validation(state)
        return gate_review(state)

    result = app.invoke(initial_state)
    if isinstance(result, WorkflowState):
        return result
    return WorkflowState.model_validate(result)
