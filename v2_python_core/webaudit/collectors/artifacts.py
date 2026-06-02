"""Well-known artifacts collector — robots.txt, security.txt, sitemap.xml (v1 parity).

What: ``collect_artifacts()`` fetches public discovery files via GET.
Where: Registered in ``pipeline._step_artifacts``; stored under ``artifacts.inventory``.
How: Truncates bodies per config limits; parsing happens in ``analyzers/artifacts.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from webaudit.config.settings import ArtifactsCollectorSettings


@dataclass
class RobotsArtifact:
    status_code: int | None = None
    raw: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"status_code": self.status_code, "raw": self.raw, "error": self.error}


@dataclass
class SecurityTxtArtifact:
    body: str = ""
    present: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"body": self.body, "present": self.present, "error": self.error}


@dataclass
class SitemapArtifact:
    status_code: int | None = None
    raw: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"status_code": self.status_code, "raw": self.raw, "error": self.error}


@dataclass
class ArtifactsProbeResult:
    target_url: str
    robots: RobotsArtifact = field(default_factory=RobotsArtifact)
    security_txt: SecurityTxtArtifact = field(default_factory=SecurityTxtArtifact)
    sitemap: SitemapArtifact = field(default_factory=SitemapArtifact)

    def to_artifact(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "robots": self.robots.to_dict(),
            "security_txt": self.security_txt.to_dict(),
            "sitemap": self.sitemap.to_dict(),
        }


def collect_artifacts(
    target_url: str,
    *,
    settings: ArtifactsCollectorSettings,
    user_agent: str,
    timeout_seconds: int,
    client: Any | None = None,
) -> ArtifactsProbeResult:
    import httpx

    result = ArtifactsProbeResult(target_url=target_url)
    base = target_url.rstrip("/")
    headers = {"User-Agent": user_agent}

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    try:
        if settings.check_robots:
            url = f"{base}/robots.txt"
            try:
                response = client.get(url, headers=headers)
                result.robots.status_code = response.status_code
                if response.status_code == 200:
                    result.robots.raw = response.text[: settings.max_robots_bytes]
            except httpx.HTTPError as exc:
                result.robots.error = str(exc)

        if settings.check_security_txt:
            url = f"{base}/.well-known/security.txt"
            try:
                response = client.get(url, headers=headers)
                body = response.text[: settings.max_security_txt_bytes]
                if body and "<html" not in body.lower():
                    result.security_txt.body = body
                    result.security_txt.present = True
            except httpx.HTTPError as exc:
                result.security_txt.error = str(exc)

        if settings.check_sitemap:
            url = f"{base}/sitemap.xml"
            try:
                response = client.get(url, headers=headers)
                result.sitemap.status_code = response.status_code
                if response.status_code == 200:
                    result.sitemap.raw = response.text[: settings.max_sitemap_bytes]
            except httpx.HTTPError as exc:
                result.sitemap.error = str(exc)

        return result
    finally:
        if own_client:
            client.close()
