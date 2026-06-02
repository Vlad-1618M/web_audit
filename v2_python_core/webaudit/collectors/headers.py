"""HTTP response header collector.

What: ``collect_headers()`` probes a URL via HEAD (GET fallback) and normalizes response headers.
Where: Called from ``orchestrator.run_audit()``; raw output stored in ``artifacts.headers``.
How: Pass ``target_url``, ``user_agent``, ``timeout_seconds``; optional injected ``httpx.Client`` for tests.
      Returns ``HeaderProbeResult`` for ``analyzers/headers.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HeaderProbeResult:
    target_url: str
    final_url: str
    status_code: int | None
    headers: dict[str, str] = field(default_factory=dict)
    raw_header_lines: list[str] = field(default_factory=list)
    error: str | None = None

    def to_artifact(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "final_url": self.final_url,
            "status_code": self.status_code,
            "headers": self.headers,
            "error": self.error,
        }


def collect_headers(
    target_url: str,
    *,
    user_agent: str,
    timeout_seconds: int,
    client: Any | None = None,
) -> HeaderProbeResult:
    """Fetch response headers via HEAD, falling back to GET on 405."""
    import httpx

    headers_req = {"User-Agent": user_agent}
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    try:
        response = client.head(target_url, headers=headers_req)
        if response.status_code == 405:
            response = client.get(target_url, headers=headers_req)
        normalized: dict[str, str] = {}
        for key, value in response.headers.items():
            normalized[key.lower()] = value
        return HeaderProbeResult(
            target_url=target_url,
            final_url=str(response.url),
            status_code=response.status_code,
            headers=normalized,
            raw_header_lines=[f"{k}: {v}" for k, v in response.headers.multi_items()],
        )
    except httpx.HTTPError as exc:
        return HeaderProbeResult(
            target_url=target_url,
            final_url=target_url,
            status_code=None,
            error=str(exc),
        )
    finally:
        if own_client:
            client.close()
