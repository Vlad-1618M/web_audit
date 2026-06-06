from __future__ import annotations

import re
from pathlib import Path

from .paths import REPO_ROOT
from .manifest import Manifest, VersionFileRule


def read_mac_version(manifest: Manifest) -> str:
    path = REPO_ROOT / manifest.mac_version_file
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Empty Mac version file: {path}")
    return text


def read_engine_version(manifest: Manifest) -> str:
    found: list[str] = []
    for rule in manifest.engine_version_rules:
        path = REPO_ROOT / rule.path
        content = path.read_text(encoding="utf-8")
        if path.name == "__version__.py":
            match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        else:
            match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if match:
            found.append(match.group(1))
    if not found:
        raise ValueError("Could not read engine version from manifest rules")
    unique = set(found)
    if len(unique) > 1:
        raise ValueError(f"Engine version mismatch across sources: {sorted(unique)}")
    return found[0]


def apply_line_rule(content: str, rule: VersionFileRule, old: str, new: str) -> tuple[str, int]:
    pattern = rule.line_pattern.format(old=old, new=new)
    replacement = rule.line_replacement.format(old=old, new=new)
    if pattern not in content:
        return content, 0
    return content.replace(pattern, replacement, 1), 1


def replace_version_literal(content: str, old: str, new: str) -> tuple[str, int]:
    if old == new or old not in content:
        return content, 0
    return content.replace(old, new), content.count(old)


def whole_file_version(content: str, new: str) -> str:
    return new.rstrip() + "\n"
