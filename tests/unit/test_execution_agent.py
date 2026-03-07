from ai_migration_accelerator.agents.execution_agent import (
    _prepare_container_connections,
    _resolve_container_network,
)
from ai_migration_accelerator.models.state import RunContext, WorkflowState


def _build_state(
    source_connection: str,
    target_connection: str,
    container_network_mode: str = "auto",
    container_network_name: str | None = None,
) -> WorkflowState:
    context = RunContext(
        source_type="oracle",
        source_connection=source_connection,
        target_connection=target_connection,
        run_containerized_migration=True,
        container_runtime="podman",
        container_network_mode=container_network_mode,
        container_network_name=container_network_name,
    )
    return WorkflowState(run_id="test-run", context=context)


def test_prepare_container_connections_rewrites_loopback_hosts_for_podman():
    state = _build_state(
        source_connection="oracle+oracledb://u:p@localhost:1521/?service_name=XEPDB1",
        target_connection="postgresql+psycopg://u:p@127.0.0.1:5432/accelerator",
    )

    source, target = _prepare_container_connections(state, runtime="podman")

    assert "@host.containers.internal:1521" in source
    assert "@host.containers.internal:5432" in target


def test_prepare_container_connections_keeps_remote_hosts_unchanged():
    source_connection = "oracle+oracledb://u:p@db.company.net:1521/?service_name=XEPDB1"
    target_connection = "postgresql+psycopg://u:p@pg.company.net:5432/accelerator"
    state = _build_state(
        source_connection=source_connection,
        target_connection=target_connection,
    )

    source, target = _prepare_container_connections(state, runtime="podman")

    assert source == source_connection
    assert target == target_connection


def test_resolve_container_network_requires_name_for_compose_mode():
    state = _build_state(
        source_connection="oracle+oracledb://u:p@oracle:1521/?service_name=XEPDB1",
        target_connection="postgresql+psycopg://u:p@postgres:5432/accelerator",
        container_network_mode="compose",
    )

    network_name = _resolve_container_network(state)

    assert network_name is None
    assert any("container_network_mode=compose" in q for q in state.open_questions)


def test_resolve_container_network_uses_explicit_name():
    state = _build_state(
        source_connection="oracle+oracledb://u:p@oracle:1521/?service_name=XEPDB1",
        target_connection="postgresql+psycopg://u:p@postgres:5432/accelerator",
        container_network_mode="compose",
        container_network_name="ops_default",
    )

    network_name = _resolve_container_network(state)

    assert network_name == "ops_default"
