"""Sitemap URL collection — parse indexes and nested child sitemaps (WordPress parity)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

_LOC_RE = re.compile(r"<loc[^>]*>([^<]+)</loc>", re.IGNORECASE)


def parse_sitemap_locs(body: str, *, limit: int = 500) -> list[str]:
    if not body:
        return []
    urls = [match.group(1).strip() for match in _LOC_RE.finditer(body)]
    return urls[:limit]


def _looks_like_sitemap_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(".xml") or "sitemap" in path


def _is_sitemap_index_body(body: str, locs: list[str]) -> bool:
    lower = body.lower()
    if "sitemapindex" in lower:
        return True
    if locs and all(_looks_like_sitemap_url(loc) for loc in locs):
        return True
    return False


def collect_sitemap_urls(
    target_url: str,
    root_body: str,
    *,
    user_agent: str,
    timeout_seconds: int,
    max_urls: int = 500,
    max_child_sitemaps: int = 12,
    max_sitemap_bytes: int = 16_000,
    client: Any | None = None,
) -> tuple[list[str], int]:
    """Return page URLs from sitemap.xml, following sitemap index children when needed."""
    import httpx

    root_locs = parse_sitemap_locs(root_body, limit=max_urls)
    if not root_locs:
        return [], 0

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    headers = {"User-Agent": user_agent}
    collected: list[str] = []
    seen_sitemaps: set[str] = set()
    child_count = 0

    def _fetch_sitemap(url: str) -> str:
        nonlocal child_count
        if url in seen_sitemaps or child_count >= max_child_sitemaps:
            return ""
        seen_sitemaps.add(url)
        child_count += 1
        try:
            response = client.get(url, headers=headers)
            if response.status_code != 200:
                return ""
            return response.text[:max_sitemap_bytes]
        except httpx.HTTPError:
            return ""

    try:
        if _is_sitemap_index_body(root_body, root_locs):
            for child_url in root_locs:
                if len(collected) >= max_urls:
                    break
                child_body = _fetch_sitemap(child_url)
                if not child_body:
                    continue
                for loc in parse_sitemap_locs(child_body, limit=max_urls - len(collected)):
                    if not _looks_like_sitemap_url(loc):
                        collected.append(loc)
                    elif len(collected) < max_urls:
                        nested_body = _fetch_sitemap(loc)
                        for nested_loc in parse_sitemap_locs(nested_body, limit=max_urls - len(collected)):
                            if not _looks_like_sitemap_url(nested_loc):
                                collected.append(nested_loc)
        else:
            for loc in root_locs:
                if _looks_like_sitemap_url(loc):
                    child_body = _fetch_sitemap(loc)
                    collected.extend(
                        url
                        for url in parse_sitemap_locs(child_body, limit=max_urls - len(collected))
                        if not _looks_like_sitemap_url(url)
                    )
                else:
                    collected.append(loc)
                if len(collected) >= max_urls:
                    break
    finally:
        if own_client:
            client.close()

    # Deduplicate while preserving order
    unique: list[str] = []
    seen_pages: set[str] = set()
    for url in collected:
        if url not in seen_pages:
            seen_pages.add(url)
            unique.append(url)
    return unique[:max_urls], child_count
