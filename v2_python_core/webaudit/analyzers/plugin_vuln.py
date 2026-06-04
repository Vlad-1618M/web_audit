"""WordPress plugin/theme CVE matching from shipped snapshot + sqlite cache."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from webaudit.config.settings import VulnCollectorSettings
from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.profiles.loader import FrameworkProfile, ProfileVulnSettings
from webaudit.storage.vuln_cache import VulnCache
from webaudit.storage.vuln_snapshot import (
    VulnRecord,
    VulnSnapshot,
    load_vuln_snapshot,
    version_is_affected,
)

_AUTH_NONE = frozenset({"none", "unauthenticated", "no", "false"})
_AUTH_ADMIN = frozenset({"admin", "administrator", "authenticated"})


def _wpscan_url(unit: str, slug: str) -> str:
    if unit == "theme":
        return f"https://wpscan.com/theme/{slug}"
    return f"https://wpscan.com/plugin/{slug}"


def _severity_from_record(record: VulnRecord) -> Severity:
    mapping = {
        "CRITICAL": Severity.CRITICAL,
        "HIGH": Severity.HIGH,
        "MEDIUM": Severity.MEDIUM,
        "LOW": Severity.LOW,
    }
    return mapping.get(record.severity.upper(), Severity.MEDIUM)


def _class_for_auth(auth_required: str, profile_vuln: ProfileVulnSettings) -> tuple[FindingClass, bool]:
    auth = auth_required.lower()
    if auth in _AUTH_NONE:
        return FindingClass.ACTION, True
    if auth in _AUTH_ADMIN:
        return FindingClass.INFO, False
    if profile_vuln.auth_required_default_class.upper() == "INFO":
        return FindingClass.INFO, False
    return FindingClass.VERIFY, False


def _category_for_unit(unit: str) -> str:
    return "PLUGIN_CVE" if unit == "plugin" else "THEME_CVE"


def _normalize_slug(slug: str, profile: FrameworkProfile) -> str:
    return profile.normalize_slug(slug.lower())


def _lookup_hits(
    unit: str,
    slug: str,
    version: str | None,
    *,
    snapshot: VulnSnapshot,
    cache: VulnCache | None,
    source: str,
) -> list[VulnRecord]:
    if not version:
        return []

    cache_key_source = f"snapshot:{snapshot.updated}"
    if cache is not None:
        cached = cache.get(unit, slug, version, source=cache_key_source)
        if cached is not None:
            return [_record_from_hit(unit, hit) for hit in cached.hits]

    hits = [
        record
        for record in snapshot.records_for(unit, slug)
        if version_is_affected(version, record)
    ]

    if cache is not None:
        cache.put(
            unit,
            slug,
            version,
            source=cache_key_source,
            hits=[_hit_from_record(record) for record in hits],
        )

    return hits


def _hit_from_record(record: VulnRecord) -> dict[str, Any]:
    return {
        "unit": record.unit,
        "slug": record.slug,
        "cve_id": record.cve_id,
        "title": record.title,
        "auth_required": record.auth_required,
        "severity": record.severity,
        "cvss": record.cvss,
        "affected_min": record.affected_min,
        "affected_max": record.affected_max,
        "fixed_in": record.fixed_in,
        "aliases": record.aliases,
    }


def _record_from_hit(unit: str, hit: dict[str, Any]) -> VulnRecord:
    return VulnRecord(
        unit=unit,
        slug=str(hit.get("slug") or ""),
        cve_id=str(hit.get("cve_id") or ""),
        title=str(hit.get("title") or ""),
        auth_required=str(hit.get("auth_required") or "none"),
        severity=str(hit.get("severity") or "MEDIUM"),
        cvss=float(hit["cvss"]) if hit.get("cvss") is not None else None,
        affected_min=hit.get("affected_min"),
        affected_max=hit.get("affected_max"),
        fixed_in=hit.get("fixed_in"),
        aliases=[str(alias) for alias in hit.get("aliases") or []],
    )


def _finding_for_hit(
    *,
    unit: str,
    item_slug: str,
    version: str,
    record: VulnRecord,
    profile_vuln: ProfileVulnSettings,
) -> Finding:
    severity = _severity_from_record(record)
    class_, scored = _class_for_auth(record.auth_required, profile_vuln)
    category = _category_for_unit(unit)
    label = "plugin" if unit == "plugin" else "theme"
    detail = (
        f"{item_slug} {version} matches {record.cve_id} — {record.title} "
        f"(auth: {record.auth_required}; fixed in {record.fixed_in or 'vendor release'})"
    )
    return Finding.from_check(
        category=category,
        item=f"{item_slug}:{record.cve_id}",
        status="MATCH",
        severity=severity,
        detail=detail,
        class_=class_,
        scored=scored,
        evidence={
            "unit": unit,
            "slug": item_slug,
            "version": version,
            "cve_id": record.cve_id,
            "title": record.title,
            "auth_required": record.auth_required,
            "severity": record.severity,
            "cvss": record.cvss,
            "fixed_in": record.fixed_in,
            "affected_min": record.affected_min,
            "affected_max": record.affected_max,
            "wpscan_url": _wpscan_url(unit, item_slug),
            "source": "snapshot",
            "label": label,
        },
    )


def analyze_wordpress_vulns(
    extensions_artifact: dict[str, Any],
    profile: FrameworkProfile,
    settings: VulnCollectorSettings,
    *,
    profile_vuln: ProfileVulnSettings | None = None,
) -> tuple[list[Finding], dict[str, Any]]:
    """Match observed plugin/theme versions against CVE snapshot (+ sqlite cache)."""
    profile_vuln = profile_vuln or ProfileVulnSettings()
    if not settings.enabled or not profile_vuln.enabled:
        return [], {}

    source = settings.source or profile_vuln.source
    if source == "wporg_only":
        return [], {"enabled": False, "reason": "wporg_only skips CVE matching"}

    snapshot = load_vuln_snapshot(settings.snapshot_path or None)
    cache: VulnCache | None = None
    if settings.cache_enabled:
        cache_path = Path(settings.cache_path).expanduser() if settings.cache_path else None
        cache = VulnCache(cache_path, ttl_days=settings.cache_ttl_days or profile_vuln.cache_ttl_days)

    findings: list[Finding] = []
    matched_slugs: list[str] = []

    for item in extensions_artifact.get("extensions") or []:
        if not isinstance(item, dict):
            continue
        slug = _normalize_slug(str(item.get("name") or item.get("slug") or ""), profile)
        version = item.get("version")
        if not slug or not version:
            continue
        for record in _lookup_hits(
            "plugin",
            slug,
            str(version),
            snapshot=snapshot,
            cache=cache,
            source=source,
        ):
            findings.append(
                _finding_for_hit(
                    unit="plugin",
                    item_slug=slug,
                    version=str(version),
                    record=record,
                    profile_vuln=profile_vuln,
                )
            )
            matched_slugs.append(slug)

    themes_art = extensions_artifact.get("themes") or {}
    for theme_key in ("active", "parent"):
        theme = themes_art.get(theme_key)
        if not isinstance(theme, dict):
            continue
        slug = str(theme.get("slug") or "")
        version = theme.get("version")
        if not slug or not version:
            continue
        for record in _lookup_hits(
            "theme",
            slug.lower(),
            str(version),
            snapshot=snapshot,
            cache=cache,
            source=source,
        ):
            findings.append(
                _finding_for_hit(
                    unit="theme",
                    item_slug=slug,
                    version=str(version),
                    record=record,
                    profile_vuln=profile_vuln,
                )
            )
            matched_slugs.append(slug)

    artifact = {
        "enabled": True,
        "source": source,
        "snapshot_updated": snapshot.updated,
        "match_count": len(findings),
        "matched_slugs": sorted(set(matched_slugs)),
        "cache_path": str(cache.path) if cache is not None else "",
    }
    return findings, artifact
