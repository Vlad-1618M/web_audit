"""Site discovery — merge homepage, sitemap, and sampled page links."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from webaudit.collectors.html import HtmlInventory, parse_html_inventory
from webaudit.collectors.url_utils import same_origin


def merge_site_link(
    inventory: HtmlInventory,
    *,
    url: str,
    kind: str,
    source: str,
    seen: set[str],
    max_site_links: int,
) -> bool:
    if url in seen or len(inventory.site_links) >= max_site_links:
        return False
    seen.add(url)
    inventory.site_links.append({"url": url, "kind": kind, "source": source})
    if kind == "internal":
        inventory.internal_link_count += 1
    elif kind == "external":
        inventory.external_link_count += 1
    return True


def merge_inventories(
    base: HtmlInventory,
    extra: HtmlInventory,
    *,
    target_url: str,
    source: str,
    seen: set[str],
    max_site_links: int,
    max_images: int,
) -> None:
    base.link_count += extra.link_count
    base.image_count += extra.image_count
    base.form_count += extra.form_count
    base.mixed_content_count += extra.mixed_content_count
    base.mixed_content_samples.extend(extra.mixed_content_samples[:10])
    base.insecure_form_actions.extend(extra.insecure_form_actions)

    for href in extra.internal_links_sample:
        if len(base.internal_links_sample) < 500:
            base.internal_links_sample.append(href)

    for item in extra.site_links:
        merge_site_link(
            base,
            url=item["url"],
            kind=item["kind"],
            source=source,
            seen=seen,
            max_site_links=max_site_links,
        )

    image_seen = {img["url"] for img in base.images}
    for item in extra.images:
        if item["url"] in image_seen or len(base.images) >= max_images:
            continue
        image_seen.add(item["url"])
        base.images.append(item)


def enrich_site_inventory(
    inventory: HtmlInventory,
    *,
    target_url: str,
    sitemap_urls: list[str],
    user_agent: str,
    timeout_seconds: int,
    max_sample_pages: int,
    max_body_bytes: int,
    max_site_links: int,
    max_images: int,
    check_mixed_content: bool,
    check_forms: bool,
    client: Any | None = None,
) -> tuple[int, int]:
    """Add sitemap URLs and sample additional pages; returns (pages_sampled, sitemap_url_count)."""
    import httpx

    seen = {item["url"] for item in inventory.site_links}
    for url in sitemap_urls:
        kind = "internal" if same_origin(target_url, url) else "external"
        merge_site_link(
            inventory,
            url=url,
            kind=kind,
            source="sitemap",
            seen=seen,
            max_site_links=max_site_links,
        )

    sample_urls: list[str] = []
    sample_seen: set[str] = set()
    for candidate in [target_url, *sitemap_urls]:
        if candidate in sample_seen:
            continue
        if not same_origin(target_url, candidate):
            continue
        if _looks_like_sitemap_url(candidate):
            continue
        sample_seen.add(candidate)
        sample_urls.append(candidate)
        if len(sample_urls) >= max_sample_pages:
            break

    own_client = client is None and len(sample_urls) > 1
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    pages_sampled = 0
    headers = {"User-Agent": user_agent}

    try:
        for page_url in sample_urls:
            if page_url == target_url and inventory.link_count > 0:
                pages_sampled += 1
                continue
            try:
                response = client.get(page_url, headers=headers)
                body = response.text[:max_body_bytes]
            except httpx.HTTPError:
                continue
            if not body.strip():
                continue
            pages_sampled += 1
            page_path = urlparse(page_url).path or "/"
            page_inv = parse_html_inventory(
                body,
                target_url=page_url,
                check_mixed_content=check_mixed_content,
                check_forms=check_forms,
                max_internal_links=500,
                max_site_links=max_site_links,
                max_images=max_images,
                page_source=page_path,
            )
            merge_inventories(
                inventory,
                page_inv,
                target_url=target_url,
                source=f"page:{page_path}",
                seen=seen,
                max_site_links=max_site_links,
                max_images=max_images,
            )
    finally:
        if own_client and client is not None:
            client.close()

    return pages_sampled, len(sitemap_urls)


def _looks_like_sitemap_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(".xml") or "sitemap" in path
