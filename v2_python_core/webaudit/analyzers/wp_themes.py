"""WordPress theme analyzer — version compare, child theme, update-trap, hardening hints."""

from __future__ import annotations

from typing import Any

from packaging.version import Version

from webaudit.analyzers.extension_compare import fetch_wporg_theme_version
from webaudit.analyzers.wp_plugins import _parse_version
from webaudit.collectors.wp_themes import ObservedTheme, WpThemesProbeResult
from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.profiles.loader import FrameworkProfile, WatchlistEntry

_ADMIN_PATHS = frozenset({"/wp-admin", "/wp-admin/", "/wp-login.php"})


def _severity_for_theme_gap(detected: Version, latest: Version) -> Severity:
    if detected.major < latest.major:
        return Severity.HIGH
    gap_minor = latest.minor - detected.minor
    if gap_minor >= 2:
        return Severity.MEDIUM
    if gap_minor == 1:
        return Severity.LOW
    if detected.micro < latest.micro:
        return Severity.LOW
    return Severity.INFO


def _theme_watchlist_entry(profile: FrameworkProfile, slug: str) -> WatchlistEntry | None:
    return profile.theme_watchlist_map().get(slug)


def _is_premium_theme(entry: WatchlistEntry | None, latest: str | None) -> bool:
    if entry and entry.premium:
        return True
    if entry and not entry.compare_latest:
        return True
    return latest is None and entry is not None and entry.tier in {"high", "critical"}


def _admin_reachable(path_probes: list[dict[str, Any]] | None) -> bool:
    if not path_probes:
        return False
    for probe in path_probes:
        path = str(probe.get("path") or "")
        if path not in _ADMIN_PATHS:
            continue
        code = probe.get("final_status") or probe.get("status_code")
        if code in {200, 301, 302, 307, 308}:
            return True
    return False


def analyze_wp_themes(
    probe: WpThemesProbeResult,
    profile: FrameworkProfile,
    *,
    user_agent: str,
    timeout_seconds: int,
    client: Any | None = None,
    path_probes: list[dict[str, Any]] | None = None,
) -> list[Finding]:
    if probe.error and not probe.active:
        return [
            Finding.from_check(
                category="THEME",
                item="Theme probe",
                status="ERROR",
                severity=Severity.INFO,
                detail=probe.error,
                class_=FindingClass.INFO,
                scored=False,
            )
        ]

    if not probe.active:
        return [
            Finding.from_check(
                category="THEME_INFO",
                item="WordPress theme",
                status="NONE_OBSERVED",
                severity=Severity.INFO,
                detail="No theme paths observed in HTML asset URLs",
                class_=FindingClass.INFO,
                scored=False,
            )
        ]

    import httpx

    findings: list[Finding] = []
    own_client = client is None and profile.compare.wporg_api
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    try:
        version_target = probe.parent if probe.active.is_child_theme and probe.parent else probe.active

        if probe.active.is_child_theme:
            findings.append(
                Finding.from_check(
                    category="THEME_INFO",
                    item=probe.active.slug,
                    status="CHILD_THEME",
                    severity=Severity.INFO,
                    detail=(
                        f"Child theme {probe.active.name or probe.active.slug} detected "
                        f"(parent: {probe.active.parent_slug}) — customizations likely isolated from parent updates"
                    ),
                    class_=FindingClass.INFO,
                    scored=False,
                    evidence={
                        "slug": probe.active.slug,
                        "parent_slug": probe.active.parent_slug,
                        "version": probe.active.version,
                    },
                )
            )

        findings.extend(
            _analyze_theme_version(
                version_target,
                profile,
                user_agent=user_agent,
                client=client,
                label_prefix="Parent theme" if probe.active.is_child_theme and probe.parent else "Theme",
            )
        )

        if not probe.active.is_child_theme:
            entry = _theme_watchlist_entry(profile, probe.active.slug)
            if entry and entry.tier in {"high", "critical", "medium"}:
                findings.append(
                    Finding.from_check(
                        category="THEME_VERIFY",
                        item=probe.active.slug,
                        status="UPDATE_TRAP_RISK",
                        severity=Severity.MEDIUM,
                        detail=(
                            f"Popular premium parent theme {probe.active.name or probe.active.slug} "
                            "used directly with no child theme — sites often freeze updates to preserve custom edits"
                        ),
                        class_=FindingClass.VERIFY,
                        scored=False,
                        evidence={"slug": probe.active.slug, "tier": entry.tier},
                    )
                )

        if _admin_reachable(path_probes):
            findings.append(
                Finding.from_check(
                    category="THEME_VERIFY",
                    item="wp-config hardening",
                    status="EDITOR_UNVERIFIABLE",
                    severity=Severity.MEDIUM,
                    detail=(
                        "Cannot confirm DISALLOW_FILE_EDIT from outside; wp-admin or wp-login is reachable. "
                        "Ask your host or developer to disable the theme/plugin file editor in production "
                        "(define('DISALLOW_FILE_EDIT', true) in wp-config.php)"
                    ),
                    class_=FindingClass.VERIFY,
                    scored=False,
                    evidence={"admin_reachable": True},
                )
            )
    finally:
        if own_client and client is not None:
            client.close()

    return findings


