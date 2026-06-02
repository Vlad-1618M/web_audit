"""WordPress extension fingerprint — HTML assets + optional readme.txt."""

from __future__ import annotations

from typing import Any

from webaudit.collectors.extensions.models import ExtensionsProbeResult, ObservedExtension
from webaudit.collectors.wp_plugins import collect_wp_plugins
from webaudit.profiles.loader import FrameworkProfile


def collect_wordpress_extensions(
    target_url: str,
    html: str,
    profile: FrameworkProfile,
    *,
    user_agent: str,
    timeout_seconds: int,
    client: Any | None = None,
) -> ExtensionsProbeResult:
    wp_probe = collect_wp_plugins(
        target_url,
        html,
        profile,
        user_agent=user_agent,
        timeout_seconds=timeout_seconds,
        client=client,
    )
    result = ExtensionsProbeResult(
        target_url=target_url,
        framework="wordpress",
        unit="plugin",
        mode=wp_probe.mode,
        error=wp_probe.error,
    )
    for plugin in wp_probe.plugins:
        result.extensions.append(
            ObservedExtension(
                name=plugin.slug,
                version=plugin.best_version(),
                source=plugin.source,
                unit="plugin",
            )
        )
    return result
