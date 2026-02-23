from __future__ import annotations

from pydantic import BaseModel, Field


class ArtifactManifest(BaseModel):
    run_id: str
    files: dict[str, str] = Field(default_factory=dict)


class ValidationSummary(BaseModel):
    run_id: str
    passed: bool
    checks: dict[str, str] = Field(default_factory=dict)
