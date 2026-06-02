"""Django extension fingerprint — passive version + debug signals."""

from __future__ import annotations

import re

from webaudit.collectors.extensions.models import ExtensionSignal, ExtensionsProbeResult, ObservedExtension
from webaudit.profiles.loader import FrameworkProfile

_DJANGO_VERSION_RE = re.compile(
    r"django(?:\.[\w-]+)?[^\d]{0,40}(\d+\.\d+(?:\.\d+)?(?:[a-z0-9]+)?)",
    re.IGNORECASE,
)
_ADMIN_STATIC_RE = re.compile(r"/static/admin/(?:css|js)/", re.IGNORECASE)
_DEBUG_MARKERS = (
    "you're seeing this error because you have debug = true",
    "django.core.exceptions",
    "settings.py",
    "traceback (most recent call last)",
)
_ALLOWED_HOSTS_MARKER = "invalid http_host header"


def _extract_django_version(html: str, headers: dict[str, str]) -> str | None:
    blob = html
    for value in headers.values():
        blob += f"\n{value}"
    match = _DJANGO_VERSION_RE.search(blob)
    if match:
        return match.group(1)
    if re.search(r"csrfmiddlewaretoken", html, re.IGNORECASE) and _ADMIN_STATIC_RE.search(html):
        return None
    return None


def _detect_signals(html: str, headers: dict[str, str], profile: FrameworkProfile) -> list[ExtensionSignal]:
    lower = html.lower()
    blob = lower + "\n" + _header_blob(headers).lower()
    signals: list[ExtensionSignal] = []
    signal_map = profile.signals or {}

    if any(marker in lower for marker in _DEBUG_MARKERS):
        signals.append(
            ExtensionSignal(
                key="debug_page",
                status="EXPOSED",
                detail="Django DEBUG error page or traceback visible on public response",
                severity=signal_map.get("debug_page", "CRITICAL"),
            )
        )

    if _ALLOWED_HOSTS_MARKER in lower:
        signals.append(
            ExtensionSignal(
                key="allowed_hosts_leak",
                status="LEAKING",
                detail="DisallowedHost or ALLOWED_HOSTS misconfiguration leak in response",
                severity=signal_map.get("allowed_hosts_leak", "HIGH"),
            )
        )

    if _ADMIN_STATIC_RE.search(html):
        signals.append(
            ExtensionSignal(
                key="admin_static",
                status="OBSERVED",
                detail="Django admin static assets referenced in HTML",
                severity=signal_map.get("admin_static", "INFO"),
            )
        )

    powered = headers.get("X-Powered-By", headers.get("x-powered-by", ""))
    if powered and "django" in powered.lower():
        signals.append(
            ExtensionSignal(
                key="x_powered_by",
                status="DISCLOSED",
                detail=f"X-Powered-By discloses Django: {powered[:120]}",
                severity=signal_map.get("x_powered_by", "LOW"),
            )
        )

    if "exposed_requirements_txt" in signal_map and "requirements.txt" in blob:
        signals.append(
            ExtensionSignal(
                key="exposed_requirements_txt",
                status="REFERENCED",
                detail="requirements.txt referenced in public HTML — verify not openly served",
                severity=signal_map.get("exposed_requirements_txt", "MEDIUM"),
            )
        )

    return signals


def _header_blob(headers: dict[str, str]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in headers.items())


def collect_django_extensions(
    target_url: str,
    html: str,
    profile: FrameworkProfile,
    *,
    headers: dict[str, str] | None = None,
) -> ExtensionsProbeResult:
    header_map = headers or {}
    result = ExtensionsProbeResult(
        target_url=target_url,
        framework="django",
        unit="package",
        mode=profile.probe.mode,
    )

    version = _extract_django_version(html, header_map)
    if version:
        result.extensions.append(
            ObservedExtension(name="django", version=version, source="html", unit="package")
        )

    for entry in profile.watchlist:
        name = entry.name
        if name == "django" and version:
            continue
        pattern = re.compile(rf"\b{re.escape(name.replace('-', '[-_]'))}\b[^\d]{{0,20}}(\d+\.\d+(?:\.\d+)?)", re.I)
        match = pattern.search(html)
        if match:
            result.extensions.append(
                ObservedExtension(name=name, version=match.group(1), source="html", unit="package")
            )

    result.signals = _detect_signals(html, header_map, profile)
    return result
