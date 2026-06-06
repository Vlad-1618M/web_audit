from __future__ import annotations

import json
from typing import Any
from pathlib import Path
from dataclasses import dataclass
from .paths import MANIFEST_PATH


@dataclass(frozen=True)
class VersionFileRule:
    path: str
    line_pattern: str
    line_replacement: str


@dataclass(frozen=True)
class Manifest:
    raw: dict[str, Any]
    mac_version_file: str
    mac_replace_files: tuple[str, ...]
    engine_version_rules: tuple[VersionFileRule, ...]
    engine_replace_files: tuple[str, ...]


def load_manifest(path: Path = MANIFEST_PATH) -> Manifest:
    data = json.loads(path.read_text(encoding="utf-8"))
    mac = data["mac"]
    engine = data["engine"]

    version_rules = tuple(
        VersionFileRule(
            path=item["path"],
            line_pattern=item["line_pattern"],
            line_replacement=item["line_replacement"],
        )
        for item in engine["version_files"]
    )

    return Manifest(
        raw=data,
        mac_version_file=mac["version_file"],
        mac_replace_files=tuple(mac["replace_in_files"]),
        engine_version_rules=version_rules,
        engine_replace_files=tuple(engine["replace_in_files"]),
    )
