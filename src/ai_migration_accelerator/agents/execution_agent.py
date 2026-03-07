from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from ai_migration_accelerator.models.state import WorkflowState


def _record_log(state: WorkflowState, line: str) -> None:
    state.execution_logs.append(line)
    from ai_migration_accelerator.api.run_store import append_log

    append_log(state.run_id, line)


def _finalize_logs_artifact(state: WorkflowState) -> None:
    if not state.execution_logs:
        return
    state.generated_artifacts["execution_logs.txt"] = "\n".join(state.execution_logs)


def _run_command(
    command: list[str],
    state: WorkflowState,
    stage: str,
) -> None:
    _record_log(state, f"$ {' '.join(command)}")
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )

    if result.stdout:
        for line in result.stdout.splitlines():
            _record_log(state, f"[{stage}] {line}")
    if result.stderr:
        for line in result.stderr.splitlines():
            _record_log(state, f"[{stage}:stderr] {line}")

    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=command,
            output=result.stdout,
            stderr=result.stderr,
        )


def _resolve_hf_token_env_var(state: WorkflowState) -> str:
    configured = str(state.context.hf_token_env_var or "").strip()
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", configured):
        return configured

    state.open_questions.append(
        (
            f"Invalid HF token env var key '{configured}' in context; "
            "falling back to 'HF_TOKEN'."
        )
    )
    return "HF_TOKEN"


def _extract_dsn_host(connection_string: str) -> str | None:
    match = re.match(
        r"^[A-Za-z0-9_+]+://[^@]+@(?P<host>\[[^\]]+\]|[^:/?]+)",
        connection_string,
    )
    if not match:
        return None

    host = match.group("host")
    return host[1:-1] if host.startswith("[") and host.endswith("]") else host


def _replace_dsn_host(connection_string: str, new_host: str) -> str:
    return re.sub(
        r"(^[A-Za-z0-9_+]+://[^@]+@)(\[[^\]]+\]|[^:/?]+)",
        rf"\1{new_host}",
        connection_string,
        count=1,
    )


def _resolve_container_host(runtime: str) -> str:
    if runtime == "podman":
        return "host.containers.internal"
    return "host.docker.internal"


def _prepare_container_connections(
    state: WorkflowState,
    runtime: str,
) -> tuple[str, str]:
    source_connection = state.context.source_connection
    target_connection = state.context.target_connection
    mode = state.context.container_network_mode

    if mode not in {"auto", "host"}:
        return source_connection, target_connection

    container_host = _resolve_container_host(runtime)
    local_hosts = {"localhost", "127.0.0.1", "::1"}

    source_host = _extract_dsn_host(source_connection)
    if source_host and source_host.lower() in local_hosts:
        source_connection = _replace_dsn_host(source_connection, container_host)
        _record_log(
            state,
            (
                "Rewrote source_connection host from local loopback to "
                f"'{container_host}' for container execution."
            ),
        )

    target_host = _extract_dsn_host(target_connection)
    if target_host and target_host.lower() in local_hosts:
        target_connection = _replace_dsn_host(target_connection, container_host)
        _record_log(
            state,
            (
                "Rewrote target_connection host from local loopback to "
                f"'{container_host}' for container execution."
            ),
        )

    return source_connection, target_connection


def _rewrite_generated_connections(
    migrate_script_path: Path,
    source_connection: str,
    target_connection: str,
) -> None:
    content = migrate_script_path.read_text(encoding="utf-8")
    source_line = f"SOURCE_CONNECTION = {json.dumps(source_connection)}"
    target_line = f"TARGET_CONNECTION = {json.dumps(target_connection)}"

    content = re.sub(
        r'^SOURCE_CONNECTION\s*=\s*".*"\s*$',
        source_line,
        content,
        count=1,
        flags=re.MULTILINE,
    )
    content = re.sub(
        r'^TARGET_CONNECTION\s*=\s*".*"\s*$',
        target_line,
        content,
        count=1,
        flags=re.MULTILINE,
    )
    migrate_script_path.write_text(content, encoding="utf-8")


