"""WordPress plugin analyzer — wp.org version compare and premium VERIFY signals.

What: ``analyze_wp_plugins()`` compares observed versions to wordpress.org latest.
Where: ``pipeline._step_wp_plugins`` after ``collect_wp_plugins()``.
How: Free plugins on wp.org → ACTION when behind; premium/custom → PLUGIN_VERIFY.
"""

from __future__ import annotations

import re
from typing import Any

from packaging.version import InvalidVersion, Version

from webaudit.collectors.wp_plugins import ObservedPlugin, WpPluginsProbeResult
from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.profiles.loader import FrameworkProfile, WatchlistEntry

_WPORG_API = "https://api.wordpress.org/plugins/info/1.0/{slug}.json"

# Slugs where ?ver= on assets is often an internal build number, not plugin semver.
_ASSET_VER_UNRELIABLE = frozenset({"elementor", "elementor-pro"})


def _infer_premium_slug(slug: str, entry: WatchlistEntry | None) -> bool:
    if entry and entry.premium:
        return True
    if entry and not entry.compare_latest:
        return True
    lowered = slug.lower()
    if lowered.endswith("-pro") or lowered.endswith("-premium"):
        return True
    if "premium" in lowered or lowered.endswith("-pro-lite"):
        return True
    return lowered in {
        "object-cache-pro",
        "wp-rocket",
        "gravityforms",
        "advanced-custom-fields-pro",
    }


def _version_looks_like_asset_noise(detected: Version, latest: Version) -> bool:
    """HTML ?ver= can exceed wp.org semver (e.g. Elementor asset build ids)."""
    if detected.major >= latest.major + 2:
        return True
    if detected.major == latest.major + 1 and detected.minor > latest.minor + 2:
        return True
    return False


def _severity_for_gap(detected: Version, latest: Version) -> Severity:
    if detected.major < latest.major:
        return Severity.HIGH
    if detected.minor < latest.minor:
        return Severity.MEDIUM
    if detected.micro < latest.micro:
        return Severity.LOW
    return Severity.INFO


def _parse_version(raw: str | None) -> Version | None:
    if not raw:
        return None
    cleaned = raw.strip()
    cleaned = re.sub(r"[^0-9.a-zA-Z-]", "", cleaned)
    if not cleaned or cleaned.lower() in {"trunk", "beta", "dev"}:
        return None
    try:
        return Version(cleaned)
    except InvalidVersion:
        return None


def fetch_wporg_latest_version(
    slug: str,
    *,
    client: Any,
    user_agent: str,
) -> str | None:
    url = _WPORG_API.format(slug=slug)
    headers = {"User-Agent": user_agent}
    try:
        response = client.get(url, headers=headers)
        if response.status_code != 200:
            return None
        data = response.json()
        version = data.get("version")
        return str(version) if version else None
    except Exception:
        return None


def _watchlist_entry(profile: FrameworkProfile, slug: str) -> WatchlistEntry | None:
    return profile.watchlist_map().get(slug)


def _is_premium(entry: WatchlistEntry | None, slug: str, latest: str | None) -> bool:
    if _infer_premium_slug(slug, entry):
        return True
    return latest is None and entry is not None and entry.tier in {"high", "critical"}


