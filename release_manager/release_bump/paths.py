from __future__ import annotations

from pathlib import Path

RELEASE_MANAGER_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = RELEASE_MANAGER_DIR.parent
MANIFEST_PATH = RELEASE_MANAGER_DIR / "version-bump-manifest.json"
ARCHIVE_DIR = RELEASE_MANAGER_DIR / ".version-bump-archive"
RELEASES_DIR = RELEASE_MANAGER_DIR / "releases"
JSONL_PATH = RELEASES_DIR / "release-history.jsonl"
RELEASE_LOG_PATH = RELEASES_DIR / "RELEASE.log"
