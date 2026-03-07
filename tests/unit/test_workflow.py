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


def test_execute_workflow_includes_business_filters_in_generated_script():
    context = RunContext(
        source_type="oracle",
        source_connection="oracle+oracledb://user:pass@host:1521/service",
        target_connection="postgresql+psycopg://user:pass@localhost:5432/db",
        ddl_text="""
        CREATE TABLE customers (cust_id NUMBER, name VARCHAR2(100), tier VARCHAR2(20));
        CREATE TABLE product_feedback (
            feedback_id NUMBER,
            cust_id NUMBER,
            comments VARCHAR2(4000),
            status VARCHAR2(20)
        );
        """,
        business_logic_prompt='status = Resolved',
    )

    result = execute_workflow(run_id="test-run-business-filters", context=context)

    migrate_script = result.generated_artifacts["migrate.py"]
    assert "BUSINESS_FILTERS" in migrate_script
    assert "resolved" in migrate_script.lower()