def analyze_wp_plugins(
    probe: WpPluginsProbeResult,
    profile: FrameworkProfile,
    *,
    user_agent: str,
    timeout_seconds: int,
    client: Any | None = None,
) -> list[Finding]:
    if probe.error:
        return [
            Finding.from_check(
                category="PLUGIN",
                item="Plugin probe",
                status="ERROR",
                severity=Severity.INFO,
                detail=probe.error,
                class_=FindingClass.INFO,
                scored=False,
            )
        ]

    if not probe.plugins:
        return [
            Finding.from_check(
                category="PLUGIN_INFO",
                item="WordPress plugins",
                status="NONE_OBSERVED",
                severity=Severity.INFO,
                detail="No plugin slugs observed in HTML asset URLs",
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
        for plugin in probe.plugins:
            findings.extend(
                _analyze_one_plugin(
                    plugin,
                    profile,
                    user_agent=user_agent,
                    client=client,
                )
            )
    finally:
        if own_client and client is not None:
            client.close()

    return findings


def _analyze_one_plugin(
    plugin: ObservedPlugin,
    profile: FrameworkProfile,
    *,
    user_agent: str,
    client: Any | None,
) -> list[Finding]:
    slug = plugin.slug
    entry = _watchlist_entry(profile, slug)
    detected_raw = plugin.best_version()
    detected = _parse_version(detected_raw)

    latest_raw: str | None = None
    wporg_slug = plugin.readme_slug()
    if profile.compare.wporg_api and client is not None:
        if not entry or entry.compare_latest:
            if not _infer_premium_slug(slug, entry):
                latest_raw = fetch_wporg_latest_version(
                    wporg_slug, client=client, user_agent=user_agent
                )
                if latest_raw is None and wporg_slug != slug:
                    latest_raw = fetch_wporg_latest_version(
                        slug, client=client, user_agent=user_agent
                    )

    if _is_premium(entry, slug, latest_raw):
        return [
            Finding.from_check(
                category="PLUGIN_VERIFY",
                item=slug,
                status="PREMIUM_OR_UNVERIFIABLE",
                severity=Severity.INFO,
                detail=(
                    f"Detected {slug}"
                    + (f" v{detected_raw}" if detected_raw else "")
                    + " — premium or vendor-hosted; verify updates in wp-admin or the vendor portal"
                ),
                class_=FindingClass.VERIFY,
                scored=False,
                evidence={"slug": slug, "version": detected_raw, "tier": entry.tier if entry else None},
            )
        ]

    if latest_raw is None:
        return [
            Finding.from_check(
                category="PLUGIN_VERIFY",
                item=slug,
                status="UNKNOWN_SLUG",
                severity=Severity.INFO,
                detail=(
                    f"Detected {slug}"
                    + (f" v{detected_raw}" if detected_raw else "")
                    + " — not on wordpress.org (may be custom or admin-only); verify manually"
                ),
                class_=FindingClass.VERIFY,
                scored=False,
                evidence={"slug": slug, "version": detected_raw},
            )
        ]

    latest = _parse_version(latest_raw)
    if detected and latest and _version_looks_like_asset_noise(detected, latest):
        if plugin.version_readme:
            detected_raw = plugin.version_readme
            detected = _parse_version(detected_raw)
        elif slug in _ASSET_VER_UNRELIABLE or plugin.version_html:
            return [
                Finding.from_check(
                    category="PLUGIN_VERIFY",
                    item=slug,
                    status="VERSION_UNVERIFIED",
                    severity=Severity.INFO,
                    detail=(
                        f"Detected {slug} from public assets"
                        + (f" (?ver={plugin.version_html})" if plugin.version_html else "")
                        + f" — does not match wordpress.org semver ({latest_raw}); "
                        "readme.txt blocked or asset build id — confirm version in wp-admin"
                    ),
                    class_=FindingClass.VERIFY,
                    scored=False,
                    evidence={
                        "slug": slug,
                        "version": plugin.version_html,
                        "latest_wporg": latest_raw,
                        "version_readme": plugin.version_readme,
                    },
                )
            ]
    if not detected:
        return [
            Finding.from_check(
                category="PLUGIN_VERIFY",
                item=slug,
                status="NO_VERSION",
                severity=Severity.INFO,
                detail=f"Detected {slug} but no parseable version string — verify updates manually",
                class_=FindingClass.VERIFY,
                scored=False,
                evidence={"slug": slug, "latest_wporg": latest_raw},
            )
        ]

    if latest is None:
        return []

    if detected >= latest:
        return [
            Finding.from_check(
                category="PLUGIN_INFO",
                item=slug,
                status="CURRENT",
                severity=Severity.INFO,
                detail=f"{slug} {detected_raw} matches or exceeds wp.org latest ({latest_raw})",
                class_=FindingClass.INFO,
                scored=False,
                evidence={"slug": slug, "version": detected_raw, "latest_wporg": latest_raw},
            )
        ]

    severity = _severity_for_gap(detected, latest)
    return [
        Finding.from_check(
            category="PLUGIN",
            item=slug,
            status="STALE",
            severity=severity,
            detail=f"{slug} {detected_raw} is behind wordpress.org latest {latest_raw}",
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
