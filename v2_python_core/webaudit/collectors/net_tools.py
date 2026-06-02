"""Optional host network tools — detect dig/whois/mtr; enrich when available."""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any


def detect_net_tools() -> dict[str, bool]:
    return {
        tool: shutil.which(tool) is not None
        for tool in ("dig", "whois", "host", "mtr", "traceroute")
    }


def _run_command(args: list[str], *, timeout_seconds: int) -> str:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (completed.stdout or "") + (completed.stderr or "")


def optional_whois_domain(domain: str, *, timeout_seconds: int = 8) -> dict[str, str]:
    """Best-effort domain WHOIS when the ``whois`` binary exists on the audit host."""
    if not shutil.which("whois"):
        return {}
    output = _run_command(["whois", domain], timeout_seconds=timeout_seconds)
    if not output.strip():
        return {}

    summary: dict[str, str] = {"raw_excerpt": "\n".join(output.splitlines()[:12])}
    patterns = {
        "registrar": r"Registrar:\s*(.+)",
        "registrant_org": r"Registrant Organization:\s*(.+)",
        "creation_date": r"Creation Date:\s*(.+)",
        "registry_expiry": r"(?:Registry Expiry|Registrar Registration Expiration) Date:\s*(.+)",
        "name_servers": r"Name Server:\s*(.+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, output, re.I)
        if match:
            summary[key] = match.group(1).strip()
    return summary
