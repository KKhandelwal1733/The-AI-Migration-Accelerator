from __future__ import annotations

from importlib import import_module

from ai_migration_accelerator.agents.codegen_agent import generate_code
from ai_migration_accelerator.agents.schema_analyzer import analyze_schema
from ai_migration_accelerator.agents.validation_agent import run_validation
from ai_migration_accelerator.connectors.oracle.introspection import collect_metadata
from ai_migration_accelerator.generator.render import render_fastapi_pipeline
from ai_migration_accelerator.graph.router import should_validate
from ai_migration_accelerator.models.state import RunContext, WorkflowState


def normalize_schema(state: WorkflowState) -> WorkflowState:
    state.canonical_schema = {
        "tables": state.raw_metadata.get("tables", []),
        "constraints": state.raw_metadata.get("constraints", []),
    }
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
    graph.add_node("analyze_mappings", analyze_schema)
    graph.add_node("generate_code", generate_code)
    graph.add_node("render_artifacts", render_fastapi_pipeline)
    graph.add_node("run_validation", run_validation)
    graph.add_node("gate_review", gate_review)

    graph.add_edge(START, "collect_metadata")
    graph.add_edge("collect_metadata", "normalize_schema")
    graph.add_edge("normalize_schema", "analyze_mappings")
    graph.add_edge("analyze_mappings", "generate_code")
    graph.add_edge("generate_code", "render_artifacts")
    graph.add_conditional_edges(
        "render_artifacts",
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
        state = generate_code(state)
        state = render_fastapi_pipeline(state)
        if should_validate(state) == "run_validation":
            return run_validation(state)
        return gate_review(state)

    result = app.invoke(initial_state)
    if isinstance(result, WorkflowState):
        return result
    return WorkflowState.model_validate(result)
