"""HTML DOM inventory — links, images, forms, mixed content (v2 Tier 1).

What: ``HtmlProbeResult`` holds page HTML; ``parse_html_inventory()`` extracts DOM facts.
Where: ``pipeline._step_html`` reads homepage body from framework artifact when possible.
How: ``beautifulsoup4`` parser — no extra HTTP when framework collector ran first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

from webaudit.collectors.url_utils import same_origin


@dataclass
class HtmlInventory:
    link_count: int = 0
    image_count: int = 0
    form_count: int = 0
    mixed_content_count: int = 0
    internal_link_count: int = 0
    external_link_count: int = 0
    insecure_form_actions: list[str] = field(default_factory=list)
    mixed_content_samples: list[str] = field(default_factory=list)
    internal_links_sample: list[str] = field(default_factory=list)
    site_links: list[dict[str, str]] = field(default_factory=list)
    images: list[dict[str, str]] = field(default_factory=list)
    pages_sampled: int = 0
    sitemap_urls_parsed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_count": self.link_count,
            "image_count": self.image_count,
            "form_count": self.form_count,
            "mixed_content_count": self.mixed_content_count,
            "internal_link_count": self.internal_link_count,
            "external_link_count": self.external_link_count,
            "insecure_form_actions": self.insecure_form_actions,
            "mixed_content_samples": self.mixed_content_samples,
            "internal_links_sample": self.internal_links_sample,
            "site_links": self.site_links,
            "images": self.images,
            "pages_sampled": self.pages_sampled,
            "sitemap_urls_parsed": self.sitemap_urls_parsed,
            "site_links_catalogued": len(self.site_links),
            "images_catalogued": len(self.images),
        }


@dataclass
class HtmlProbeResult:
    target_url: str
    body: str = ""
    pages_scanned: int = 0
    inventory: HtmlInventory = field(default_factory=HtmlInventory)
    error: str | None = None

    def to_artifact(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "pages_scanned": self.pages_scanned,
            "body_length": len(self.body),
            "inventory": self.inventory.to_dict(),
            "error": self.error,
        }


def _absolute_url(base_url: str, href: str) -> str | None:
    href = (href or "").strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    return urljoin(base_url.rstrip("/") + "/", href)


def _add_unique(
    bucket: list[dict[str, str]],
    *,
    url: str,
    kind: str,
    source: str,
    seen: set[str],
    limit: int,
) -> None:
    if len(bucket) >= limit or url in seen:
        return
    seen.add(url)
    bucket.append({"url": url, "kind": kind, "source": source})


def _page_source(target_url: str, page_source: str | None = None) -> str:
    if page_source:
        return page_source
    return urlparse(target_url).path or "/"


def _collect_srcset(
    bucket: list[dict[str, str]],
    *,
    target_url: str,
    srcset: str,
    kind: str,
    source: str,
    seen: set[str],
    limit: int,
) -> None:
    if not isinstance(srcset, str):
        return
    for part in srcset.split(","):
        piece = part.strip().split(" ", 1)[0]
        absolute = _absolute_url(target_url, piece)
        if absolute:
            _add_unique(
                bucket,
                url=absolute,
                kind=kind,
                source=source,
                seen=seen,
                limit=limit,
            )


_META_IMAGE_KEYS = frozenset({"og:image", "twitter:image", "twitter:image:src"})


def parse_html_inventory(
    html: str,
    *,
    target_url: str,
    check_mixed_content: bool = True,
    check_forms: bool = True,
    max_internal_links: int = 50,
    max_site_links: int = 250,
    max_images: int = 250,
    page_source: str | None = None,
) -> HtmlInventory:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    inventory = HtmlInventory()

    links = soup.find_all("a", href=True)
    inventory.link_count = len(links)

    images = soup.find_all("img")
    inventory.image_count = len(images)

    forms = soup.find_all("form")
    inventory.form_count = len(forms)

    parsed_target = urlparse(target_url)
    is_https = parsed_target.scheme == "https"
    source = _page_source(target_url, page_source)
    link_seen: set[str] = set()
    image_seen: set[str] = set()

    for link in links:
        href = link.get("href", "")
        absolute = _absolute_url(target_url, href)
        if not absolute:
            continue
        scope = "internal" if same_origin(target_url, absolute) else "external"
        if scope == "internal":
            inventory.internal_link_count += 1
            if len(inventory.internal_links_sample) < max_internal_links:
                inventory.internal_links_sample.append(href[:200])
        else:
            inventory.external_link_count += 1
        _add_unique(
            inventory.site_links,
            url=absolute,
            kind=scope,
            source="homepage",
            seen=link_seen,
            limit=max_site_links,
        )

    for img in images:
        for attr in ("src", "data-src", "data-lazy-src", "data-original"):
            absolute = _absolute_url(target_url, img.get(attr, ""))
            if absolute:
                kind = "img" if attr == "src" else f"img-{attr}"
                _add_unique(
                    inventory.images,
                    url=absolute,
                    kind=kind,
                    source=source,
                    seen=image_seen,
                    limit=max_images,
                )
        _collect_srcset(
            inventory.images,
            target_url=target_url,
            srcset=img.get("srcset", ""),
            kind="img-srcset",
            source=source,
            seen=image_seen,
            limit=max_images,
        )

    for picture in soup.find_all("picture"):
        for source_tag in picture.find_all("source"):
            _collect_srcset(
                inventory.images,
                target_url=target_url,
                srcset=source_tag.get("srcset", ""),
                kind="picture-srcset",
                source=source,
                seen=image_seen,
                limit=max_images,
            )

    for tag in soup.find_all("link", href=True):
        rel = " ".join(tag.get("rel") or []).lower()
        if tag.get("as") == "image":
            absolute = _absolute_url(target_url, tag.get("href", ""))
            if absolute:
                _add_unique(
                    inventory.images,
                    url=absolute,
                    kind="preload-image",
                    source=source,
                    seen=image_seen,
                    limit=max_images,
                )
            continue
        if "apple-touch-icon" in rel:
            kind = "apple-touch-icon"
        elif "icon" in rel or "shortcut icon" in rel:
            kind = "favicon"
        else:
            continue
        absolute = _absolute_url(target_url, tag.get("href", ""))
        if absolute:
            _add_unique(
                inventory.images,
                url=absolute,
                kind=kind,
                source=source,
                seen=image_seen,
                limit=max_images,
            )

    for tag in soup.find_all("meta", content=True):
        key = (tag.get("property") or tag.get("name") or "").lower()
        if key not in _META_IMAGE_KEYS:
            continue
        absolute = _absolute_url(target_url, tag.get("content", ""))
        if absolute:
            _add_unique(
                inventory.images,
                url=absolute,
                kind=key.replace(":", "-"),
                source=source,
                seen=image_seen,
                limit=max_images,
            )

    if check_mixed_content and is_https:
        for tag, attr in (("img", "src"), ("script", "src"), ("link", "href"), ("iframe", "src")):
            for element in soup.find_all(tag):
                value = element.get(attr, "")
                if isinstance(value, str) and value.startswith("http://"):
                    inventory.mixed_content_count += 1
                    if len(inventory.mixed_content_samples) < 10:
                        inventory.mixed_content_samples.append(f"{tag}[{attr}]={value[:120]}")

    if check_forms and is_https:
        for form in forms:
            action = form.get("action", "") or target_url
            if isinstance(action, str) and action.startswith("http://"):
                inventory.insecure_form_actions.append(action[:200])

    return inventory


def collect_html(
    target_url: str,
    *,
    body: str = "",
    user_agent: str,
    timeout_seconds: int,
    max_body_bytes: int = 65536,
    max_internal_links: int = 50,
    max_site_links: int = 250,
    max_images: int = 250,
    client: Any | None = None,
) -> HtmlProbeResult:
    """Fetch homepage HTML when framework collector did not already provide a body."""
    import httpx

    if body:
        result = HtmlProbeResult(target_url=target_url, body=body, pages_scanned=1)
        result.inventory = parse_html_inventory(
            body,
            target_url=target_url,
            max_internal_links=max_internal_links,
            max_site_links=max_site_links,
            max_images=max_images,
        )
        return result

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    try:
        response = client.get(target_url, headers={"User-Agent": user_agent})
        body = response.text[:max_body_bytes]
        result = HtmlProbeResult(target_url=target_url, body=body, pages_scanned=1 if body else 0)
        if body:
            result.inventory = parse_html_inventory(
                body,
                target_url=target_url,
                max_internal_links=max_internal_links,
                max_site_links=max_site_links,
                max_images=max_images,
            )
        return result
    except httpx.HTTPError as exc:
        return HtmlProbeResult(target_url=target_url, error=str(exc))
    finally:
        if own_client:
            client.close()
