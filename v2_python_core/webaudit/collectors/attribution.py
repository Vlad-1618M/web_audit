"""Designer / creator attribution — lightweight v1 parity from homepage HTML."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

_CREDIT_LABELS = (
    r"Designed by|Design by|Created by|Developed by|Built by|Crafted by|"
    r"Theme by|Site by|Powered by|Made by|Maintained by|Author:|Creator:|"
    r"Coded by|Website by|Web design by"
)
_NOISE = re.compile(
    r"^(wordpress|elementor|cloudflare|nginx|apache|shopify|wix|squarespace|"
    r"google|vercel|netlify|react|vue|laravel|django|rails)$",
    re.I,
)
_META_NAMES = re.compile(r"^(author|designer|creator|web_author|copyright|publisher)$", re.I)


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
    name = re.sub(r"[<|].*", "", name).strip()
    if len(name) < 3 or len(name) > 60:
        return None
    if _NOISE.match(name):
        return None
    return name


def _from_label_match(match: re.Match[str]) -> str | None:
    return _trim_name(match.group(0).split(maxsplit=2)[-1] if " " in match.group(0) else match.group(0))


def extract_attribution(html: str, *, base_url: str) -> AttributionInfo:
    from bs4 import BeautifulSoup

    info = AttributionInfo()
    if not html.strip():
        return info

    head = html[:25000]

    comment_match = re.search(
        rf"<!--[^>]*(?:{_CREDIT_LABELS})[^>]*-->",
        head,
        re.I | re.S,
    )
    if comment_match:
        inner = re.sub(r"<!--|-->", "", comment_match.group(0))
        label_match = re.search(rf"(?:{_CREDIT_LABELS})\s*([^\n<]+)", inner, re.I)
        if label_match:
            name = _trim_name(label_match.group(1))
            if name:
                info.name = name
                info.source = "html_comment"
                info.placement = "acceptable"
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

    text_match = re.search(rf"({_CREDIT_LABELS})\s+([A-Za-z][A-Za-z0-9 .'&-]{{2,55}})", head, re.I)
    if text_match:
        name = _trim_name(text_match.group(2))
        if name:
            info.name = name
            info.source = "visible_text"
            info.placement = "visible"
            for anchor in soup.find_all("a", href=True):
                if name.lower() in anchor.get_text(" ", strip=True).lower():
                    info.link_url = urljoin(base_url, anchor["href"])
                    info.source = "footer_link"
                    break
            return info

    title = soup.find("title")
    if title and title.string:
        title_match = re.search(rf"({_CREDIT_LABELS})\s+([A-Za-z][A-Za-z0-9 .'-]{{2,40}})", title.string, re.I)
        if title_match:
            name = _trim_name(title_match.group(2))
            if name:
                info.name = name
                info.source = "title_tag"
                info.placement = "title"
                return info

    return info
