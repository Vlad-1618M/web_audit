"""Rails extension fingerprint — passive version + asset signals."""

from __future__ import annotations

import re

from webaudit.collectors.extensions.models import ExtensionSignal, ExtensionsProbeResult, ObservedExtension
from webaudit.profiles.loader import FrameworkProfile

_RAILS_VERSION_RE = re.compile(
    r"rails[^\d]{0,20}(\d+\.\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_RAILS_META_RE = re.compile(r'name="csrf-(?:param|token)"', re.IGNORECASE)
_SPROCKETS_RE = re.compile(r"/assets/(?:application|manifest)-", re.IGNORECASE)


def collect_rails_extensions(
    target_url: str,
    html: str,
    profile: FrameworkProfile,
    *,
    headers: dict[str, str] | None = None,
) -> ExtensionsProbeResult:
    header_map = headers or {}
    result = ExtensionsProbeResult(
        target_url=target_url,
        framework="rails",
        unit="gem",
        mode=profile.probe.mode,
    )

    match = _RAILS_VERSION_RE.search(html)
    if match:
        result.extensions.append(
            ObservedExtension(name="rails", version=match.group(1), source="html", unit="gem")
        )

    for entry in profile.watchlist:
        name = entry.name
        if name == "rails" and result.extensions:
            continue
        pattern = re.compile(rf"\b{re.escape(name)}\b[^\d]{{0,20}}(\d+\.\d+(?:\.\d+)?)", re.I)
        gem_match = pattern.search(html)
        if gem_match:
            result.extensions.append(
                ObservedExtension(name=name, version=gem_match.group(1), source="html", unit="gem")
            )

    signal_map = profile.signals or {}
    if _RAILS_META_RE.search(html) or _SPROCKETS_RE.search(html):
        result.signals.append(
            ExtensionSignal(
                key="rails_assets",
                status="OBSERVED",
                detail="Rails CSRF meta tags or sprockets asset paths observed",
                severity=signal_map.get("rails_assets", "INFO"),
            )
        )

    powered = header_map.get("X-Powered-By", header_map.get("x-powered-by", ""))
    if powered:
        result.signals.append(
            ExtensionSignal(
                key="x_powered_by",
                status="DISCLOSED",
                detail=f"X-Powered-By: {powered[:120]}",
                severity=signal_map.get("x_powered_by", "LOW"),
            )
        )

    return result
