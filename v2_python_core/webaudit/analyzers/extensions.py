"""Framework extension analyzer — version compare + passive risk signals."""

from __future__ import annotations

from typing import Any

import httpx

from webaudit.analyzers.extension_compare import fetch_latest_version, registry_for_framework
from webaudit.analyzers.wp_plugins import _parse_version, _severity_for_gap
from webaudit.collectors.extensions.models import ExtensionSignal, ExtensionsProbeResult, ObservedExtension
from webaudit.models.finding import Finding, FindingClass, Severity
from webaudit.profiles.loader import FrameworkProfile, WatchlistEntry


def _categories(unit: str) -> tuple[str, str, str]:
    if unit == "package":
        return "PACKAGE", "PACKAGE_VERIFY", "PACKAGE_INFO"
    if unit == "gem":
        return "GEM", "GEM_VERIFY", "GEM_INFO"
    return "PLUGIN", "PLUGIN_VERIFY", "PLUGIN_INFO"


def _severity_from_string(raw: str) -> Severity:
    try:
        return Severity(raw.upper())
    except ValueError:
        return Severity.INFO


def _watchlist_entry(profile: FrameworkProfile, name: str) -> WatchlistEntry | None:
    return profile.watchlist_map().get(name)


def _is_unverifiable(entry: WatchlistEntry | None, latest: str | None) -> bool:
    if entry and entry.premium:
        return True
    if entry and not entry.compare_latest:
        return True
    return latest is None and entry is not None and entry.tier in {"high", "critical"}


def _signal_findings(
    signals: list[ExtensionSignal],
    *,
    unit: str,
    profile: FrameworkProfile,
) -> list[Finding]:
    action_cat, _verify_cat, _info_cat = _categories(unit)
    findings: list[Finding] = []
    for signal in signals:
        severity = _severity_from_string(signal.severity)
        is_action = severity in {Severity.CRITICAL, Severity.HIGH}
        findings.append(
            Finding.from_check(
                category=action_cat if is_action else action_cat.replace("_VERIFY", ""),
                item=signal.key.replace("_", " "),
                status=signal.status,
                severity=severity,
                detail=signal.detail,
                class_=FindingClass.ACTION if is_action else FindingClass.INFO,
                scored=is_action,
                evidence={"signal": signal.key, "framework": profile.framework},
            )
        )
    return findings


def analyze_extensions(
    probe: ExtensionsProbeResult,
    profile: FrameworkProfile,
    *,
    user_agent: str,
    timeout_seconds: int,
    client: Any | None = None,
) -> list[Finding]:
    if probe.error:
        action_cat, _, _ = _categories(probe.unit)
        return [
            Finding.from_check(
                category=action_cat,
                item="Extension probe",
                status="ERROR",
                severity=Severity.INFO,
                detail=probe.error,
                class_=FindingClass.INFO,
                scored=False,
            )
        ]

    findings = _signal_findings(probe.signals, unit=probe.unit, profile=profile)

    registry = registry_for_framework(probe.framework)
    compare_enabled = _compare_enabled(profile, registry)

    own_client = client is None and compare_enabled and registry is not None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    try:
        for extension in probe.extensions:
            findings.extend(
                _analyze_one_extension(
                    extension,
                    profile,
                    registry=registry,
                    compare_enabled=compare_enabled,
                    user_agent=user_agent,
                    client=client,
                )
            )
    finally:
        if own_client and client is not None:
            client.close()

    if not probe.extensions and not probe.signals:
        _, _, info_cat = _categories(probe.unit)
        label = {"plugin": "plugins", "package": "packages", "gem": "gems"}.get(probe.unit, "extensions")
        findings.append(
            Finding.from_check(
                category=info_cat,
                item=f"Framework {label}",
                status="NONE_OBSERVED",
                severity=Severity.INFO,
                detail=f"No {label} or version signals observed in public HTML/headers",
                class_=FindingClass.INFO,
                scored=False,
            )
        )

    return findings


def _compare_enabled(profile: FrameworkProfile, registry: str | None) -> bool:
    if registry == "wporg":
        return profile.compare.wporg_api
    if registry == "pypi":
        return profile.compare.pypi_api
    if registry == "packagist":
        return profile.compare.packagist_api
    if registry == "rubygems":
        return profile.compare.rubygems_api
    return False


def _analyze_one_extension(
    extension: ObservedExtension,
    profile: FrameworkProfile,
    *,
    registry: str | None,
    compare_enabled: bool,
    user_agent: str,
    client: Any | None,
) -> list[Finding]:
    action_cat, verify_cat, info_cat = _categories(extension.unit)
    name = profile.normalize_slug(extension.name)
    entry = _watchlist_entry(profile, name)
    detected_raw = extension.version
    detected = _parse_version(detected_raw)

    latest_raw: str | None = None
    if compare_enabled and registry and client is not None:
        if not entry or entry.compare_latest:
            latest_raw = fetch_latest_version(registry, name, client=client, user_agent=user_agent)

    if _is_unverifiable(entry, latest_raw):
        return [
            Finding.from_check(
                category=verify_cat,
                item=name,
                status="UNVERIFIABLE",
                severity=Severity.INFO,
                detail=(
                    f"Detected {name}"
                    + (f" v{detected_raw}" if detected_raw else "")
                    + f" — cannot verify latest via {registry or 'registry'}"
                ),
                class_=FindingClass.VERIFY,
                scored=False,
                evidence={"name": name, "version": detected_raw, "registry": registry},
            )
        ]

    if latest_raw is None:
        if compare_enabled:
            return [
                Finding.from_check(
                    category=verify_cat,
                    item=name,
                    status="UNKNOWN",
                    severity=Severity.INFO,
                    detail=(
                        f"Detected {name}"
                        + (f" v{detected_raw}" if detected_raw else "")
                        + " — not found in public registry; verify maintenance manually"
                    ),
                    class_=FindingClass.VERIFY,
                    scored=False,
                    evidence={"name": name, "version": detected_raw, "registry": registry},
                )
            ]
        return [
            Finding.from_check(
                category=info_cat,
                item=name,
                status="OBSERVED",
                severity=Severity.INFO,
                detail=f"Observed {name}" + (f" v{detected_raw}" if detected_raw else ""),
                class_=FindingClass.INFO,
                scored=False,
                evidence={"name": name, "version": detected_raw},
            )
        ]

    latest = _parse_version(latest_raw)
    if not detected:
        return [
            Finding.from_check(
                category=verify_cat,
                item=name,
                status="NO_VERSION",
                severity=Severity.INFO,
                detail=f"Detected {name} but no parseable version — verify updates manually",
                class_=FindingClass.VERIFY,
                scored=False,
                evidence={"name": name, "latest": latest_raw, "registry": registry},
            )
        ]

    if latest is None:
        return []

    if detected >= latest:
        return [
            Finding.from_check(
                category=info_cat,
                item=name,
                status="CURRENT",
                severity=Severity.INFO,
                detail=f"{name} {detected_raw} matches or exceeds latest ({latest_raw})",
                class_=FindingClass.INFO,
                scored=False,
                evidence={"name": name, "version": detected_raw, "latest": latest_raw},
            )
        ]

    severity = _severity_for_gap(detected, latest)
    return [
        Finding.from_check(
            category=action_cat,
            item=name,
            status="STALE",
            severity=severity,
            detail=f"{name} {detected_raw} is behind latest {latest_raw}",
            class_=FindingClass.ACTION,
            scored=True,
            evidence={
                "name": name,
                "version": detected_raw,
                "latest": latest_raw,
                "registry": registry,
                "tier": entry.tier if entry else "observed",
            },
        )
    ]
