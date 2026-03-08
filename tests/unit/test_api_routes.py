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
    assert "migrate.py" in files
    assert "Dockerfile" in files
    assert "requirements.txt" in files
    assert "validation_report.json" in files
    assert "execution_logs.txt" not in files

    logs_response = client.get(f"/jobs/{run_id}/logs")
    assert logs_response.status_code == 200
    payload = logs_response.json()
    assert payload["run_id"] == run_id
    assert isinstance(payload["logs"], list)
    assert "log_lines" in payload

    stream_response = client.get(f"/jobs/{run_id}/logs/stream")
    assert stream_response.status_code == 200
    assert stream_response.headers["content-type"].startswith("text/event-stream")


def test_artifacts_not_found_for_unknown_run():
    client = TestClient(app)
    response = client.get("/artifacts/unknown-run-id")
    assert response.status_code == 404


def test_logs_not_found_for_unknown_run():
    client = TestClient(app)
    response = client.get("/jobs/unknown-run-id/logs")
    assert response.status_code == 404


def test_log_stream_not_found_for_unknown_run():
    client = TestClient(app)
    response = client.get("/jobs/unknown-run-id/logs/stream")
    assert response.status_code == 404


def test_create_job_rejects_removed_payload_fields():
    client = TestClient(app)
    payload = {
        "source_type": "oracle",
        "source_connection": "oracle+oracledb://user:pass@host:1521/service",
        "target_connection": "postgresql+psycopg://user:pass@localhost:5432/db",
        "llm_model": "gemini-1.5-pro",
    }

    create_response = client.post("/jobs", json=payload)
    assert create_response.status_code == 422


def test_create_job_async_returns_running_or_completed():
    client = TestClient(app)
    payload = {
        "source_type": "oracle",
        "source_connection": "oracle+oracledb://user:pass@host:1521/service",
        "target_connection": "postgresql+psycopg://user:pass@localhost:5432/db",
        "ddl_text": "CREATE TABLE customers (id NUMBER, payload VARCHAR2(255));",
    }

    response = client.post("/jobs/async", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["status"] in {"running", "completed", "failed"}
