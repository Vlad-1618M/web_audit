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
from pydantic import BaseModel, Field, model_validator


class RuntimeSettings(BaseModel):
    timeout_seconds: int = Field(default=15, ge=1, le=120)
    max_concurrency: int = Field(default=8, ge=1, le=32)
    probe_delay_ms: int = Field(default=0, ge=0)
    user_agent: str = "WebAudit/2.0"


class TargetSettings(BaseModel):
    url: str = ""
    framework: Literal["auto", "django", "wordpress", "laravel", "rails", "php", "unknown"] = "auto"


class PathsSettings(BaseModel):
    """Stage 2 — sensitive path probes (Exposure)."""

    enabled: bool = True
    sensitive_builtin: bool = True
    max_probe_urls: int = Field(default=250, ge=1, le=2000)
    extra_paths: list[str] = Field(default_factory=list)
    expected_open: list[str] = Field(default_factory=list)


class PolicySettings(BaseModel):
    """Stage 2 — HSTS/CSP deep parse (reads headers artifact; no collector)."""

    enabled: bool = True
    hsts_min_max_age_seconds: int = Field(default=15_552_000, ge=0)
    csp_detail_max_length: int = Field(default=500, ge=100, le=2000)


class DnsCollectorSettings(BaseModel):
    enabled: bool = True
    check_spf: bool = True
    check_dmarc: bool = True
    check_dkim: bool = False
    check_caa: bool = True
    check_dnssec: bool = True
    check_aaaa: bool = True
    check_a: bool = True
    check_mx: bool = True
    check_ns: bool = True
    check_asn: bool = True
    use_host_tools: bool = True


class TlsCollectorSettings(BaseModel):
    enabled: bool = True
    check_deprecated_versions: bool = True
    check_chain: bool = True
    check_ciphers: bool = False
    check_ocsp: bool = False
    expiry_warn_days: int = Field(default=30, ge=1, le=365)


class CookiesCollectorSettings(BaseModel):
    enabled: bool = True


class ArtifactsCollectorSettings(BaseModel):
    enabled: bool = True
    check_robots: bool = True
    check_security_txt: bool = True
    check_sitemap: bool = True
    max_robots_bytes: int = Field(default=12_000, ge=1000)
    max_security_txt_bytes: int = Field(default=8000, ge=500)
    max_sitemap_bytes: int = Field(default=16_000, ge=1000)
    max_sitemap_urls: int = Field(default=150, ge=1, le=500)


class RateLimitCollectorSettings(BaseModel):
    enabled: bool = True
    get_burst_count: int = Field(default=6, ge=1, le=20)
    post_burst_count: int = Field(default=15, ge=1, le=30)


class CorsCollectorSettings(BaseModel):
    enabled: bool = True
    probe_origin: str = "https://evil.example.com"
    api_paths: list[str] = Field(default_factory=lambda: ["/api/", "/api/v1/"])


class FrameworkCollectorSettings(BaseModel):
    enabled: bool = True
    probe_admin: bool = True
    max_body_bytes: int = Field(default=8000, ge=1000, le=200_000)


class HtmlCollectorSettings(BaseModel):
    enabled: bool = True
    check_mixed_content: bool = True
    check_forms: bool = True
    prefer_full_homepage_fetch: bool = True
    max_body_bytes: int = Field(default=65536, ge=1000, le=500_000)
    max_internal_links_sample: int = Field(default=50, ge=1, le=500)
    max_site_links: int = Field(default=1000, ge=1, le=5000)
    max_images: int = Field(default=500, ge=1, le=5000)
    max_sample_pages: int = Field(default=8, ge=1, le=32)
    max_sitemap_urls: int = Field(default=500, ge=1, le=5000)
    fetch_if_missing: bool = True


class WpPluginsCollectorSettings(BaseModel):
    """Stage 5 / Tier 2b — framework extension fingerprint (plugins, packages, gems)."""

    enabled: bool = True


