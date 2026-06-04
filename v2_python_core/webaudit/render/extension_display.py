"""Extension / plugin version section for HTML reports."""

from __future__ import annotations

from typing import Any

from webaudit.analyzers.extension_compare import (
    registry_for_framework,
    registry_meta,
    registry_package_url,
)
from webaudit.models.finding import Finding
from webaudit.profiles.loader import load_framework_profile

_EXTENSION_CATEGORIES = frozenset(
    {
        "PLUGIN",
        "PLUGIN_VERIFY",
        "PLUGIN_INFO",
        "PACKAGE",
        "PACKAGE_VERIFY",
        "PACKAGE_INFO",
        "GEM",
        "GEM_VERIFY",
        "GEM_INFO",
    }
)

_FRAMEWORK_LABELS = {
    "wordpress": "WordPress",
    "django": "Django",
    "laravel": "Laravel",
    "rails": "Ruby on Rails",
    "php": "PHP",
}

_UNIT_PLURAL = {
    "plugin": "plugins",
    "package": "packages",
    "gem": "gems",
    "runtime": "runtime signals",
}

_STATUS_TONE = {
    "CURRENT": "good",
    "STALE": "bad",
    "UNKNOWN": "warn",
    "UNKNOWN_SLUG": "warn",
    "VERSION_UNVERIFIED": "warn",
    "UNVERIFIABLE": "neutral",
    "NO_VERSION": "warn",
    "OBSERVED": "neutral",
    "PREMIUM_OR_UNVERIFIABLE": "neutral",
}


def _finding_map(findings: list[Finding]) -> dict[str, Finding]:
    mapped: dict[str, Finding] = {}
    for finding in findings:
        if finding.category not in _EXTENSION_CATEGORIES:
            continue
        mapped[finding.item] = finding
    return mapped


def _compare_enabled(profile, registry: str | None) -> bool:
    if registry == "wporg":
        return profile.compare.wporg_api
    if registry == "pypi":
        return profile.compare.pypi_api
    if registry == "packagist":
        return profile.compare.packagist_api
    if registry == "rubygems":
        return profile.compare.rubygems_api
    return False


def _latest_from_evidence(evidence: dict[str, Any]) -> str:
    for key in ("latest", "latest_wporg"):
        value = evidence.get(key)
        if value:
            return str(value)
    return ""


def build_extension_section(
    artifacts: dict[str, Any],
    findings: list[Finding],
    *,
    framework: str,
) -> dict[str, Any] | None:
    ext_art = artifacts.get("extensions") or artifacts.get("plugins") or {}
    if not ext_art and not any(f.category in _EXTENSION_CATEGORIES for f in findings):
        return None

    profile = load_framework_profile(framework)
    unit = str(ext_art.get("unit") or (profile.fingerprint_unit if profile else "extension"))
    registry = registry_for_framework(framework)
    reg = registry_meta(registry)
    compare_on = bool(profile and registry and _compare_enabled(profile, registry))

    finding_by_item = _finding_map(findings)
    watchlist = profile.watchlist_map() if profile else {}
    rows: list[dict[str, str]] = []

    for item in ext_art.get("extensions") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("slug") or "")
        if not name:
            continue
        finding = finding_by_item.get(name)
        evidence = finding.evidence if finding else {}
        status = finding.status if finding else "OBSERVED"
        latest = _latest_from_evidence(evidence)
        entry = watchlist.get(name)
        rows.append(
            {
                "name": name,
                "detected_version": str(item.get("version") or "—"),
                "latest_version": latest or ("—" if compare_on else "n/a"),
                "source": str(item.get("source") or "—"),
                "status": status,
                "status_tone": _STATUS_TONE.get(status, "neutral"),
                "detail": (finding.detail if finding else "") or "",
                "tier": entry.tier if entry else "",
                "on_watchlist": "yes" if entry else "",
                "registry_url": registry_package_url(registry, name) or "",
            }
        )

    rows.sort(key=lambda row: row["name"])

    stale_count = sum(1 for row in rows if row["status"] == "STALE")
    current_count = sum(1 for row in rows if row["status"] == "CURRENT")
    compared_count = sum(1 for row in rows if row["latest_version"] not in {"", "—", "n/a"})

    none_observed = next(
        (
            finding
            for finding in findings
            if finding.category in _EXTENSION_CATEGORIES and finding.status.upper() == "NONE_OBSERVED"
        ),
        None,
    )
    framework_meta = (artifacts.get("inventory") or {}).get("framework") or {}
    powered_by = str(framework_meta.get("powered_by") or "")
    frontend_note = ""
    if not rows and powered_by and "next" in powered_by.lower():
        frontend_note = (
            f"Public HTML is served by {powered_by}. WordPress may run behind the scenes, "
            "but plugin asset paths are not exposed in the homepage HTML this scan could read."
        )

    passive_scan_note = ""
    if framework == "wordpress":
        passive_scan_note = (
            "Passive scan: only plugins that enqueue public CSS/JS on the scanned page appear here. "
            "wp-admin may list many more installed plugins with no public asset URLs on this URL."
        )

    return {
        "framework": framework,
        "framework_label": _FRAMEWORK_LABELS.get(framework, framework.title()),
        "profile_name": f"{framework}/extensions.yaml",
        "unit": unit,
        "unit_plural": _UNIT_PLURAL.get(unit, f"{unit}s"),
        "registry": registry or "",
        "registry_label": reg["label"] if reg else "",
        "registry_home": reg["home"] if reg else "",
        "compare_enabled": compare_on,
        "watchlist_count": len(watchlist),
        "detected_count": len(rows),
        "compared_count": compared_count,
        "stale_count": stale_count,
        "current_count": current_count,
        "mode": str(ext_art.get("mode") or "observed_only"),
        "rows": rows,
        "has_rows": bool(rows),
        "error": str(ext_art.get("error") or ""),
        "none_observed_detail": none_observed.detail if none_observed else "",
        "frontend_note": frontend_note,
        "passive_scan_note": passive_scan_note,
    }
