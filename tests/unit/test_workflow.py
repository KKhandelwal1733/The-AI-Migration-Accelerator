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

    assert "generated_pipeline.py" in result.generated_artifacts
    assert "checks" in result.validation_report
