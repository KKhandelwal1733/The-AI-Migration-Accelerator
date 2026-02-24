from __future__ import annotations

from ai_migration_accelerator.models.state import WorkflowState


def generate_infra(state: WorkflowState) -> WorkflowState:
    state.generated_artifacts["requirements.txt"] = "\n".join(
        [
            "sqlalchemy>=2.0.0",
            "psycopg[binary]>=3.2.0",
            "oracledb>=2.2.0",
            "pandas>=2.2.0",
            "sentence-transformers>=3.0.0",
        ]
    )

    state.generated_artifacts["Dockerfile"] = "\n".join(
        [
            "FROM python:3.11-slim",
            "WORKDIR /app",
            "COPY requirements.txt ./",
            "RUN pip install --no-cache-dir -r requirements.txt",
            "COPY migrate.py ./",
            'CMD ["python", "migrate.py"]',
        ]
    )

    return state
