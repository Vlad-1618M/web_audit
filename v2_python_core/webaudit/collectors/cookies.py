"""Cookie collector — Set-Cookie parsing from login and homepage (v1 ``check_cookies()`` parity).

What: ``collect_cookies()`` fetches login URL (framework default) then homepage fallback.
Where: Registered in ``pipeline._step_cookies``; stored in ``artifacts.inventory.cookies``.
How: Parses raw Set-Cookie header lines for flag analysis in ``analyzers/cookies.py``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

from webaudit.collectors.framework_urls import login_path_for_framework


@dataclass
class CookieEntry:
    name: str
    raw: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "raw": self.raw}


@dataclass
class CookiesProbeResult:
    target_url: str
    source_url: str | None = None
    cookies: list[CookieEntry] = field(default_factory=list)
    error: str | None = None

    def to_artifact(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "source_url": self.source_url,
            "cookies": [c.to_dict() for c in self.cookies],
            "error": self.error,
        }


_COOKIE_NAME_RE = re.compile(r"^Set-Cookie:\s*", re.IGNORECASE)


def _parse_set_cookie_lines(header_lines: list[str]) -> list[CookieEntry]:
    cookies: list[CookieEntry] = []
    for line in header_lines:
        raw = _COOKIE_NAME_RE.sub("", line.strip())
        if not raw:
            continue
        name = raw.split("=", 1)[0].strip()
        if name:
            cookies.append(CookieEntry(name=name, raw=raw))
    return cookies


def collect_cookies(
    target_url: str,
    *,
    framework: str,
    user_agent: str,
    timeout_seconds: int,
    client: Any | None = None,
) -> CookiesProbeResult:
    import httpx

    result = CookiesProbeResult(target_url=target_url)
    base = target_url.rstrip("/")
    login_url = f"{base}{login_path_for_framework(framework)}"

    headers_req = {"User-Agent": user_agent}
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    try:
        for url in (login_url, base):
            try:
                response = client.get(url, headers=headers_req)
            except httpx.HTTPError as exc:
                result.error = str(exc)
                continue
            lines = [f"Set-Cookie: {value}" for value in response.headers.get_list("set-cookie")]
            cookies = _parse_set_cookie_lines(lines)
            if cookies:
                result.source_url = str(response.url)
                result.cookies = cookies
                return result
        return result
    finally:
        if own_client:
            client.close()
