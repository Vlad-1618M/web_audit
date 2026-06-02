"""YAML configuration loader and Pydantic settings models.

What: Defines ``Settings`` and ``load_settings()`` — merges defaults, user, project, and CLI paths.
Where: Used by ``cli/main.py`` before a scan; snapshot stored in ``audit_run.json``.
How: ``load_settings(config_path=..., site_config_path=..., target_url=...)`` returns validated settings.
      Shipped defaults live in ``webaudit/config/defaults.yaml``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class RuntimeSettings(BaseModel):
    timeout_seconds: int = Field(default=15, ge=1, le=120)
    max_concurrency: int = Field(default=8, ge=1, le=32)
    probe_delay_ms: int = Field(default=0, ge=0)
    user_agent: str = "WebAudit/2.0"


class TargetSettings(BaseModel):
    url: str = ""
    framework: Literal["auto", "django", "wordpress", "laravel", "rails", "php", "unknown"] = "auto"


class PathsSettings(BaseModel):
    """Stage 2 — sensitive path probes (Exposure). Stub wired in defaults.yaml; collector TBD."""

    sensitive_builtin: bool = True
    max_probe_urls: int = Field(default=250, ge=1, le=2000)


class DnsCollectorSettings(BaseModel):
    enabled: bool = True
    check_spf: bool = True
    check_dmarc: bool = True
    check_dkim: bool = False
    check_caa: bool = True
    check_dnssec: bool = True
    check_aaaa: bool = True


class CollectorsSettings(BaseModel):
    dns: DnsCollectorSettings = Field(default_factory=DnsCollectorSettings)


class HygieneWeights(BaseModel):
    CRITICAL: int = 25
    HIGH: int = 10
    MEDIUM: int = 4
    LOW: int = 1


class ScoringSettings(BaseModel):
    hygiene_weights: HygieneWeights = Field(default_factory=HygieneWeights)
    seo_surface_affects_scores: bool = False


class ReportSettings(BaseModel):
    variant: str = "technical"
    theme: str = "dark"


class OutputSettings(BaseModel):
    directory: str = "./audit_logs"
    formats: list[str] = Field(default_factory=lambda: ["json"])


class CiSettings(BaseModel):
    fail_under_hygiene: int | None = None
    fail_under_exposure: int | None = None


class Settings(BaseModel):
    webaudit_version: str = "2.0"
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    target: TargetSettings = Field(default_factory=TargetSettings)
    paths: PathsSettings = Field(default_factory=PathsSettings)
    collectors: CollectorsSettings = Field(default_factory=CollectorsSettings)
    scoring: ScoringSettings = Field(default_factory=ScoringSettings)
    report: ReportSettings = Field(default_factory=ReportSettings)
    output: OutputSettings = Field(default_factory=OutputSettings)
    ci: CiSettings = Field(default_factory=CiSettings)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return data


def default_config_path() -> Path:
    return Path(__file__).resolve().parent / "defaults.yaml"


def load_settings(
    *,
    config_path: Path | None = None,
    site_config_path: Path | None = None,
    target_url: str | None = None,
) -> Settings:
    data = _load_yaml(default_config_path())

    user_path = Path.home() / ".config" / "webaudit" / "config.yaml"
    data = _deep_merge(data, _load_yaml(user_path))

    project_path = Path.cwd() / "webaudit.yaml"
    data = _deep_merge(data, _load_yaml(project_path))

    if config_path:
        data = _deep_merge(data, _load_yaml(config_path))

    if site_config_path:
        data = _deep_merge(data, _load_yaml(site_config_path))

    settings = Settings.model_validate(data)

    if target_url:
        settings.target.url = target_url.rstrip("/")

    return settings