ExtensionsCollectorSettings = WpPluginsCollectorSettings


class SeoSurfaceSettings(BaseModel):
    """Stage 5 / Tier 2c — discoverability checks (INFO/VERIFY only)."""

    enabled: bool = True
    check_meta_robots: bool = True
    check_canonical: bool = True
    check_meta_description: bool = True
    check_open_graph: bool = False
    check_robots_blocks: bool = True
    check_sitemap: bool = True
    sitemap_empty_threshold: int = Field(default=1, ge=0, le=100)
    check_broken_links: bool = False
    broken_link_sample_max: int = Field(default=20, ge=1, le=100)


class JsCollectorSettings(BaseModel):
    """Tier 2 — Playwright post-render DOM pass (optional ``webaudit[js]`` extra)."""

    enabled: bool = False
    wait_seconds: float = Field(default=3.0, ge=0, le=30)
    browser: Literal["chromium", "firefox", "webkit"] = "chromium"


class ApiCollectorSettings(BaseModel):
    """Tier 2 — GraphQL introspection and OpenAPI/Swagger discovery."""

    enabled: bool = False
    graphql_probe: bool = True
    graphql_paths: list[str] = Field(
        default_factory=lambda: ["/graphql", "/api/graphql", "/v1/graphql"],
    )
    openapi_paths: list[str] = Field(
        default_factory=lambda: [
            "/openapi.json",
            "/swagger.json",
            "/api/docs",
            "/swagger",
            "/swagger-ui/",
            "/redoc/",
        ],
    )


class CollectorsSettings(BaseModel):
    dns: DnsCollectorSettings = Field(default_factory=DnsCollectorSettings)
    tls: TlsCollectorSettings = Field(default_factory=TlsCollectorSettings)
    cookies: CookiesCollectorSettings = Field(default_factory=CookiesCollectorSettings)
    artifacts: ArtifactsCollectorSettings = Field(default_factory=ArtifactsCollectorSettings)
    rate_limit: RateLimitCollectorSettings = Field(default_factory=RateLimitCollectorSettings)
    cors: CorsCollectorSettings = Field(default_factory=CorsCollectorSettings)
    framework: FrameworkCollectorSettings = Field(default_factory=FrameworkCollectorSettings)
    html: HtmlCollectorSettings = Field(default_factory=HtmlCollectorSettings)
    extensions: ExtensionsCollectorSettings = Field(default_factory=ExtensionsCollectorSettings)
    wp_plugins: ExtensionsCollectorSettings = Field(default_factory=ExtensionsCollectorSettings)
    seo_surface: SeoSurfaceSettings = Field(default_factory=SeoSurfaceSettings)
    js: JsCollectorSettings = Field(default_factory=JsCollectorSettings)
    api: ApiCollectorSettings = Field(default_factory=ApiCollectorSettings)

    @model_validator(mode="before")
    @classmethod
    def _merge_legacy_wp_plugins(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "wp_plugins" in data and "extensions" not in data:
            data = dict(data)
            data["extensions"] = data["wp_plugins"]
        elif "extensions" in data and "wp_plugins" not in data:
            data = dict(data)
            data["wp_plugins"] = data["extensions"]
        return data


class HygieneWeights(BaseModel):
    CRITICAL: int = 25
    HIGH: int = 10
    MEDIUM: int = 4
    LOW: int = 1


class ScoringSettings(BaseModel):
    hygiene_weights: HygieneWeights = Field(default_factory=HygieneWeights)
    hygiene_caps: dict[str, int] = Field(default_factory=lambda: {"PLUGIN": 30, "PLUGIN_CVE": 30})
    plugin_worst_wins: bool = True
    seo_surface_affects_scores: bool = False


class ReportSettings(BaseModel):
    variant: str = "owner"
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
    policy: PolicySettings = Field(default_factory=PolicySettings)
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
