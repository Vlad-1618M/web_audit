"""API surface collector — GraphQL introspection and OpenAPI/Swagger discovery (Tier 2).

What: ``collect_api_surface()`` probes common GraphQL and OpenAPI paths.
Where: ``pipeline._step_api`` when ``collectors.api.enabled``.
How: httpx POST/GET with short timeouts; no auth assumed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from webaudit.config.settings import ApiCollectorSettings

_INTROSPECTION_QUERY = json.dumps(
    {"query": "{ __schema { queryType { name } } }"},
    separators=(",", ":"),
)


@dataclass
class GraphqlProbeEntry:
    path: str
    status_code: int | None = None
    introspection_enabled: bool = False
    response_snippet: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "status_code": self.status_code,
            "introspection_enabled": self.introspection_enabled,
            "response_snippet": self.response_snippet,
            "error": self.error,
        }


@dataclass
class OpenApiProbeEntry:
    path: str
    status_code: int | None = None
    openapi_detected: bool = False
    title: str = ""
    version: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "status_code": self.status_code,
            "openapi_detected": self.openapi_detected,
            "title": self.title,
            "version": self.version,
            "error": self.error,
        }


@dataclass
class ApiProbeResult:
    target_url: str
    graphql_probes: list[GraphqlProbeEntry] = field(default_factory=list)
    openapi_probes: list[OpenApiProbeEntry] = field(default_factory=list)

    def to_artifact(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "graphql": [p.to_dict() for p in self.graphql_probes],
            "openapi": [p.to_dict() for p in self.openapi_probes],
        }


def _looks_like_graphql_introspection(body: str) -> bool:
    text = body.lower()
    return "__schema" in text and "querytype" in text.replace(" ", "")


def _parse_openapi_meta(body: str) -> tuple[bool, str, str]:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return False, "", ""
    if not isinstance(data, dict):
        return False, "", ""
    if "openapi" not in data and "swagger" not in data:
        return False, "", ""
    info = data.get("info") if isinstance(data.get("info"), dict) else {}
    title = str(info.get("title") or data.get("title") or "")
    version = str(info.get("version") or data.get("openapi") or data.get("swagger") or "")
    return True, title[:120], version[:40]


def collect_api_surface(
    target_url: str,
    *,
    settings: ApiCollectorSettings,
    user_agent: str,
    timeout_seconds: int,
    client: Any | None = None,
) -> ApiProbeResult:
    import httpx

    result = ApiProbeResult(target_url=target_url)
    base = target_url.rstrip("/")
    headers = {"User-Agent": user_agent, "Accept": "application/json, */*"}
    post_headers = {**headers, "Content-Type": "application/json"}

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    try:
        if settings.graphql_probe:
            seen: set[str] = set()
            for path in settings.graphql_paths:
                if path in seen:
                    continue
                seen.add(path)
                entry = GraphqlProbeEntry(path=path)
                url = f"{base}{path}"
                try:
                    response = client.post(url, headers=post_headers, content=_INTROSPECTION_QUERY)
                    entry.status_code = response.status_code
                    body = response.text[:4000]
                    entry.response_snippet = body[:500]
                    entry.introspection_enabled = (
                        response.status_code == 200 and _looks_like_graphql_introspection(body)
                    )
                except httpx.HTTPError as exc:
                    entry.error = str(exc)
                result.graphql_probes.append(entry)

        seen_openapi: set[str] = set()
        for path in settings.openapi_paths:
            if path in seen_openapi:
                continue
            seen_openapi.add(path)
            entry = OpenApiProbeEntry(path=path)
            url = f"{base}{path}"
            try:
                response = client.get(url, headers=headers)
                entry.status_code = response.status_code
                if response.status_code == 200:
                    detected, title, version = _parse_openapi_meta(response.text[:200_000])
                    entry.openapi_detected = detected
                    entry.title = title
                    entry.version = version
            except httpx.HTTPError as exc:
                entry.error = str(exc)
            result.openapi_probes.append(entry)

        return result
    finally:
        if own_client:
            client.close()
