"""WordPress theme section for HTML reports."""

from __future__ import annotations

from typing import Any

from webaudit.analyzers.extension_compare import registry_meta
from webaudit.models.finding import Finding
from webaudit.profiles.loader import load_framework_profile

_THEME_CATEGORIES = frozenset({"THEME", "THEME_VERIFY", "THEME_INFO", "THEME_CVE"})

_STATUS_TONE = {
    "CURRENT": "good",
    "STALE": "bad",
    "CHILD_THEME": "good",
    "UPDATE_TRAP_RISK": "warn",
    "EDITOR_UNVERIFIABLE": "warn",
    "PREMIUM_OR_UNVERIFIABLE": "neutral",
    "UNKNOWN_SLUG": "warn",
    "NO_VERSION": "warn",
    "NONE_OBSERVED": "neutral",
}


def _finding_map(findings: list[Finding]) -> dict[str, Finding]:
    mapped: dict[str, Finding] = {}
    for finding in findings:
        if finding.category not in _THEME_CATEGORIES:
            continue
        mapped[finding.item] = finding
    return mapped


def build_theme_section(
    artifacts: dict[str, Any],
    findings: list[Finding],
    *,
    framework: str,
) -> dict[str, Any] | None:
    if framework != "wordpress":
        return None

    ext_art = artifacts.get("extensions") or artifacts.get("plugins") or {}
    themes_art = ext_art.get("themes") or {}
    active = themes_art.get("active") if isinstance(themes_art, dict) else None
    parent = themes_art.get("parent") if isinstance(themes_art, dict) else None
    theme_findings = [f for f in findings if f.category in _THEME_CATEGORIES]

    if not active and not theme_findings:
        return None

    profile = load_framework_profile("wordpress")
    compare_on = bool(profile and profile.compare.wporg_api)
    reg = registry_meta("wporg")
    finding_by_item = _finding_map(theme_findings)
    watchlist = profile.theme_watchlist_map() if profile else {}

    rows: list[dict[str, str]] = []

    def _append_row(theme: dict[str, Any], *, role: str) -> None:
        slug = str(theme.get("slug") or "")
        if not slug:
            return
        finding = finding_by_item.get(slug)
        status = finding.status if finding else "OBSERVED"
        evidence = finding.evidence if finding else {}
        latest = str(evidence.get("latest_wporg") or "")
        entry = watchlist.get(slug)
        rows.append(
            {
                "slug": slug,
                "name": str(theme.get("name") or slug),
                "role": role,
                "detected_version": str(theme.get("version") or "—"),
                "latest_version": latest or ("—" if compare_on else "n/a"),
                "is_child": "yes" if theme.get("is_child_theme") else "",
                "parent_slug": str(theme.get("parent_slug") or ""),
                "status": status,
                "status_tone": _STATUS_TONE.get(status, "neutral"),
                "detail": (finding.detail if finding else "") or "",
                "tier": entry.tier if entry else "",
                "registry_url": f"https://wordpress.org/themes/{slug}/" if slug else "",
            }
        )

    if isinstance(active, dict):
        _append_row(active, role="Active theme")
    if isinstance(parent, dict):
        _append_row(parent, role="Parent theme")

    advisory = finding_by_item.get("wp-config hardening")
    none_observed = finding_by_item.get("WordPress theme")

    stale_count = sum(1 for row in rows if row["status"] == "STALE")
    child_detected = any(row["status"] == "CHILD_THEME" for row in rows) or (
        isinstance(active, dict) and active.get("is_child_theme")
    )

    return {
        "framework": "wordpress",
        "profile_name": "wordpress/extensions.yaml",
        "compare_enabled": compare_on,
        "registry_label": reg["label"] if reg else "WordPress.org Theme Directory",
        "registry_home": "https://wordpress.org/themes/",
        "watchlist_count": len(watchlist),
        "detected_count": len(rows),
        "stale_count": stale_count,
        "child_detected": child_detected,
        "has_rows": bool(rows),
        "rows": rows,
        "advisory": {
            "status": advisory.status if advisory else "",
            "detail": advisory.detail if advisory else "",
            "tone": _STATUS_TONE.get(advisory.status if advisory else "", "neutral"),
        }
        if advisory
        else None,
        "none_observed_detail": none_observed.detail if none_observed and none_observed.status == "NONE_OBSERVED" else "",
        "error": str(themes_art.get("error") or "") if isinstance(themes_art, dict) else "",
    }
