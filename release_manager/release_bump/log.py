from __future__ import annotations

import os
import json
import socket
import platform
from typing import Any
from pathlib import Path
from datetime import datetime, timezone
from .paths import JSONL_PATH, RELEASE_LOG_PATH, RELEASES_DIR


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _operator() -> str:
    return os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"


def _host() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return "unknown"


def append_event(event: dict[str, Any]) -> None:
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    event.setdefault("timestamp", _now_iso())
    event.setdefault("operator", _operator())
    event.setdefault("host", _host())
    event.setdefault("arch", platform.machine())

    line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    with JSONL_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

    summary = (
        f"{event['timestamp']}  {event.get('status', 'event')}  "
        f"mode={event.get('mode', '?')}  run_id={event.get('run_id', '?')}")
    
    if event.get("dry_run"):
        summary += "  dry_run"
    if event.get("mac"):
        summary += f"  mac={event['mac'].get('from')}->{event['mac'].get('to')}"
    if event.get("engine"):
        summary += f"  engine={event['engine'].get('from')}->{event['engine'].get('to')}"
    with RELEASE_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(summary + "\n")


def tail_jsonl(n: int) -> list[dict[str, Any]]:
    if not JSONL_PATH.is_file():
        return []
    lines = JSONL_PATH.read_text(encoding="utf-8").splitlines()
    out: list[dict[str, Any]] = []
    for line in lines[-n:]:
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def find_run_files(run_id: str) -> list[str] | None:
    for entry in reversed(tail_jsonl(500)):
        if entry.get("run_id") == run_id and entry.get("files_touched"):
            return list(entry["files_touched"])
    return None
