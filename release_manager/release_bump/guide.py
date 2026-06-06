from __future__ import annotations

from .paths import REPO_ROOT
from .versions import read_mac_version
from .manifest import Manifest


def print_release_guide(manifest: Manifest) -> None:
    mac = read_mac_version(manifest)
    tag = f"macos-v{mac}"
    dmg = f"WebAudit-{mac}-macOS.dmg"

    print(
        f"""
Web Audit — release guide (this repo)
=====================================

Mac app (current VERSION: {mac})
  1. Review changes:  git status && git diff
  2. Smoke DMG:       cd macos && ./orchestrate-macos.sh public-smoke
  3. Commit bumps:    git add -A && git commit -m "chore: bump Mac to {mac}"
  4. Tag (signed):    git tag -s {tag} -m "Web Audit for Mac {mac}"
  5. Push:            git push origin HEAD && git push origin {tag}
  6. Verify:          GitHub Releases → {dmg} + workflow "Release macOS app"

Engine (optional before Mac cut)
  1. Bump:          ./release_manager/bump-versions.sh --dry-run --engine <ver>
  2. CHANGELOG:     v2_python_core/CHANGELOG.md
  3. Tag:           git tag -s v<ver> -m "webaudit <ver>"
  4. Push tag:      git push origin v<ver>
  5. GHCR:          CI publishes ghcr.io/vlad-1618m/webaudit:<ver>

Docs
  - {REPO_ROOT / "VERSIONING_AND_TAGS.md"}
  - {REPO_ROOT / "DELIVERY_PATHS.md"}
  - release_manager/releases/release-history.jsonl
""".strip()
    )
