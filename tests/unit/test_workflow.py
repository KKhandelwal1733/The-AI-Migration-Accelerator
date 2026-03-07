from ai_migration_accelerator.graph.workflow import execute_workflow
from ai_migration_accelerator.models.state import RunContext


def test_execute_workflow_generates_artifact_and_report():
    context = RunContext(
        source_type="oracle",
        source_connection="oracle+oracledb://user:pass@host:1521/service",
        target_connection="postgresql+psycopg://user:pass@localhost:5432/db",
        ddl_text="CREATE TABLE customers (id NUMBER, payload VARCHAR2(255));",
    )
    result = execute_workflow(run_id="test-run", context=context)

    assert "migrate.py" in result.generated_artifacts
    assert "Dockerfile" in result.generated_artifacts
    assert "requirements.txt" in result.generated_artifacts
    assert "checks" in result.validation_report


def test_execute_workflow_skips_execution_when_containerized_disabled():
    context = RunContext(
        source_type="oracle",
        source_connection="oracle+oracledb://user:pass@host:1521/service",
        target_connection="postgresql+psycopg://user:pass@localhost:5432/db",
        ddl_text="CREATE TABLE customers (id NUMBER, payload VARCHAR2(255));",
        run_containerized_migration=False,
    )

    result = execute_workflow(run_id="test-run-no-exec", context=context)

    assert result.execution_report == {}
    assert result.validation_report["checks"]["execution_status"] == "missing"
