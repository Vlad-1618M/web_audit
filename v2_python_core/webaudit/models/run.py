"""Audit run envelope — top-level JSON contract for a completed scan.

What: ``AuditRun``, ``AuditMeta``, ``AuditScores``, ``AuditArtifacts`` — schema for ``audit_run.json``.
Where: Built by ``orchestrator.run_audit()``; serialized by ``storage/runs.py`` and ``--json`` CLI.
How: ``run.to_json_dict()`` produces the on-disk JSON; ``schema_version`` is currently ``2.0``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from webaudit.models.finding import Finding


class AuditMeta(BaseModel):
    target_url: str
    started_at: str
    finished_at: str | None = None
    webaudit_version: str
    framework: str = "auto"


class AuditScores(BaseModel):
    hygiene: int = 100
    exposure: int = 100
    verdict: str = "PASS"


class AuditArtifacts(BaseModel):
    headers: dict[str, Any] = Field(default_factory=dict)
    dns: dict[str, Any] = Field(default_factory=dict)
    tls: dict[str, Any] = Field(default_factory=dict)
    inventory: dict[str, Any] = Field(default_factory=dict)
    plugins: dict[str, Any] = Field(default_factory=dict)
    seo_surface: dict[str, Any] = Field(default_factory=dict)


class AuditRun(BaseModel):
    schema_version: str = "2.0"
    meta: AuditMeta
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    scores: AuditScores = Field(default_factory=AuditScores)
    findings: list[Finding] = Field(default_factory=list)
    artifacts: AuditArtifacts = Field(default_factory=AuditArtifacts)
    reports: dict[str, str] = Field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "meta": self.meta.model_dump(),
            "config_snapshot": self.config_snapshot,
            "scores": self.scores.model_dump(),
            "findings": [f.to_json_dict() for f in self.findings],
            "artifacts": self.artifacts.model_dump(),
            "reports": self.reports,
        }