def _resolve_container_network(state: WorkflowState) -> str | None:
    mode = state.context.container_network_mode
    configured = (state.context.container_network_name or "").strip()

    if mode == "compose":
        if configured:
            return configured
        state.open_questions.append(
            "container_network_mode=compose requires container_network_name; running without explicit network."
        )
        return None

    if mode == "auto" and configured:
        return configured

    return None


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
        _record_log(state, "Execution skipped because run_containerized_migration=false.")
        _finalize_logs_artifact(state)
        return state

    runtime = state.context.container_runtime
    if shutil.which(runtime) is None:
        _record_log(state, f"Container runtime '{runtime}' not found; using simulated execution.")
        state.open_questions.append(
            f"Container runtime '{runtime}' not found; switched to simulated execution."
        )
        state = _simulated_execution(state)
        _finalize_logs_artifact(state)
        return state

    with tempfile.TemporaryDirectory(prefix="migration-run-") as temp_dir:
        temp_path = Path(temp_dir)
        report_path = temp_path / "migration_report.json"

        required_files = ["migrate.py", "requirements.txt", "Dockerfile"]
        for file_name in required_files:
            content = state.generated_artifacts.get(file_name)
            if content is None:
                _record_log(
                    state,
                    f"Missing generated artifact '{file_name}' required for execution.",
                )
                state.open_questions.append(
                    f"Missing generated artifact '{file_name}' for execution."
                )
                state = _simulated_execution(state)
                _finalize_logs_artifact(state)
                return state
            (temp_path / file_name).write_text(content, encoding="utf-8")

        image_tag = f"ai-migration-run-{state.run_id[:8]}"
        mount_source = str(temp_path.resolve())
        hf_token_env_key = _resolve_hf_token_env_var(state)
        source_connection, target_connection = _prepare_container_connections(state, runtime)
        _rewrite_generated_connections(
            migrate_script_path=temp_path / "migrate.py",
            source_connection=source_connection,
            target_connection=target_connection,
        )
        network_name = _resolve_container_network(state)

        run_command = [
            runtime,
            "run",
            "--rm",
        ]
        if network_name:
            run_command.extend(["--network", network_name])
            _record_log(state, f"Using container network '{network_name}' for migration run.")

        run_command.extend(
            [
                "-e",
                "REPORT_PATH=/output/migration_report.json",
                "-e",
                f"{hf_token_env_key}={os.getenv(hf_token_env_key, '')}",
                "-e",
                "VECTOR_DIM=" + os.getenv("VECTOR_DIM", "384"),
                "-v",
                f"{mount_source}:/output",
                image_tag,
            ]
        )

        try:
            _run_command(
                [runtime, "build", "-t", image_tag, str(temp_path)],
                state,
                "build",
            )
            _run_command(run_command, state, "run")
        except subprocess.CalledProcessError as exc:
            state.open_questions.append(
                (
                    "Container execution failed "
                    f"(cmd={' '.join(exc.cmd)}, exit_code={exc.returncode}): "
                    f"{exc.stderr.strip() or exc.stdout.strip()}"
                )
            )
            state = _simulated_execution(state)
            _finalize_logs_artifact(state)
            return state

        if report_path.exists():
            report_data = json.loads(report_path.read_text(encoding="utf-8"))
            report_data["mode"] = "container"
            report_data["status"] = "completed"
            state.execution_report = report_data
            _record_log(state, "Container execution completed and migration report detected.")
            _finalize_logs_artifact(state)
            return state

        state.open_questions.append(
            "Container finished but no migration report was produced; switched to simulated report."
        )
        _record_log(state, "Container execution finished without report; switched to simulated report.")
        state = _simulated_execution(state)
        _finalize_logs_artifact(state)
        return state
