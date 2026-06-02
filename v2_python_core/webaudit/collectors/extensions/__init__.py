"""Framework extension collector — dispatches by detected stack."""

from __future__ import annotations

from typing import Any

from webaudit.collectors.extensions.django import collect_django_extensions
from webaudit.collectors.extensions.laravel import collect_laravel_extensions
from webaudit.collectors.extensions.models import ExtensionsProbeResult
from webaudit.collectors.extensions.php import collect_php_extensions
from webaudit.collectors.extensions.rails import collect_rails_extensions
from webaudit.collectors.extensions.wordpress import collect_wordpress_extensions
from webaudit.profiles.loader import FrameworkProfile, load_framework_profile

_SUPPORTED = frozenset({"wordpress", "django", "laravel", "rails", "php"})


def collect_extensions(
    target_url: str,
    framework: str,
    html: str,
    *,
    headers: dict[str, str] | None = None,
    user_agent: str = "WebAudit/2.0",
    timeout_seconds: int = 15,
    client: Any | None = None,
    profile: FrameworkProfile | None = None,
) -> ExtensionsProbeResult:
    """Collect extensions/packages/gems for the active framework profile."""
    effective = framework if framework in _SUPPORTED else "php"
    loaded = profile or load_framework_profile(effective)
    if loaded is None:
        return ExtensionsProbeResult(
            target_url=target_url,
            framework=effective,
            error=f"no profile for framework: {effective}",
        )

    header_map = headers or {}

    if effective == "wordpress":
        return collect_wordpress_extensions(
            target_url,
            html,
            loaded,
            user_agent=user_agent,
            timeout_seconds=timeout_seconds,
            client=client,
        )
    if effective == "django":
        return collect_django_extensions(target_url, html, loaded, headers=header_map)
    if effective == "laravel":
        return collect_laravel_extensions(target_url, html, loaded, headers=header_map)
    if effective == "rails":
        return collect_rails_extensions(target_url, html, loaded, headers=header_map)
    return collect_php_extensions(target_url, html, loaded, headers=header_map)
