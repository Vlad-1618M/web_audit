"""WordPress plugin collector — slug/version from HTML assets + optional readme.txt.

What: ``collect_wp_plugins()`` extracts observed plugin slugs from page HTML.
Where: ``pipeline._step_wp_plugins`` when framework is WordPress.
How: Regex on ``/wp-content/plugins/<slug>/`` URLs; readme fetch only for observed slugs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from webaudit.profiles.loader import FrameworkProfile

_PLUGIN_PATH_RE = re.compile(
    r"(?:https?://[^/\"'<>]+)?/wp-content/plugins/([a-z0-9_-]+)/[^\s\"'<>]*",
    re.IGNORECASE,
)
_README_HTML_RE = re.compile(r"<!doctype\s+html|<html[\s>]", re.I)
_VERSION_RE = re.compile(r"[?&](?:ver|version)=([\d.]+(?:\.[\d]+)*)", re.IGNORECASE)
_STABLE_TAG_RE = re.compile(r"^\s*Stable tag:\s*(.+)\s*$", re.MULTILINE | re.IGNORECASE)


@dataclass
class ObservedPlugin:
    slug: str
    version_html: str | None = None
    version_readme: str | None = None
    source: str = "html"

    def best_version(self) -> str | None:
        return self.version_readme or self.version_html

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "version_html": self.version_html,
            "version_readme": self.version_readme,
            "version": self.best_version(),
            "source": self.source,
        }


@dataclass
class WpPluginsProbeResult:
    target_url: str
    plugins: list[ObservedPlugin] = field(default_factory=list)
    mode: str = "observed_only"
    readme_fetch: str = "observed_only"
    error: str | None = None

    def to_artifact(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "mode": self.mode,
            "readme_fetch": self.readme_fetch,
            "plugin_count": len(self.plugins),
            "plugins": [p.to_dict() for p in self.plugins],
            "error": self.error,
        }


def extract_plugins_from_html(html: str) -> dict[str, str | None]:
    """Return slug -> best version seen in HTML asset URLs."""
    by_slug: dict[str, str | None] = {}
    for match in _PLUGIN_PATH_RE.finditer(html):
        slug = match.group(1).lower()
        fragment = match.group(0)
        ver_match = _VERSION_RE.search(fragment)
        version = ver_match.group(1) if ver_match else None
        existing = by_slug.get(slug)
        if slug not in by_slug:
            by_slug[slug] = version
        elif version and (not existing or _version_tuple(version) > _version_tuple(existing)):
            by_slug[slug] = version
    return by_slug


def _version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in version.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts or [0])


def _parse_readme_stable_tag(body: str) -> str | None:
    if not body.strip() or _README_HTML_RE.search(body[:500]):
        return None
    match = _STABLE_TAG_RE.search(body)
    if not match:
        return None
    tag = match.group(1).strip()
    if tag.lower() in {"trunk", "stable tag", "n/a"}:
        return None
    return tag


def _fetch_readme_version(
    base_url: str,
    slug: str,
    *,
    user_agent: str,
    timeout_seconds: int,
    client: Any,
) -> str | None:
    url = f"{base_url.rstrip('/')}/wp-content/plugins/{slug}/readme.txt"
    headers = {"User-Agent": user_agent}
    try:
        response = client.get(url, headers=headers)
        if response.status_code != 200:
            return None
        return _parse_readme_stable_tag(response.text)
    except Exception:
        return None


def collect_wp_plugins(
    target_url: str,
    html: str,
    profile: FrameworkProfile,
    *,
    user_agent: str,
    timeout_seconds: int,
    client: Any | None = None,
) -> WpPluginsProbeResult:
    """Collect WordPress plugins observed in HTML (and optional readme.txt)."""
    import httpx

    result = WpPluginsProbeResult(
        target_url=target_url,
        mode=profile.probe.mode,
        readme_fetch=profile.probe.readme_fetch,
    )

    if profile.probe.mode != "observed_only":
        result.error = f"unsupported probe mode: {profile.probe.mode}"
        return result

    observed = extract_plugins_from_html(html)
    for slug, version in sorted(observed.items()):
        normalized = profile.normalize_slug(slug)
        result.plugins.append(
            ObservedPlugin(slug=normalized, version_html=version, source="html")
        )

    if profile.probe.readme_fetch != "observed_only" or not result.plugins:
        return result

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    try:
        for plugin in result.plugins:
            readme_ver = _fetch_readme_version(
                target_url,
                plugin.slug,
                user_agent=user_agent,
                timeout_seconds=timeout_seconds,
                client=client,
            )
            if readme_ver:
                plugin.version_readme = readme_ver
                plugin.source = "html+readme"
    finally:
        if own_client:
            client.close()

    return result
