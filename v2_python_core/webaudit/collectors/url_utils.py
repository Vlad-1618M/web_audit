"""URL origin helpers shared by HTML and site-discovery collectors."""

from __future__ import annotations

from urllib.parse import urlparse


def registrable_host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        return host[4:]
    return host


def same_origin(target_url: str, url: str) -> bool:
    if not urlparse(url).netloc:
        return True
    return registrable_host(target_url) == registrable_host(url)
