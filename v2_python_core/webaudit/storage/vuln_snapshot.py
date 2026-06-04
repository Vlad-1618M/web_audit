"""Shipped CVE snapshot loader — offline plugin/theme vulnerability data."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version


@dataclass
class VulnRecord:
    unit: str
    slug: str
    cve_id: str
    title: str
    auth_required: str
    severity: str
    cvss: float | None = None
    affected_min: str | None = None
    affected_max: str | None = None
    fixed_in: str | None = None
    aliases: list[str] = field(default_factory=list)

    def slug_keys(self) -> set[str]:
        keys = {self.slug.lower()}
        keys.update(alias.lower() for alias in self.aliases)
        return keys


@dataclass
class VulnSnapshot:
    schema_version: str
    updated: str
    plugins: list[VulnRecord] = field(default_factory=list)
    themes: list[VulnRecord] = field(default_factory=list)

    def records_for(self, unit: str, slug: str) -> list[VulnRecord]:
        lowered = slug.lower()
        pool = self.plugins if unit == "plugin" else self.themes
        return [record for record in pool if lowered in record.slug_keys()]


def _parse_version(raw: str | None) -> Version | None:
    if not raw:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    try:
        return Version(cleaned)
    except InvalidVersion:
        return None


def version_is_affected(detected_raw: str | None, record: VulnRecord) -> bool:
    detected = _parse_version(detected_raw)
    if detected is None:
        return False

    fixed = _parse_version(record.fixed_in)
    if fixed is not None and detected >= fixed:
        return False

    affected_min = _parse_version(record.affected_min)
    if affected_min is not None and detected < affected_min:
        return False

    affected_max = _parse_version(record.affected_max)
    if affected_max is not None and detected > affected_max:
        return False

    if affected_min is None and affected_max is None and fixed is None:
        return False

    return True


def _record_from_dict(unit: str, item: dict[str, Any]) -> VulnRecord:
    return VulnRecord(
        unit=unit,
        slug=str(item.get("slug") or ""),
        cve_id=str(item.get("cve_id") or ""),
        title=str(item.get("title") or ""),
        auth_required=str(item.get("auth_required") or "none").lower(),
        severity=str(item.get("severity") or "MEDIUM").upper(),
        cvss=float(item["cvss"]) if item.get("cvss") is not None else None,
        affected_min=item.get("affected_min"),
        affected_max=item.get("affected_max"),
        fixed_in=item.get("fixed_in"),
        aliases=[str(alias) for alias in item.get("aliases") or []],
    )


def default_snapshot_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "vuln_snapshot.json"


@lru_cache(maxsize=4)
def load_vuln_snapshot(path: str | None = None) -> VulnSnapshot:
    snapshot_path = Path(path).expanduser() if path else default_snapshot_path()
    with snapshot_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    plugins = [_record_from_dict("plugin", item) for item in data.get("plugins") or []]
    themes = [_record_from_dict("theme", item) for item in data.get("themes") or []]
    return VulnSnapshot(
        schema_version=str(data.get("schema_version") or "1.0"),
        updated=str(data.get("updated") or ""),
        plugins=plugins,
        themes=themes,
    )
