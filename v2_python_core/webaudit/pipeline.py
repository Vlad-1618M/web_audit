"""Scan pipeline registry — ordered collector/analyzer steps for orchestrator.

What: ``run_pipeline()`` runs all registered scan steps and returns findings + artifacts.
Where: Called exclusively from ``orchestrator.run_audit()`` — add Stage 2 modules here.
How: Each step is optional (config-gated). Append findings; merge artifact dicts by key.
      Do not add scoring or HTTP calls inside analyzers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from webaudit.cli.scan_progress import ScanProgress

from webaudit.analyzers.artifacts import analyze_artifacts
from webaudit.analyzers.cookies import analyze_cookies
from webaudit.analyzers.cors import analyze_cors
from webaudit.analyzers.dns import analyze_dns
from webaudit.analyzers.framework import analyze_framework
from webaudit.analyzers.headers import analyze_headers
from webaudit.analyzers.html import analyze_html
from webaudit.analyzers.paths import analyze_paths
from webaudit.analyzers.extensions import analyze_extensions
from webaudit.analyzers.extension_compare import registry_for_framework, registry_meta
from webaudit.analyzers.policy import analyze_policy
from webaudit.analyzers.rate_limit import analyze_rate_limit
from webaudit.analyzers.seo_surface import analyze_seo_surface
from webaudit.analyzers.tls import analyze_tls
from webaudit.collectors.extensions import collect_extensions
from webaudit.collectors.artifacts import collect_artifacts
from webaudit.collectors.cookies import collect_cookies
from webaudit.collectors.cors import collect_cors
from webaudit.collectors.dns import collect_dns
from webaudit.collectors.framework import collect_framework
from webaudit.collectors.headers import collect_headers
from webaudit.collectors.html import HtmlProbeResult, collect_html, parse_html_inventory
from webaudit.collectors.paths import collect_paths
from webaudit.collectors.rate_limit import collect_rate_limit
from webaudit.collectors.tls import collect_tls
from webaudit.config.settings import Settings
from webaudit.models.finding import Finding
from webaudit.cli.scan_progress import STEP_LABELS, step_enabled
from webaudit.profiles.loader import load_framework_profile


@dataclass
class PipelineResult:
    findings: list[Finding] = field(default_factory=list)
    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)


def _step_headers(settings: Settings) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    probe = collect_headers(
        settings.target.url,
        user_agent=settings.runtime.user_agent,
        timeout_seconds=settings.runtime.timeout_seconds,
    )
    return analyze_headers(probe), {"headers": probe.to_artifact()}


def _apply_detected_framework(settings: Settings, effective: str) -> None:
    if settings.target.framework not in {"auto", "unknown"}:
        return
    if effective in {"django", "wordpress", "laravel", "rails", "php"}:
        settings.target.framework = effective  # type: ignore[assignment]


def _step_framework(
    settings: Settings,
    result: PipelineResult,
) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    if not settings.collectors.framework.enabled:
        return [], {}
    headers_artifact = result.artifacts.get("headers", {})
    header_map = headers_artifact.get("headers") or {}
    probe = collect_framework(
        settings.target.url,
        forced_framework=settings.target.framework,
        headers=header_map,
        user_agent=settings.runtime.user_agent,
        timeout_seconds=settings.runtime.timeout_seconds,
        max_body_bytes=settings.collectors.framework.max_body_bytes,
        probe_admin=settings.collectors.framework.probe_admin,
    )
    _apply_detected_framework(settings, probe.effective_framework)
    findings = analyze_framework(probe, settings.collectors.framework)
    return findings, {"inventory": {"framework": probe.to_artifact()}}


def _step_dns(settings: Settings) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    if not settings.collectors.dns.enabled:
        return [], {}
    probe = collect_dns(
        settings.target.url,
        timeout_seconds=settings.runtime.timeout_seconds,
        check_spf=settings.collectors.dns.check_spf,
        check_dmarc=settings.collectors.dns.check_dmarc,
        check_caa=settings.collectors.dns.check_caa,
        check_dnssec=settings.collectors.dns.check_dnssec,
        check_aaaa=settings.collectors.dns.check_aaaa,
        check_a=settings.collectors.dns.check_a,
        check_mx=settings.collectors.dns.check_mx,
        check_ns=settings.collectors.dns.check_ns,
        check_asn=settings.collectors.dns.check_asn,
        use_host_tools=settings.collectors.dns.use_host_tools,
    )
    return analyze_dns(probe, settings.collectors.dns), {"dns": probe.to_artifact()}


def _step_paths(settings: Settings) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    if not settings.paths.enabled:
        return [], {}
    probe = collect_paths(
        settings.target.url,
        framework=settings.target.framework,
        paths_settings=settings.paths,
        user_agent=settings.runtime.user_agent,
        timeout_seconds=settings.runtime.timeout_seconds,
        probe_delay_ms=settings.runtime.probe_delay_ms,
    )
    findings = analyze_paths(
        probe,
        framework=settings.target.framework,
        paths_settings=settings.paths,
    )
    return findings, {"inventory": {"paths": probe.to_artifact()}}


def _step_tls(settings: Settings) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    if not settings.collectors.tls.enabled:
        return [], {}
    probe = collect_tls(
        settings.target.url,
        timeout_seconds=settings.runtime.timeout_seconds,
        probe_versions=settings.collectors.tls.check_deprecated_versions,
        fetch_certificate=True,
    )
    findings = analyze_tls(probe, settings.collectors.tls)
    return findings, {"tls": probe.to_artifact()}


def _step_policy(
    settings: Settings,
    result: PipelineResult,
) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    if not settings.policy.enabled:
        return [], {}
    headers_artifact = result.artifacts.get("headers", {})
    header_map = headers_artifact.get("headers") or {}
    if not header_map:
        return [], {}
    findings, parsed = analyze_policy(header_map, settings.policy)
    return findings, {"policy": parsed.to_artifact()}


def _step_cookies(settings: Settings) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    if not settings.collectors.cookies.enabled:
        return [], {}
    probe = collect_cookies(
        settings.target.url,
        framework=settings.target.framework,
        user_agent=settings.runtime.user_agent,
        timeout_seconds=settings.runtime.timeout_seconds,
    )
    findings = analyze_cookies(probe, settings.collectors.cookies, framework=settings.target.framework)
    return findings, {"inventory": {"cookies": probe.to_artifact()}}


def _step_rate_limit(settings: Settings) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    if not settings.collectors.rate_limit.enabled:
        return [], {}
    probe = collect_rate_limit(
        settings.target.url,
        framework=settings.target.framework,
        settings=settings.collectors.rate_limit,
        user_agent=settings.runtime.user_agent,
        timeout_seconds=settings.runtime.timeout_seconds,
    )
    findings = analyze_rate_limit(probe, settings.collectors.rate_limit)
    return findings, {"inventory": {"rate_limit": probe.to_artifact()}}


def _step_artifacts(
    settings: Settings,
    result: PipelineResult,
) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    if not settings.collectors.artifacts.enabled:
        return [], {}
    probe = collect_artifacts(
        settings.target.url,
        settings=settings.collectors.artifacts,
        user_agent=settings.runtime.user_agent,
        timeout_seconds=settings.runtime.timeout_seconds,
    )
    paths_data = result.artifacts.get("inventory", {}).get("paths", {})
    open_paths = paths_data.get("paths", [])
    findings = analyze_artifacts(probe, settings.collectors.artifacts, open_paths=open_paths)
    return findings, {"inventory": {"artifacts": probe.to_artifact()}}


def _step_cors(settings: Settings) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    if not settings.collectors.cors.enabled:
        return [], {}
    probe = collect_cors(
        settings.target.url,
        settings=settings.collectors.cors,
        user_agent=settings.runtime.user_agent,
        timeout_seconds=settings.runtime.timeout_seconds,
        extra_api_paths=settings.paths.extra_paths,
    )
    findings = analyze_cors(probe, settings.collectors.cors)
    return findings, {"inventory": {"cors": probe.to_artifact()}}


def _step_html(
    settings: Settings,
    result: PipelineResult,
) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    if not settings.collectors.html.enabled:
        return [], {}

    from webaudit.collectors.site_discovery import enrich_site_inventory
    from webaudit.collectors.sitemap import collect_sitemap_urls

    html_settings = settings.collectors.html
    framework_artifact = result.artifacts.get("inventory", {}).get("framework", {})
    framework_body = framework_artifact.get("body", "")

    use_framework_body = (
        bool(framework_body)
        and not html_settings.prefer_full_homepage_fetch
        and not html_settings.fetch_if_missing
    )

    if use_framework_body:
        probe = HtmlProbeResult(
            target_url=settings.target.url,
            body=framework_body,
            pages_scanned=1,
        )
        probe.inventory = parse_html_inventory(
            framework_body,
            target_url=settings.target.url,
            check_mixed_content=html_settings.check_mixed_content,
            check_forms=html_settings.check_forms,
            max_internal_links=html_settings.max_internal_links_sample,
            max_site_links=html_settings.max_site_links,
            max_images=html_settings.max_images,
        )
    else:
        body = framework_body if framework_body and not html_settings.prefer_full_homepage_fetch else ""
        probe = collect_html(
            settings.target.url,
            body=body,
            user_agent=settings.runtime.user_agent,
            timeout_seconds=settings.runtime.timeout_seconds,
            max_body_bytes=html_settings.max_body_bytes,
            max_internal_links=html_settings.max_internal_links_sample,
            max_site_links=html_settings.max_site_links,
            max_images=html_settings.max_images,
        )
        if probe.body and not probe.inventory.site_links:
            probe.inventory = parse_html_inventory(
                probe.body,
                target_url=settings.target.url,
                check_mixed_content=html_settings.check_mixed_content,
                check_forms=html_settings.check_forms,
                max_internal_links=html_settings.max_internal_links_sample,
                max_site_links=html_settings.max_site_links,
                max_images=html_settings.max_images,
            )

    artifacts_data = result.artifacts.get("inventory", {}).get("artifacts", {})
    sitemap_raw = (artifacts_data.get("sitemap") or {}).get("raw") or ""
    sitemap_urls: list[str] = []
    if sitemap_raw:
        sitemap_urls, _child_sitemaps = collect_sitemap_urls(
            settings.target.url,
            sitemap_raw,
            user_agent=settings.runtime.user_agent,
            timeout_seconds=settings.runtime.timeout_seconds,
            max_urls=html_settings.max_sitemap_urls,
            max_sitemap_bytes=settings.collectors.artifacts.max_sitemap_bytes,
        )

    pages_sampled, sitemap_count = enrich_site_inventory(
        probe.inventory,
        target_url=settings.target.url,
        sitemap_urls=sitemap_urls,
        user_agent=settings.runtime.user_agent,
        timeout_seconds=settings.runtime.timeout_seconds,
        max_sample_pages=html_settings.max_sample_pages,
        max_body_bytes=html_settings.max_body_bytes,
        max_site_links=html_settings.max_site_links,
        max_images=html_settings.max_images,
        check_mixed_content=html_settings.check_mixed_content,
        check_forms=html_settings.check_forms,
    )
    probe.inventory.pages_sampled = max(probe.pages_scanned, pages_sampled)
    probe.inventory.sitemap_urls_parsed = sitemap_count
    probe.pages_scanned = probe.inventory.pages_sampled

    findings = analyze_html(probe, html_settings)
    artifact = probe.to_artifact()
    body_for_attr = probe.body or framework_body
    from webaudit.collectors.attribution import extract_attribution

    attribution = extract_attribution(body_for_attr, base_url=settings.target.url)
    if body_for_attr:
        artifact["scan_html"] = body_for_attr
    return findings, {
        "inventory": {
            "html": artifact,
            "attribution": attribution.to_dict(),
        }
    }


_EXTENSION_FRAMEWORKS = frozenset({"wordpress", "django", "laravel", "rails", "php"})


def _step_extensions(
    settings: Settings,
    result: PipelineResult,
) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    if not settings.collectors.extensions.enabled:
        return [], {}

    framework = settings.target.framework
    if framework not in _EXTENSION_FRAMEWORKS:
        return [], {}

    profile = load_framework_profile(framework)
    if profile is None:
        return [], {}

    framework_artifact = result.artifacts.get("inventory", {}).get("framework", {})
    html_artifact = result.artifacts.get("inventory", {}).get("html", {})
    body = html_artifact.get("scan_html") or framework_artifact.get("body", "")
    headers_artifact = result.artifacts.get("headers", {})
    header_map = headers_artifact.get("headers") or {}

    if not body and framework != "php":
        return [], {}

    probe = collect_extensions(
        settings.target.url,
        framework,
        body,
        headers=header_map,
        user_agent=settings.runtime.user_agent,
        timeout_seconds=settings.runtime.timeout_seconds,
        profile=profile,
    )
    findings = analyze_extensions(
        probe,
        profile,
        user_agent=settings.runtime.user_agent,
        timeout_seconds=settings.runtime.timeout_seconds,
    )
    artifact = probe.to_artifact()
    registry = registry_for_framework(framework)
    if registry:
        artifact["registry"] = registry
        meta = registry_meta(registry)
        if meta:
            artifact["registry_label"] = meta["label"]
            artifact["registry_home"] = meta["home"]
    artifact["profile"] = f"{framework}/extensions.yaml"
    return findings, {"extensions": artifact, "plugins": artifact if framework == "wordpress" else {}}


def _step_seo_surface(
    settings: Settings,
    result: PipelineResult,
) -> tuple[list[Finding], dict[str, dict[str, Any]]]:
    seo_settings = settings.collectors.seo_surface
    if not seo_settings.enabled:
        return [], {}

    framework_artifact = result.artifacts.get("inventory", {}).get("framework", {})
    body = framework_artifact.get("body", "")
    artifacts_data = result.artifacts.get("inventory", {}).get("artifacts", {})

    findings, summary = analyze_seo_surface(body, artifacts_data, seo_settings)
    return findings, {"seo_surface": summary}


# Stage 2+: register new steps here in planned order (see docs/implementation_tracker.md)
_CONTEXT_STEPS = frozenset({
    "_step_policy",
    "_step_artifacts",
    "_step_framework",
    "_step_html",
    "_step_extensions",
    "_step_seo_surface",
})
_PIPELINE: tuple[Callable[..., tuple[list[Finding], dict[str, dict[str, Any]]]], ...] = (
    _step_headers,
    _step_framework,
    _step_dns,
    _step_paths,
    _step_tls,
    _step_policy,
    _step_cookies,
    _step_rate_limit,
    _step_artifacts,
    _step_cors,
    _step_html,
    _step_extensions,
    _step_seo_surface,
)


def run_pipeline(
    settings: Settings,
    *,
    progress: ScanProgress | None = None,
) -> PipelineResult:
    """Execute all pipeline steps; merge findings and artifact fragments."""
    result = PipelineResult()
    for step in _PIPELINE:
        step_name = step.__name__
        label, description = STEP_LABELS.get(step_name, (step_name, ""))
        if not step_enabled(step_name, settings):
            if progress:
                progress.step_skipped(label)
            continue
        if progress:
            progress.step_start(label, description)
        if step_name in _CONTEXT_STEPS:
            findings, artifact_parts = step(settings, result)
        else:
            findings, artifact_parts = step(settings)
        result.findings.extend(findings)
        for key, value in artifact_parts.items():
            if key == "inventory" and key in result.artifacts:
                result.artifacts[key] = {**result.artifacts[key], **value}
            else:
                result.artifacts[key] = value
        if progress:
            progress.step_done(step_name, label, findings, artifact_parts)
    return result