def _analyze_theme_version(
    theme: ObservedTheme,
    profile: FrameworkProfile,
    *,
    user_agent: str,
    client: Any | None,
    label_prefix: str,
) -> list[Finding]:
    slug = theme.slug
    entry = _theme_watchlist_entry(profile, slug)
    detected_raw = theme.version
    detected = _parse_version(detected_raw)

    latest_raw: str | None = None
    if profile.compare.wporg_api and client is not None:
        if not entry or entry.compare_latest:
            latest_raw = fetch_wporg_theme_version(slug, client=client, user_agent=user_agent)

    name = theme.name or slug

    if _is_premium_theme(entry, latest_raw):
        return [
            Finding.from_check(
                category="THEME_VERIFY",
                item=slug,
                status="PREMIUM_OR_UNVERIFIABLE",
                severity=Severity.INFO,
                detail=(
                    f"{label_prefix} {name}"
                    + (f" v{detected_raw}" if detected_raw else "")
                    + " — cannot verify latest via wordpress.org (premium or custom theme)"
                ),
                class_=FindingClass.VERIFY,
                scored=False,
                evidence={"slug": slug, "version": detected_raw, "tier": entry.tier if entry else None},
            )
        ]

    if latest_raw is None:
        return [
            Finding.from_check(
                category="THEME_VERIFY",
                item=slug,
                status="UNKNOWN_SLUG",
                severity=Severity.INFO,
                detail=(
                    f"{label_prefix} {name}"
                    + (f" v{detected_raw}" if detected_raw else "")
                    + " — not listed on wordpress.org; verify maintenance manually"
                ),
                class_=FindingClass.VERIFY,
                scored=False,
                evidence={"slug": slug, "version": detected_raw},
            )
        ]

    if not detected:
        return [
            Finding.from_check(
                category="THEME_VERIFY",
                item=slug,
                status="NO_VERSION",
                severity=Severity.INFO,
                detail=f"{label_prefix} {name} detected but no parseable version in style.css — verify updates manually",
                class_=FindingClass.VERIFY,
                scored=False,
                evidence={"slug": slug, "latest_wporg": latest_raw},
            )
        ]

    latest = _parse_version(latest_raw)
    if latest is None:
        return []

    if detected >= latest:
        return [
            Finding.from_check(
                category="THEME_INFO",
                item=slug,
                status="CURRENT",
                severity=Severity.INFO,
                detail=f"{label_prefix} {name} {detected_raw} matches or exceeds wp.org latest ({latest_raw})",
                class_=FindingClass.INFO,
                scored=False,
                evidence={"slug": slug, "version": detected_raw, "latest_wporg": latest_raw},
            )
        ]

    severity = _severity_for_theme_gap(detected, latest)
    return [
        Finding.from_check(
            category="THEME",
            item=slug,
            status="STALE",
            severity=severity,
            detail=f"{label_prefix} {name} {detected_raw} is behind wordpress.org latest {latest_raw}",
            class_=FindingClass.ACTION,
            scored=True,
            evidence={
                "slug": slug,
                "version": detected_raw,
                "latest_wporg": latest_raw,
                "tier": entry.tier if entry else "observed",
            },
        )
    ]
