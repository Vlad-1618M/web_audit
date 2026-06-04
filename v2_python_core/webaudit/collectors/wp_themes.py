"""WordPress theme collector — active slug from HTML + style.css header parse.

What: ``collect_wp_themes()`` fingerprints the active theme and optional parent.
Where: ``pipeline._step_extensions`` when framework is WordPress.
How: Regex on ``/wp-content/themes/<slug>/``; GET ``style.css`` for Version/Template.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from webaudit.profiles.loader import FrameworkProfile

_THEME_PATH_RE = re.compile(r"(?:https?://[^/\"'<>]+)?/wp-content/themes/([a-z0-9_-]+)/[^\s\"'<>]*", re.IGNORECASE,)
_STYLE_HEADER_RE = re.compile(r"^\s*(Theme Name|Version|Template|Author|Author URI|Text Domain|Status):\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE,)
_README_HTML_RE = re.compile(r"<!doctype\s+html|<html[\s>]", re.I)


@dataclass
class ObservedTheme:
    slug: str
    name: str = ""
    version: str | None = None
    parent_slug: str | None = None
    author: str = ""
    is_child_theme: bool = False
    source: str = "style.css"

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "version": self.version,
            "parent_slug": self.parent_slug,
            "author": self.author,
            "is_child_theme": self.is_child_theme,
            "source": self.source,
        }


@dataclass
class WpThemesProbeResult:
    target_url: str
    active: ObservedTheme | None = None
    parent: ObservedTheme | None = None
    error: str | None = None

    def to_artifact(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "active": self.active.to_dict() if self.active else None,
            "parent": self.parent.to_dict() if self.parent else None,
            "theme_count": 1 if self.active else 0,
            "error": self.error,
        }


def extract_theme_slug_from_html(html: str) -> str | None:
    """Return the most frequently referenced theme slug in HTML asset paths."""
    counts: dict[str, int] = {}
    for match in _THEME_PATH_RE.finditer(html):
        slug = match.group(1).lower()
        counts[slug] = counts.get(slug, 0) + 1
    if not counts:
        return None
    return max(counts, key=lambda slug: counts[slug])


def parse_style_css_header(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in _STYLE_HEADER_RE.finditer(body[:8000]):
        key = match.group(1).strip().lower().replace(" ", "_")
        fields[key] = match.group(2).strip()
    return fields


def _fetch_style_css(
    base_url: str,
    slug: str,
    *,
    user_agent: str,
    timeout_seconds: int,
    client: Any,
) -> tuple[str | None, str | None]:
    url = f"{base_url.rstrip('/')}/wp-content/themes/{slug}/style.css"
    headers = {"User-Agent": user_agent}
    try:
        response = client.get(url, headers=headers)
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}"
        body = response.text
        if _README_HTML_RE.search(body[:500]):
            return None, "soft-404 HTML"
        return body, None
    except Exception as exc:
        return None, str(exc)


def _theme_from_style(slug: str, body: str) -> ObservedTheme:
    fields = parse_style_css_header(body)
    parent = fields.get("template", "").strip().lower() or None
    return ObservedTheme(
        slug=slug,
        name=fields.get("theme_name", slug),
        version=fields.get("version") or None,
        parent_slug=parent,
        author=fields.get("author", ""),
        is_child_theme=bool(parent),
        source="style.css",
    )


def collect_wp_themes(
    target_url: str,
    html: str,
    profile: FrameworkProfile,
    *,
    user_agent: str,
    timeout_seconds: int,
    client: Any | None = None,
) -> WpThemesProbeResult:
    """Collect active WordPress theme metadata from public HTML + style.css."""
    import httpx

    result = WpThemesProbeResult(target_url=target_url)
    slug = extract_theme_slug_from_html(html)
    if not slug:
        return result

    slug = profile.normalize_slug(slug)
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    try:
        body, err = _fetch_style_css(
            target_url,
            slug,
            user_agent=user_agent,
            timeout_seconds=timeout_seconds,
            client=client,
        )
        if not body:
            result.active = ObservedTheme(slug=slug, name=slug, source="html-only")
            if err:
                result.error = f"style.css fetch failed for {slug}: {err}"
            return result

        active = _theme_from_style(slug, body)
        result.active = active

        if active.is_child_theme and active.parent_slug:
            parent_slug = profile.normalize_slug(active.parent_slug)
            parent_body, parent_err = _fetch_style_css(
                target_url,
                parent_slug,
                user_agent=user_agent,
                timeout_seconds=timeout_seconds,
                client=client,
            )
            if parent_body:
                result.parent = _theme_from_style(parent_slug, parent_body)
            elif parent_err:
                result.parent = ObservedTheme(slug=parent_slug, name=parent_slug, source="html-only")

        return result
    finally:
        if own_client and client is not None:
            client.close()
