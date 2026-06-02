"""CORS collector — API path probes with forged Origin (v1 ``check_cors()`` parity).

What: ``collect_cors()`` sends HEAD requests with ``Origin: evil.example.com``.
Where: Registered in ``pipeline._step_cors``; stored in ``artifacts.inventory.cors``.
How: Probes built-in ``/api/`` paths plus config extras; analyzer classifies ACAO values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from webaudit.config.settings import CorsCollectorSettings


@dataclass
class CorsProbeEntry:
    path: str
    status_code: int | None = None
    acao: str | None = None
    acac: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "status_code": self.status_code,
            "acao": self.acao,
            "acac": self.acac,
            "error": self.error,
        }


@dataclass
class CorsProbeResult:
    target_url: str
    origin_sent: str
    probes: list[CorsProbeEntry] = field(default_factory=list)

    def to_artifact(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "origin_sent": self.origin_sent,
            "probes": [p.to_dict() for p in self.probes],
            "notes": [
                f"path={p.path} ACAO={p.acao}" + (f", ACAC={p.acac}" if p.acac else "")
                for p in self.probes
                if p.acao
            ],
        }


def collect_cors(
    target_url: str,
    *,
    settings: CorsCollectorSettings,
    user_agent: str,
    timeout_seconds: int,
    extra_api_paths: list[str] | None = None,
    client: Any | None = None,
) -> CorsProbeResult:
    import httpx

    result = CorsProbeResult(target_url=target_url, origin_sent=settings.probe_origin)
    base = target_url.rstrip("/")

    seen: set[str] = set()
    paths: list[str] = []
    for path in settings.api_paths:
        if path not in seen:
            seen.add(path)
            paths.append(path)
    for path in extra_api_paths or []:
        if path.startswith("/api/") and path not in seen:
            seen.add(path)
            paths.append(path)

    headers = {
        "User-Agent": user_agent,
        "Origin": settings.probe_origin,
    }

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=False)

    try:
        for path in paths:
            url = f"{base}{path}"
            entry = CorsProbeEntry(path=path)
            try:
                response = client.head(url, headers=headers)
                entry.status_code = response.status_code
                entry.acao = response.headers.get("access-control-allow-origin")
                entry.acac = response.headers.get("access-control-allow-credentials")
            except httpx.HTTPError as exc:
                entry.error = str(exc)
            result.probes.append(entry)
        return result
    finally:
        if own_client:
            client.close()
