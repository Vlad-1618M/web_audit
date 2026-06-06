from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .paths import ARCHIVE_DIR, REPO_ROOT


def new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid4().hex[:8]}"


def archive_run_dir(run_id: str) -> Path:
    return ARCHIVE_DIR / run_id


def snapshot_files(run_id: str, rel_paths: list[str]) -> None:
    dest_root = archive_run_dir(run_id)
    dest_root.mkdir(parents=True, exist_ok=True)
    for rel in rel_paths:
        src = REPO_ROOT / rel
        if not src.is_file():
            continue
        dest = dest_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def restore_from_archive(run_id: str, rel_paths: list[str] | None = None) -> list[str]:
    src_root = archive_run_dir(run_id)
    if not src_root.is_dir():
        raise FileNotFoundError(f"No archive for run_id: {run_id}")

    restored: list[str] = []
    if rel_paths is None:
        for path in sorted(src_root.rglob("*")):
            if path.is_file():
                rel = path.relative_to(src_root).as_posix()
                dest = REPO_ROOT / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
                restored.append(rel)
        return restored

    for rel in rel_paths:
        src = src_root / rel
        if not src.is_file():
            continue
        dest = REPO_ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        restored.append(rel)
    return restored
