"""TLS certificate helpers — issuer display, hostname validation, status labels."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

_KNOWN_CAS: tuple[tuple[str, str], ...] = (
    ("let's encrypt", "Let's Encrypt"),
    ("lets encrypt", "Let's Encrypt"),
    ("digicert", "DigiCert"),
    ("google trust services", "Google Trust Services"),
    ("cloudflare", "Cloudflare"),
    ("amazon", "Amazon (ACM)"),
    ("sectigo", "Sectigo"),
    ("globalsign", "GlobalSign"),
    ("go daddy", "GoDaddy"),
    ("godaddy", "GoDaddy"),
    ("hashicorp", "HashiCorp"),
    ("zerossl", "ZeroSSL"),
    ("identrust", "Identrust"),
    ("microsoft", "Microsoft Azure TLS"),
    ("comodo", "Sectigo / Comodo"),
    ("rapidssl", "RapidSSL"),
    ("certainly", "Certainly (Automattic)"),
)


def rfc4514_attr(rfc4514: str, key: str) -> str | None:
    """Extract a single attribute from an RFC4514 DN string."""
    if not rfc4514:
        return None
    pattern = rf"(?:^|,\s*){re.escape(key)}=([^,]+)"
    match = re.search(pattern, rfc4514, re.IGNORECASE)
    return match.group(1).strip() if match else None


def issuer_display_name(*, issuer: str, issuer_org: str | None, issuer_cn: str | None) -> str:
    blob = " ".join(part for part in (issuer_org, issuer_cn, issuer) if part).lower()
    for needle, label in _KNOWN_CAS:
        if needle in blob:
            if issuer_cn and issuer_cn not in label and len(issuer_cn) < 24:
                return f"{label} ({issuer_cn})"
            return label
    if issuer_org:
        return issuer_org
    if issuer_cn:
        return issuer_cn
    return issuer[:100] if issuer else "Unknown certificate authority"


def subject_common_name(subject: str | None) -> str | None:
    return rfc4514_attr(subject or "", "CN")


def _hostname_matches(host: str, pattern: str) -> bool:
    host = host.lower().rstrip(".")
    pattern = pattern.lower().rstrip(".")
    if pattern.startswith("*."):
        suffix = pattern[1:]
        return host.endswith(suffix) and host != suffix.lstrip(".")
    return host == pattern


def validate_hostname(hostname: str, *, subject: str | None, san: list[str]) -> tuple[bool, str]:
    """Return whether the cert covers the scanned host and a short note."""
    host = hostname.lower().strip(".")
    if host.startswith("www."):
        bare = host[4:]
    else:
        bare = host

    candidates: list[str] = []
    cn = subject_common_name(subject)
    if cn:
        candidates.append(cn)
    candidates.extend(san)

    seen: set[str] = set()
    unique_candidates: list[str] = []
    for pattern in candidates:
        if not isinstance(pattern, str):
            continue
        key = pattern.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(pattern)
    candidates = unique_candidates

    if not candidates:
        return True, "No CN/SAN to compare — assumed OK"

    for pattern in candidates:
        if not isinstance(pattern, str):
            continue
        if _hostname_matches(host, pattern) or _hostname_matches(bare, pattern):
            return True, f"Covers {host}"

    preview = ", ".join(candidates[:4])
    if len(candidates) > 4:
        preview += f" (+{len(candidates) - 4} more)"
    return False, f"Certificate names ({preview}) do not include {host}"


def cert_lifecycle_status(days_left: int | None, *, warn_days: int = 30) -> str:
    if days_left is None:
        return "UNKNOWN"
    if days_left < 0:
        return "EXPIRED"
    if days_left <= warn_days:
        return "EXPIRING"
    return "VALID"


def format_cert_datetime(iso_value: str | None) -> str:
    if not iso_value:
        return "—"
    try:
        normalized = iso_value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%b %d, %Y %H:%M UTC")
    except ValueError:
        return iso_value[:19]


def format_days_left(days_left: int | None) -> str:
    if days_left is None:
        return "Unknown"
    if days_left < 0:
        return f"Expired {abs(days_left)} day(s) ago"
    if days_left == 0:
        return "Expires today"
    if days_left == 1:
        return "1 day left"
    return f"{days_left} days left"


def build_cert_issues(
    cert: dict[str, Any],
    *,
    tls_versions: list[dict[str, Any]] | None = None,
    warn_days: int = 30,
) -> list[str]:
    issues: list[str] = []
    if cert.get("error") and not cert.get("subject"):
        issues.append(f"Could not read certificate: {cert['error']}")
        return issues

    days_left = cert.get("days_left")
    if isinstance(days_left, int):
        if days_left < 0:
            issues.append(f"Certificate expired on {format_cert_datetime(cert.get('not_after'))}")
        elif days_left <= warn_days:
            issues.append(f"Certificate expires soon — {format_days_left(days_left)}")

    if cert.get("hostname_match") is False:
        issues.append(str(cert.get("hostname_note") or "Hostname does not match certificate names"))

    for entry in tls_versions or []:
        version = str(entry.get("version") or "")
        if entry.get("supported") and version in {"1.0", "1.1"}:
            issues.append(f"Deprecated TLS {version} is still accepted")

    return issues
