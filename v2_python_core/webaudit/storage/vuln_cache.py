"""SQLite TTL cache for vulnerability lookups (WPScan/API results + snapshot hits)."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CachedVulnLookup:
    unit: str
    slug: str
    version: str
    hits: list[dict[str, Any]]
    source: str
    fetched_at: float


def default_cache_path() -> Path:
    return Path.home() / ".local" / "share" / "webaudit" / "vuln_cache.db"


class VulnCache:
    def __init__(self, path: Path | None = None, *, ttl_days: int = 14) -> None:
        self.path = path or default_cache_path()
        self.ttl_seconds = max(1, ttl_days) * 86_400
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vuln_lookup (
                    unit TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    version TEXT NOT NULL,
                    source TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    fetched_at REAL NOT NULL,
                    PRIMARY KEY (unit, slug, version, source)
                )
                """
            )
            conn.commit()

    def get(self, unit: str, slug: str, version: str, *, source: str) -> CachedVulnLookup | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload, fetched_at, source
                FROM vuln_lookup
                WHERE unit = ? AND slug = ? AND version = ? AND source = ?
                """,
                (unit, slug.lower(), version, source),
            ).fetchone()
        if row is None:
            return None
        fetched_at = float(row["fetched_at"])
        if time.time() - fetched_at > self.ttl_seconds:
            return None
        payload = json.loads(row["payload"])
        hits = payload if isinstance(payload, list) else payload.get("hits") or []
        return CachedVulnLookup(
            unit=unit,
            slug=slug.lower(),
            version=version,
            hits=hits,
            source=source,
            fetched_at=fetched_at,
        )

    def put(
        self,
        unit: str,
        slug: str,
        version: str,
        *,
        source: str,
        hits: list[dict[str, Any]],
    ) -> None:
        payload = json.dumps(hits, ensure_ascii=False)
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO vuln_lookup (unit, slug, version, source, payload, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(unit, slug, version, source) DO UPDATE SET
                    payload = excluded.payload,
                    fetched_at = excluded.fetched_at
                """,
                (unit, slug.lower(), version, source, payload, now),
            )
            conn.commit()

    def purge_expired(self) -> int:
        cutoff = time.time() - self.ttl_seconds
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM vuln_lookup WHERE fetched_at < ?", (cutoff,))
            conn.commit()
            return int(cursor.rowcount)
