from fastapi.testclient import TestClient

from ai_migration_accelerator.main import app


def test_create_job_and_fetch_status_and_artifacts():
    client = TestClient(app)
    payload = {
        "source_type": "oracle",
        "source_connection": "oracle+oracledb://user:pass@host:1521/service",
        "target_connection": "postgresql+psycopg://user:pass@localhost:5432/db",
        "ddl_text": "CREATE TABLE customers (id NUMBER, payload VARCHAR2(255));",
        "enable_llm_advisor": False,
    }

    create_response = client.post("/jobs", json=payload)
    assert create_response.status_code == 200
    run_id = create_response.json()["run_id"]

    status_response = client.get(f"/jobs/{run_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] in {"completed", "failed"}

    artifacts_response = client.get(f"/artifacts/{run_id}")
    assert artifacts_response.status_code == 200
    files = artifacts_response.json()["files"]
    assert "generated_pipeline.py" in files
    assert "validation_report.json" in files


def test_artifacts_not_found_for_unknown_run():
    client = TestClient(app)
    response = client.get("/artifacts/unknown-run-id")
    assert response.status_code == 404
