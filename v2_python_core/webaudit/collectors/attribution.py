"""Designer / creator attribution — lightweight v1 parity from homepage HTML."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

_DESIGN_LABELS = (
    r"Designed by|Design by|Created by|Developed by|Built by|Crafted by|"
    r"Theme by|Site by|Made by|Maintained by|Author:|Creator:|"
    r"Coded by|Website by|Web design by"
)
_POWERED_LABELS = r"Powered by|Powered with|Built with"
_ALL_LABELS = f"{_DESIGN_LABELS}|{_POWERED_LABELS}"
_NAME_CAPTURE = r"([A-Za-z][A-Za-z0-9 .'&()-]{2,55})"

_NOISE = re.compile(
    r"^(wordpress|elementor|cloudflare|nginx|apache|shopify|wix|squarespace|"
    r"google|vercel|netlify|react|vue|laravel|django|rails)$",
    re.I,
)
_META_NAMES = re.compile(r"^(author|designer|creator|web_author|copyright|publisher)$", re.I)
_DESIGN_LABEL_RE = re.compile(rf"({_DESIGN_LABELS})\s+{_NAME_CAPTURE}", re.I)
_POWERED_LABEL_RE = re.compile(rf"({_POWERED_LABELS})\s+{_NAME_CAPTURE}", re.I)
_ALL_LABEL_RE = re.compile(rf"({_ALL_LABELS})\s+{_NAME_CAPTURE}", re.I)

_SITE_FOOTER_RE = re.compile(
    r"(^|\s)(main-footer|site-footer|page-footer|global-footer|colophon)(\s|$)",
    re.I,
)
_SIDEBAR_RE = re.compile(r"sidebar|side-nav|side_nav", re.I)
_NAV_HINT_RE = re.compile(r"nav|menu|agent|muzar|chatbot|assistant", re.I)
_AI_VENDOR_RE = re.compile(
    r"^(claude|anthropic|openai|chatgpt|gpt-?4|gpt-?3|gemini|deepseek|grok|"
    r"copilot|midjourney|dall-?e|stable diffusion|adobe firefly|firefly)$",
    re.I,
)
_AI_DOC_HOST_RE = re.compile(
    r"(^|\.)docs\.anthropic\.com|(^|\.)platform\.openai\.com|(^|\.)ai\.google\.dev|"
    r"(^|\.)docs\.x\.ai|(^|\.)platform\.deepseek\.com|(^|\.)openai\.com",
    re.I,
)
_SKIP_TEXT_PARENTS = frozenset({"script", "style", "noscript", "template", "svg"})


@dataclass
class AttributionInfo:
    name: str | None = None
    source: str | None = None
    link_url: str | None = None
    placement: str | None = None
    trace: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "link_url": self.link_url,
            "placement": self.placement,
            "trace": self.trace,
            "found": bool(self.name),
        }


def _trim_name(raw: str) -> str | None:
    name = re.sub(r"\s+", " ", raw.strip())
    name = re.split(r"[,|@—–-]", name, maxsplit=1)[0].strip()
    name = re.sub(r"\([^)]*\)", "", name).strip()
    name = re.sub(r"[<|].*", "", name).strip()
    if len(name) < 3 or len(name) > 60:
        return None
    if _NOISE.match(name):
        return None
    return name


def _primary_vendor_token(name: str) -> str:
    return re.split(r"\s+", name.strip(), maxsplit=1)[0]


def _is_design_label(label: str) -> bool:
    return bool(re.search(_DESIGN_LABELS, label, re.I))


def _is_powered_label(label: str) -> bool:
    return bool(re.search(_POWERED_LABELS, label, re.I))


def _is_agent_tooling(label: str, name: str, link_url: str | None = None) -> bool:
    """Embedded AI/API tooling — not a site designer credit."""
    if _is_design_label(label):
        return False
    if not _is_powered_label(label):
        return False
    if not _AI_VENDOR_RE.match(_primary_vendor_token(name)):
        return False
    if link_url and _AI_DOC_HOST_RE.search(urlparse(link_url).netloc):
        return True
    return True


def _element_context(tag: Tag | None) -> str:
    if tag is None:
        return ""
    parts = [tag.name or "", tag.get("id") or "", " ".join(tag.get("class") or [])]
    return " ".join(parts).lower()


def _is_site_footer(tag: Tag | None) -> bool:
    for parent in tag.parents if tag else []:
        if not isinstance(parent, Tag):
            continue
        context = _element_context(parent)
        if _SIDEBAR_RE.search(context):
            continue
        if parent.name == "footer":
            return True
        if _SITE_FOOTER_RE.search(context):
            return True
    return False


def _is_nav_or_tooling_context(tag: Tag | None) -> bool:
    for parent in tag.parents if tag else []:
        if not isinstance(parent, Tag):
            continue
        context = _element_context(parent)
        if _SIDEBAR_RE.search(context) or _NAV_HINT_RE.search(context):
            return True
        if parent.name in {"nav", "header"}:
            return True
    return False


def _credit_from_text(text: str, *, allow_powered: bool) -> tuple[str, str] | None:
    pattern = _ALL_LABEL_RE if allow_powered else _DESIGN_LABEL_RE
    match = pattern.search(text)
    if not match:
        return None
    label = match.group(1)
    name = _trim_name(match.group(2))
    if not name:
        return None
    if _is_agent_tooling(label, name):
        return None
    return label, name


def _visible_text_nodes(soup: BeautifulSoup) -> list[tuple[str, Tag]]:
    nodes: list[tuple[str, Tag]] = []
    for node in soup.find_all(string=True):
        if not isinstance(node, NavigableString):
            continue
        parent = node.parent
        if not isinstance(parent, Tag):
            continue
        if parent.name in _SKIP_TEXT_PARENTS:
            continue
        text = str(node).strip()
        if text:
            nodes.append((text, parent))
    return nodes


def _footer_regions(soup: BeautifulSoup) -> list[Tag]:
    regions: list[Tag] = []
    seen: set[int] = set()
    for tag in soup.find_all(["footer", "div", "section"]):
        if id(tag) in seen:
            continue
        context = _element_context(tag)
        if _SIDEBAR_RE.search(context):
            continue
        if tag.name == "footer" or _SITE_FOOTER_RE.search(context):
            seen.add(id(tag))
            regions.append(tag)
    return regions


def _find_footer_link(
    soup: BeautifulSoup,
    *,
    name: str,
    label: str,
    base_url: str,
) -> str | None:
    name_lower = name.lower()
    label_lower = label.lower()
    for anchor in soup.find_all("a", href=True):
        if not _is_site_footer(anchor):
            continue
        anchor_text = anchor.get_text(" ", strip=True)
        blob = f"{anchor_text} {anchor.get('title') or ''}".lower()
        if label_lower in blob or name_lower in anchor_text.lower():
            return urljoin(base_url, anchor["href"])
    return None


def _apply_credit(
    info: AttributionInfo,
    *,
    label: str,
    name: str,
    source: str,
    placement: str,
    soup: BeautifulSoup,
    base_url: str,
    container: Tag | None = None,
) -> AttributionInfo:
    if _is_agent_tooling(label, name):
        return info
    info.name = name
    info.source = source
    info.placement = placement
    info.trace.append(f"label={label}")
    if container is not None:
        info.trace.append(f"context={_element_context(container)[:80]}")
    link = _find_footer_link(soup, name=name, label=label, base_url=base_url)
    if link:
        if _is_agent_tooling(label, name, link):
            return AttributionInfo(trace=[*info.trace, "rejected=agent_tooling_link"])
        info.link_url = link
        info.source = "footer_link"
    return info


def extract_attribution(html: str, *, base_url: str) -> AttributionInfo:
    info = AttributionInfo()
    if not html.strip():
        return info

    head = html[:25000]

    comment_match = re.search(
        rf"<!--[^>]*(?:{_ALL_LABELS})[^>]*-->",
        head,
        re.I | re.S,
    )
    if comment_match:
        inner = re.sub(r"<!--|-->", "", comment_match.group(0))
        parsed = _credit_from_text(inner, allow_powered=True)
        if parsed:
            credit_label, name = parsed
            info.name = name
            info.source = "html_comment"
            info.placement = "acceptable"
            info.trace.append(f"label={credit_label}")
            return info

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all("meta", content=True):
        key = (tag.get("name") or tag.get("property") or "").strip()
        if not _META_NAMES.match(key):
            continue
        name = _trim_name(tag.get("content", ""))
        if name:
            info.name = name
            info.source = "meta_tag"
            info.placement = "meta"
            info.trace.append(f"meta name={key}")
            return info

    for region in _footer_regions(soup):
        region_text = region.get_text(" ", strip=True)
        hit = _credit_from_text(region_text, allow_powered=True)
        if hit:
            label, name = hit
            return _apply_credit(
                info,
                label=label,
                name=name,
                source="visible_text",
                placement="visible",
                soup=soup,
                base_url=base_url,
                container=region,
            )

    for text, parent in _visible_text_nodes(soup):
        if _is_nav_or_tooling_context(parent):
            continue
        hit = _credit_from_text(text, allow_powered=False)
        if hit:
            label, name = hit
            return _apply_credit(
                info,
                label=label,
                name=name,
                source="visible_text",
                placement="visible",
                soup=soup,
                base_url=base_url,
                container=parent,
            )

    title = soup.find("title")
    if title and title.string:
        hit = _credit_from_text(title.string, allow_powered=False)
        if hit:
            label, name = hit
            info.name = name
            info.source = "title_tag"
            info.placement = "title"
            info.trace.append(f"label={label}")
            return info

    return info
