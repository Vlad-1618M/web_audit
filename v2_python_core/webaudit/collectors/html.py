"""HTML DOM inventory — links, images, forms, mixed content (v2 Tier 1).

What: ``HtmlProbeResult`` holds page HTML; ``parse_html_inventory()`` extracts DOM facts.
Where: ``pipeline._step_html`` reads homepage body from framework artifact when possible.
How: ``beautifulsoup4`` parser — no extra HTTP when framework collector ran first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


@dataclass
class HtmlInventory:
    link_count: int = 0
    image_count: int = 0
    form_count: int = 0
    mixed_content_count: int = 0
    insecure_form_actions: list[str] = field(default_factory=list)
    mixed_content_samples: list[str] = field(default_factory=list)
    internal_links_sample: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_count": self.link_count,
            "image_count": self.image_count,
            "form_count": self.form_count,
            "mixed_content_count": self.mixed_content_count,
            "insecure_form_actions": self.insecure_form_actions,
            "mixed_content_samples": self.mixed_content_samples,
            "internal_links_sample": self.internal_links_sample,
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


def parse_html_inventory(
    html: str,
    *,
    target_url: str,
    check_mixed_content: bool = True,
    check_forms: bool = True,
    max_internal_links: int = 50,
) -> HtmlInventory:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    inventory = HtmlInventory()

    links = soup.find_all("a", href=True)
    inventory.link_count = len(links)

    images = soup.find_all("img", src=True)
    inventory.image_count = len(images)

    forms = soup.find_all("form")
    inventory.form_count = len(forms)

    parsed_target = urlparse(target_url)
    target_host = parsed_target.netloc
    is_https = parsed_target.scheme == "https"

    for link in links:
        href = link.get("href", "")
        if len(inventory.internal_links_sample) >= max_internal_links:
            break
        if href.startswith("/") or (target_host and target_host in href):
            inventory.internal_links_sample.append(href[:200])

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
    client: Any | None = None,
) -> HtmlProbeResult:
    """Fetch homepage HTML when framework collector did not already provide a body."""
    import httpx

    if body:
        result = HtmlProbeResult(target_url=target_url, body=body, pages_scanned=1)
        result.inventory = parse_html_inventory(body, target_url=target_url)
        return result

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    try:
        response = client.get(target_url, headers={"User-Agent": user_agent})
        body = response.text[:max_body_bytes]
        result = HtmlProbeResult(target_url=target_url, body=body, pages_scanned=1 if body else 0)
        if body:
            result.inventory = parse_html_inventory(body, target_url=target_url)
        return result
    except httpx.HTTPError as exc:
        return HtmlProbeResult(target_url=target_url, error=str(exc))
    finally:
        if own_client:
            client.close()
