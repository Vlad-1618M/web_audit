"""Host system facts and report footer branding (v1 ``system_info_txt`` parity)."""

from __future__ import annotations

import platform
import socket
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from webaudit import __version__

BRAND_APP = "https://muzar.io/"
BRAND_APP_LABEL = "muzar.io"
BRAND_PRODUCT = "Web Security Audit Pro"


def collect_system_info() -> dict[str, str]:
    uname = platform.uname()
    try:
        host = socket.gethostname().split(".")[0]
    except OSError:
        host = "unknown"
    shell = "unknown"
    import os

    shell_path = os.environ.get("SHELL", "")
    if shell_path:
        shell = f"{shell_path.rsplit('/', 1)[-1]}"
    return {
        "audit_host": host,
        "architecture": uname.machine or "unknown",
        "os_pretty": platform.platform(),
        "kernel": uname.release or "unknown",
        "system": " ".join(filter(None, [uname.system, uname.release, uname.version])),
        "shell": shell,
        "python": platform.python_version(),
    }


def format_report_timestamp(iso_ts: str | None = None) -> str:
    """Human-readable local timestamp, e.g. Tue Jun 2 09:52:48 CDT 2026."""
    if iso_ts:
        try:
            dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    local = dt.astimezone()
    tz = local.strftime("%Z") or local.tzname() or "UTC"
    return local.strftime(f"%a %b {local.day} %H:%M:%S {tz} %Y")


def build_report_footer(*, scanned_at: str | None = None) -> dict[str, str]:
    sysinfo = collect_system_info()
    when = format_report_timestamp(scanned_at)
    return {
        **sysinfo,
        "report_timestamp": when,
        "webaudit_version": __version__,
        "brand_app": BRAND_APP,
        "brand_app_label": BRAND_APP_LABEL,
        "brand_product": BRAND_PRODUCT,
        "brand_line": (
            f"Created by {BRAND_APP_LABEL} — {BRAND_PRODUCT} v{__version__} — {when}"
        ),
    }
