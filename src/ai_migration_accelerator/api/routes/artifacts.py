from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from ai_migration_accelerator.api.run_store import get_result
from ai_migration_accelerator.models.artifacts import ArtifactManifest

router = APIRouter()

_INTERNAL_ARTIFACT_KEYS = {
    "execution_logs.txt",
    "migrate_script_path.txt",
}


@router.get("/{run_id}", response_model=ArtifactManifest)
def get_artifacts(run_id: str) -> ArtifactManifest:
    result = get_result(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Artifacts not found")

    files = {
        name: content
        for name, content in result.generated_artifacts.items()
        if name not in _INTERNAL_ARTIFACT_KEYS
    }
    files["validation_report.json"] = json.dumps(result.validation_report, indent=2)
    return ArtifactManifest(run_id=run_id, files=files)
