"""Well-known artifacts analyzer — robots, security.txt, sitemap (v1 ``check_artifacts()`` parity).

What: ``analyze_artifacts()`` parses collector output and emits ARTIFACTS findings.
Where: Called from ``pipeline._step_artifacts``; may cross-check OPEN paths from paths artifact.
How: Pure parsing — no HTTP. Robots Disallow vs probed OPEN paths → VERIFY conflicts.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone

from webaudit.collectors.artifacts import ArtifactsProbeResult
from webaudit.collectors.path_lists import PUBLIC_BY_DESIGN
from webaudit.config.settings import ArtifactsCollectorSettings
from webaudit.models.finding import Finding, FindingClass, Severity

_LOC_RE = re.compile(r"<loc[^>]*>([^<]+)</loc>", re.IGNORECASE)


def parse_robots_txt(body: str) -> tuple[list[str], list[str], list[str]]:
    disallow: list[str] = []
    allow: list[str] = []
    sitemaps: list[str] = []
    for line in body.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("disallow:"):
            val = line.split(":", 1)[1].strip()
            if val:
                disallow.append(val)
        elif lower.startswith("allow:"):
            val = line.split(":", 1)[1].strip()
            if val:
                allow.append(val)
        elif lower.startswith("sitemap:"):
            val = line.split(":", 1)[1].strip()
            if val:
                sitemaps.append(val)
    return disallow, allow, sitemaps


def robots_path_disallowed(path: str, disallow: list[str], allow: list[str]) -> bool:
    for rule in disallow:
        if not rule or rule == "/":
            continue
        if path == rule or path.startswith(rule):
            if any(path.startswith(a) for a in allow):
                return False
            return True
    return False


def parse_security_txt_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        fields[key.strip().lower()] = val.strip()
    return fields


def parse_sitemap_locs(body: str, *, limit: int = 150) -> list[str]:
    return [m.group(1).strip() for m in _LOC_RE.finditer(body)][:limit]


def _parse_expires_days(expires: str) -> int | None:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            parsed = datetime.strptime(expires.replace("Z", "+0000"), fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return (parsed.date() - date.today()).days
        except ValueError:
            continue
    return None


def _is_expected_open_path(path: str) -> bool:
    return path in PUBLIC_BY_DESIGN or path.endswith("/login/")


def analyze_artifacts(
    probe: ArtifactsProbeResult,
    settings: ArtifactsCollectorSettings,
    *,
    open_paths: list[dict[str, str | int | None]] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    open_paths = open_paths or []

    if settings.check_robots:
        if probe.robots.status_code == 200 and probe.robots.raw:
            disallow, allow, sitemaps = parse_robots_txt(probe.robots.raw)
            findings.append(
                Finding.from_check(
                    category="ARTIFACTS",
                    item="robots.txt",
                    status="PRESENT",
                    severity=Severity.OK,
                    detail=(
                        f"Parsed {len(disallow)} Disallow, {len(allow)} Allow, "
                        f"{len(sitemaps)} Sitemap rule(s)"
                    ),
                    evidence={"disallow": disallow, "allow": allow, "sitemaps": sitemaps},
                )
            )
            conflicts = 0
            for entry in open_paths:
                if entry.get("note") != "OPEN":
                    continue
                path = str(entry.get("path", ""))
                if not robots_path_disallowed(path, disallow, allow):
                    continue
                if _is_expected_open_path(path):
                    continue
                conflicts += 1
                findings.append(
                    Finding.from_check(
                        category="ARTIFACTS",
                        item=f"robots vs probe {path}",
                        status="CONFLICT",
                        severity=Severity.MEDIUM,
                        detail=(
                            "Path returns 200 but is Disallow'd in robots.txt — "
                            "crawlers may still find it; consider 401/403 or robots update"
                        ),
                        class_=FindingClass.VERIFY,
                        scored=False,
                        evidence={"path": path},
                    )
                )
            if conflicts == 0 and disallow:
                findings.append(
                    Finding.from_check(
                        category="ARTIFACTS",
                        item="robots.txt cross-check",
                        status="OK",
                        severity=Severity.OK,
                        detail="No probed OPEN paths conflict with Disallow rules",
                    )
                )
        elif probe.robots.status_code is not None:
            findings.append(
                Finding.from_check(
                    category="ARTIFACTS",
                    item="robots.txt",
                    status="MISSING",
                    severity=Severity.INFO,
                    detail=f"robots.txt returned {probe.robots.status_code}",
                    class_=FindingClass.INFO,
                    scored=False,
                )
            )

    if settings.check_security_txt and probe.security_txt.present:
        fields = parse_security_txt_fields(probe.security_txt.body)
        expires = fields.get("expires")
        contact = fields.get("contact")
        summary = (
            f"Expires: {expires or 'n/a'}; Contact: {contact or 'n/a'}; "
            f"Policy: {fields.get('policy', 'n/a')}; Canonical: {fields.get('canonical', 'n/a')}"
        )
        findings.append(
            Finding.from_check(
                category="ARTIFACTS",
                item="security.txt parse",
                status="PARSED",
                severity=Severity.OK,
                detail="security.txt fields extracted (see report artifacts section)",
                evidence={"summary": summary, "fields": fields},
            )
        )
        if expires:
            days_left = _parse_expires_days(expires)
            if days_left is not None:
                if days_left < 0:
                    findings.append(
                        Finding.from_check(
                            category="ARTIFACTS",
                            item="security.txt Expires",
                            status="STALE",
                            severity=Severity.MEDIUM,
                            detail=f"security.txt Expires date is in the past ({expires})",
                            class_=FindingClass.ACTION,
                            scored=True,
                            evidence={"expires": expires, "days_left": days_left},
                        )
                    )
                elif days_left < 30:
                    findings.append(
                        Finding.from_check(
                            category="ARTIFACTS",
                            item="security.txt Expires",
                            status="EXPIRING",
                            severity=Severity.LOW,
                            detail=f"security.txt expires in {days_left}d ({expires})",
                            class_=FindingClass.INFO,
                            scored=False,
                            evidence={"expires": expires, "days_left": days_left},
                        )
                    )
                else:
                    findings.append(
                        Finding.from_check(
                            category="ARTIFACTS",
                            item="security.txt Expires",
                            status="OK",
                            severity=Severity.OK,
                            detail=f"Valid until {expires} (~{days_left}d)",
                            evidence={"expires": expires, "days_left": days_left},
                        )
                    )
        if not contact:
            findings.append(
                Finding.from_check(
                    category="ARTIFACTS",
                    item="security.txt Contact",
                    status="MISSING",
                    severity=Severity.LOW,
                    detail="No Contact: field in security.txt",
                    class_=FindingClass.INFO,
                    scored=False,
                )
            )

    if settings.check_sitemap and probe.sitemap.status_code == 200 and probe.sitemap.raw:
        locs = parse_sitemap_locs(probe.sitemap.raw, limit=settings.max_sitemap_urls)
        findings.append(
            Finding.from_check(
                category="ARTIFACTS",
                item="sitemap.xml",
                status="PARSED",
                severity=Severity.OK,
                detail=f"Parsed {len(locs)} URL(s) from sitemap.xml",
                evidence={"locations": locs},
            )
        )

    return findings
