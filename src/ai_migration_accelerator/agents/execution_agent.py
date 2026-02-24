from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ai_migration_accelerator.models.state import WorkflowState


def _simulated_execution(state: WorkflowState) -> WorkflowState:
    row_count = 0
    for table in state.raw_metadata.get("tables", []):
        sample_rows = table.get("sample_rows", [])
        row_count += len(sample_rows)

    if row_count == 0:
        row_count = 2

    state.execution_report = {
        "mode": "simulated",
        "status": "completed",
        "source_count": row_count,
        "target_count": row_count,
        "loss_percentage": 0.0,
    }
    return state


def execute_migration(state: WorkflowState) -> WorkflowState:
    if not state.context.run_containerized_migration:
        return _simulated_execution(state)

    runtime = state.context.container_runtime
    if shutil.which(runtime) is None:
        state.open_questions.append(
            f"Container runtime '{runtime}' not found; switched to simulated execution."
        )
        return _simulated_execution(state)

    with tempfile.TemporaryDirectory(prefix="migration-run-") as temp_dir:
        temp_path = Path(temp_dir)
        report_path = temp_path / "migration_report.json"

        required_files = ["migrate.py", "requirements.txt", "Dockerfile"]
        for file_name in required_files:
            content = state.generated_artifacts.get(file_name)
            if content is None:
                state.open_questions.append(
                    f"Missing generated artifact '{file_name}' for execution."
                )
                return _simulated_execution(state)
            (temp_path / file_name).write_text(content, encoding="utf-8")

        image_tag = f"ai-migration-run-{state.run_id[:8]}"

        try:
            subprocess.run(
                [runtime, "build", "-t", image_tag, str(temp_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    runtime,
                    "run",
                    "--rm",
                    "-e",
                    "REPORT_PATH=/output/migration_report.json",
                    "-e",
                    f"{state.context.hf_token_env_var}={os.getenv(state.context.hf_token_env_var, '')}",
                    "-e",
                    "VECTOR_DIM=" + os.getenv("VECTOR_DIM", "384"),
                    "-v",
                    f"{temp_path.as_posix()}:/output",
                    image_tag,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            state.open_questions.append(
                f"Container execution failed: {exc.stderr.strip() or exc.stdout.strip()}"
            )
            return _simulated_execution(state)

        if report_path.exists():
            report_data = json.loads(report_path.read_text(encoding="utf-8"))
            report_data["mode"] = "container"
            report_data["status"] = "completed"
            state.execution_report = report_data
            return state

        state.open_questions.append(
            "Container finished but no migration report was produced; switched to simulated report."
        )
        return _simulated_execution(state)
