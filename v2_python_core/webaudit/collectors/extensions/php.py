"""Generic PHP extension fingerprint — version disclosure signals."""

from __future__ import annotations

import re

from webaudit.collectors.extensions.models import ExtensionSignal, ExtensionsProbeResult
from webaudit.profiles.loader import FrameworkProfile

_PHP_VERSION_RE = re.compile(r"php[/\s](\d+\.\d+(?:\.\d+)?)", re.IGNORECASE)


def collect_php_extensions(
    target_url: str,
    html: str,
    profile: FrameworkProfile,
    *,
    headers: dict[str, str] | None = None,
) -> ExtensionsProbeResult:
    header_map = headers or {}
    result = ExtensionsProbeResult(
        target_url=target_url,
        framework="php",
        unit="runtime",
        mode=profile.probe.mode,
    )
    signal_map = profile.signals or {}

    server = header_map.get("Server", header_map.get("server", ""))
    if server:
        match = _PHP_VERSION_RE.search(server)
        if match:
            result.signals.append(
                ExtensionSignal(
                    key="server_version_header",
                    status="DISCLOSED",
                    detail=f"Server header discloses PHP {match.group(1)}",
                    severity=signal_map.get("server_version_header", "LOW"),
                )
            )

    powered = header_map.get("X-Powered-By", header_map.get("x-powered-by", ""))
    if powered:
        match = _PHP_VERSION_RE.search(powered)
        detail = powered[:120]
        if match:
            detail = f"X-Powered-By discloses PHP {match.group(1)}"
        result.signals.append(
            ExtensionSignal(
                key="x_powered_by",
                status="DISCLOSED",
                detail=detail,
                severity=signal_map.get("x_powered_by", "LOW"),
            )
        )

    if "readme" in html.lower() and re.search(r"php\s+\d+\.\d+", html, re.I):
        result.signals.append(
            ExtensionSignal(
                key="exposed_readme",
                status="REFERENCED",
                detail="README or install notes with PHP version referenced in HTML",
                severity=signal_map.get("exposed_readme", "MEDIUM"),
            )
        )

    return result
