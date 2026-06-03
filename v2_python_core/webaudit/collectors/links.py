"""Broken link sampler — HEAD probes on internal URLs from HTML inventory (Tier 2).

What: ``collect_link_probes()`` samples same-origin links and records HTTP status.
Where: ``pipeline._step_links`` when ``collectors.seo_surface.check_broken_links``.
How: Uses ``site_links`` from HTML artifact; capped sample size from config.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from webaudit.collectors.url_utils import same_origin


@dataclass
class LinkProbeEntry:
    url: str
    status_code: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "status_code": self.status_code,
            "error": self.error,
        }


@dataclass
class LinkProbeResult:
    target_url: str
    sampled: int = 0
    probes: list[LinkProbeEntry] = field(default_factory=list)

    def to_artifact(self) -> dict[str, Any]:
        broken = [p for p in self.probes if _is_broken(p)]
        return {
            "target_url": self.target_url,
            "sampled": self.sampled,
            "probes": [p.to_dict() for p in self.probes],
            "broken_count": len(broken),
            "broken_urls": [p.url for p in broken[:20]],
        }


def _is_broken(entry: LinkProbeEntry) -> bool:
    if entry.error:
        return True
    if entry.status_code is None:
        return True
    return entry.status_code >= 400


def _sample_internal_urls(
    target_url: str,
    site_links: list[dict[str, str]],
    *,
    max_sample: int,
) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for item in site_links:
        url = (item.get("url") or "").strip()
        if not url or url in seen:
            continue
        if not same_origin(target_url, url):
            continue
        seen.add(url)
        urls.append(url)
        if len(urls) >= max_sample:
            break
    return urls


def collect_link_probes(
    target_url: str,
    site_links: list[dict[str, str]],
    *,
    max_sample: int,
    user_agent: str,
    timeout_seconds: int,
    client: Any | None = None,
) -> LinkProbeResult:
    import httpx

    urls = _sample_internal_urls(target_url, site_links, max_sample=max_sample)
    result = LinkProbeResult(target_url=target_url, sampled=len(urls))
    if not urls:
        return result

    headers = {"User-Agent": user_agent}
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    try:
        for url in urls:
            entry = LinkProbeEntry(url=url)
            try:
                response = client.head(url, headers=headers)
                if response.status_code in {405, 501}:
                    response = client.get(url, headers=headers)
                entry.status_code = response.status_code
            except httpx.HTTPError as exc:
                entry.error = str(exc)
            result.probes.append(entry)
        return result
    finally:
        if own_client:
            client.close()
