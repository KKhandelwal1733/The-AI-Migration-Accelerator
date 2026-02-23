from __future__ import annotations

from fastapi import APIRouter

from ai_migration_accelerator.models.artifacts import ArtifactManifest

router = APIRouter()


@router.get("/{run_id}", response_model=ArtifactManifest)
def get_artifacts(run_id: str) -> ArtifactManifest:
    return ArtifactManifest(
        run_id=run_id,
        files={
            "generated_pipeline.py": "Use deterministic templates in generator/templates.",
            "validation_report.json": "Use /jobs/{run_id} for status and open questions.",
        },
    )
