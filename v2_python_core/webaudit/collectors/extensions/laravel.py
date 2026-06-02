"""Laravel extension fingerprint — passive version + debug signals."""

from __future__ import annotations

import re

from webaudit.collectors.extensions.models import ExtensionSignal, ExtensionsProbeResult, ObservedExtension
from webaudit.profiles.loader import FrameworkProfile

_LARAVEL_VERSION_RE = re.compile(
    r"laravel(?: framework)?[^\d]{0,30}(\d+\.\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_VENDOR_PATH_RE = re.compile(r"/vendor/laravel/", re.IGNORECASE)
_WHOOPS_MARKERS = ("whoops\\exception", "whoops, looks like something went wrong", "illuminate\\")
_DEBUG_MARKERS = ("app_debug", "ignition", "laravel_exception")


def collect_laravel_extensions(
    target_url: str,
    html: str,
    profile: FrameworkProfile,
    *,
    headers: dict[str, str] | None = None,
) -> ExtensionsProbeResult:
    header_map = headers or {}
    lower = html.lower()
    result = ExtensionsProbeResult(
        target_url=target_url,
        framework="laravel",
        unit="package",
        mode=profile.probe.mode,
    )

    match = _LARAVEL_VERSION_RE.search(html)
    if match:
        result.extensions.append(
            ObservedExtension(
                name="laravel/framework",
                version=match.group(1),
                source="html",
                unit="package",
            )
        )

    for entry in profile.watchlist:
        name = entry.name
        if name == "laravel/framework" and result.extensions:
            continue
        pattern = re.compile(rf"{re.escape(name)}[^\d]{{0,20}}(\d+\.\d+(?:\.\d+)?)", re.I)
        pkg_match = pattern.search(html)
        if pkg_match:
            result.extensions.append(
                ObservedExtension(name=name, version=pkg_match.group(1), source="html", unit="package")
            )

    signal_map = profile.signals or {}
    if any(marker in lower for marker in _WHOOPS_MARKERS):
        result.signals.append(
            ExtensionSignal(
                key="whoops_page",
                status="EXPOSED",
                detail="Laravel Whoops/Ignition debug page visible on public response",
                severity=signal_map.get("whoops_page", "CRITICAL"),
            )
        )
    elif any(marker in lower for marker in _DEBUG_MARKERS):
        result.signals.append(
            ExtensionSignal(
                key="app_debug",
                status="EXPOSED",
                detail="Laravel debug output or APP_DEBUG indicators in response",
                severity=signal_map.get("app_debug", "CRITICAL"),
            )
        )

    if _VENDOR_PATH_RE.search(html):
        result.signals.append(
            ExtensionSignal(
                key="exposed_vendor",
                status="REFERENCED",
                detail="vendor/laravel path referenced in HTML — verify vendor/ is not web-accessible",
                severity=signal_map.get("exposed_vendor", "HIGH"),
            )
        )

    powered = header_map.get("X-Powered-By", header_map.get("x-powered-by", ""))
    if powered and "php" in powered.lower():
        result.signals.append(
            ExtensionSignal(
                key="x_powered_by",
                status="DISCLOSED",
                detail=f"X-Powered-By: {powered[:120]}",
                severity=signal_map.get("x_powered_by", "LOW"),
            )
        )

    return result
