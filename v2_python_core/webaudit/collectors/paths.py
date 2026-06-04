"""Sensitive path collector — HTTP probes for exposure (v1 ``probe_path`` parity).

What: ``collect_paths()`` GETs each path (raw + final status) and classifies response notes.
Where: Registered in ``pipeline.py`` when ``paths.enabled``; stored in ``artifacts.inventory.paths``.
How: Built-in lists from ``path_lists.py`` + ``paths.extra_paths``; capped by ``max_probe_urls``.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from webaudit.collectors.path_lists import paths_for_framework
from webaudit.config.settings import PathsSettings


@dataclass
class PathProbeEntry:
    path: str
    raw_status: int | None
    final_status: int | None
    note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "raw_status": self.raw_status,
            "final_status": self.final_status,
            "note": self.note,
        }


@dataclass
class PathsProbeResult:
    target_url: str
    probes: list[PathProbeEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_artifact(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "probe_count": len(self.probes),
            "paths": [p.to_dict() for p in self.probes],
            "errors": self.errors,
        }


def classify_final_status(status_code: int | None) -> str:
    if status_code is None:
        return "NO_RESPONSE"
    if status_code == 200:
        return "OPEN"
    if status_code in {301, 302, 303, 307, 308}:
        return "REDIRECT"
    if status_code == 401:
        return "PROTECTED_401"
    if status_code == 403:
        return "PROTECTED_403"
    if status_code == 404:
        return "NOT_FOUND"
    if status_code == 429:
        return "RATE_LIMITED"
    if status_code in {500, 502, 503, 504}:
        return "SERVER_ERROR"
    if status_code in {520, 521, 522, 524}:
        return "CF_BLOCKED"
    return f"OTHER_{status_code}"


def path_to_url(target_url: str, path: str) -> str:
    base = target_url.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


def build_probe_list(
    *,
    framework: str,
    paths_settings: PathsSettings,
) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    def add(path: str) -> None:
        if not path.startswith("/"):
            path = f"/{path}"
        if path not in seen:
            seen.add(path)
            out.append(path)

    if paths_settings.sensitive_builtin:
        for path in paths_for_framework(framework):
            add(path)
    for path in paths_settings.extra_paths:
        add(path)
    for path in paths_settings.expected_open:
        add(path)

    limit = paths_settings.max_probe_urls
    return out[:limit]


def collect_paths(
    target_url: str,
    *,
    framework: str,
    paths_settings: PathsSettings,
    user_agent: str,
    timeout_seconds: int,
    probe_delay_ms: int = 0,
    client: Any | None = None,
    on_probe_start: Callable[[int], None] | None = None,
    on_probe: Callable[[PathProbeEntry, int, int], None] | None = None,
) -> PathsProbeResult:
    import httpx

    probe_paths = build_probe_list(framework=framework, paths_settings=paths_settings)
    result = PathsProbeResult(target_url=target_url)

    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_seconds)

    total = len(probe_paths)
    if on_probe_start and total:
        on_probe_start(total)

    try:
        for index, path in enumerate(probe_paths, start=1):
            url = path_to_url(target_url, path)
            raw_status: int | None = None
            final_status: int | None = None
            note = "NO_RESPONSE"
            try:
                raw_resp = client.get(url, headers=headers, follow_redirects=False)
                raw_status = raw_resp.status_code
                final_resp = client.get(url, headers=headers, follow_redirects=True)
                final_status = final_resp.status_code
                note = classify_final_status(final_status)
            except httpx.HTTPError as exc:
                result.errors.append(f"{path}: {exc}")

            entry = PathProbeEntry(
                path=path,
                raw_status=raw_status,
                final_status=final_status,
                note=note,
            )
            result.probes.append(entry)
            if on_probe:
                on_probe(entry, index, total)
            if probe_delay_ms > 0:
                time.sleep(probe_delay_ms / 1000.0)
    finally:
        if own_client:
            client.close()

    return result
