"""Framework profile loader — shipped YAML under ``webaudit/profiles/``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator


class ProfileProbeSettings(BaseModel):
    mode: str = "observed_only"
    readme_fetch: str = "observed_only"
    sources: list[str] = Field(default_factory=list)


class ProfileCompareSettings(BaseModel):
    wporg_api: bool = False
    pypi_api: bool = False
    packagist_api: bool = False
    rubygems_api: bool = False


class ProfileScoringSettings(BaseModel):
    hygiene_cap: int = Field(default=30, ge=0, le=100)


class WatchlistEntry(BaseModel):
    slug: str = ""
    package: str = ""
    tier: str = "medium"
    premium: bool = False
    compare_latest: bool = True

    @model_validator(mode="after")
    def _normalize_name_fields(self) -> WatchlistEntry:
        if self.slug and not self.package:
            self.package = self.slug
        elif self.package and not self.slug:
            self.slug = self.package
        return self

    @property
    def name(self) -> str:
        return self.slug or self.package


class FrameworkProfile(BaseModel):
    framework: str
    fingerprint_unit: str = "plugin"
    min_detection_confidence: float = 0.65
    probe: ProfileProbeSettings = Field(default_factory=ProfileProbeSettings)
    compare: ProfileCompareSettings = Field(default_factory=ProfileCompareSettings)
    scoring: ProfileScoringSettings = Field(default_factory=ProfileScoringSettings)
    watchlist: list[WatchlistEntry] = Field(default_factory=list)
    theme_watchlist: list[WatchlistEntry] = Field(default_factory=list)
    aliases: dict[str, str] = Field(default_factory=dict)
    signals: dict[str, str] = Field(default_factory=dict)

    def watchlist_map(self) -> dict[str, WatchlistEntry]:
        return {entry.name: entry for entry in self.watchlist}

    def theme_watchlist_map(self) -> dict[str, WatchlistEntry]:
        return {entry.name: entry for entry in self.theme_watchlist}

    def normalize_slug(self, slug: str) -> str:
        return self.aliases.get(slug, slug)


def profiles_root() -> Path:
    return Path(__file__).resolve().parent


def _normalize_watchlist(data: dict[str, Any]) -> None:
    watchlist_raw = data.get("watchlist") or []
    entries: list[WatchlistEntry] = []
    for item in watchlist_raw:
        if not isinstance(item, dict):
            continue
        if "package" in item and "slug" not in item:
            item = {**item, "slug": item["package"]}
        entries.append(WatchlistEntry.model_validate(item))
    data["watchlist"] = entries

    theme_raw = data.get("theme_watchlist") or []
    theme_entries: list[WatchlistEntry] = []
    for item in theme_raw:
        if not isinstance(item, dict):
            continue
        if "package" in item and "slug" not in item:
            item = {**item, "slug": item["package"]}
        theme_entries.append(WatchlistEntry.model_validate(item))
    data["theme_watchlist"] = theme_entries


@lru_cache(maxsize=8)
def load_framework_profile(framework: str) -> FrameworkProfile | None:
    """Load ``profiles/{framework}/extensions.yaml`` if present."""
    path = profiles_root() / framework / "extensions.yaml"
    if not path.is_file():
        generic = profiles_root() / "generic" / "extensions.yaml"
        if framework not in {"wordpress", "django", "laravel", "rails", "php"}:
            path = generic if generic.is_file() else None
        elif framework == "php":
            path = generic if generic.is_file() else path
        if path is None or not path.is_file():
            return None
    with path.open(encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh) or {}
    _normalize_watchlist(data)
    return FrameworkProfile.model_validate(data)
