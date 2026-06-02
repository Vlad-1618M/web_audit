"""Path probe analyzer — sensitive exposure and verify-only open paths (v1 parity).

What: ``analyze_paths()`` turns ``PathsProbeResult`` into PATHS findings for scoring.
Where: Called from ``pipeline._step_paths`` after ``collect_paths()``.
How: Sensitive + OPEN/SERVER_ERROR → ACTION (Exposure); expected/login → EXPECTED; other 200s → VERIFY.
"""

from __future__ import annotations

from webaudit.collectors.path_lists import CRITICAL_PATHS, PUBLIC_BY_DESIGN, SENSITIVE_PATHS
from webaudit.collectors.paths import PathsProbeResult
from webaudit.config.settings import PathsSettings
from webaudit.models.finding import Finding, FindingClass, Severity

_EXPOSURE_NOTES = frozenset({"OPEN", "SERVER_ERROR"})


def _is_login_surface(path: str, framework: str) -> bool:
    if path in {"/login/", "/administrator/"}:
        return True
    match path:
        case "/admin" | "/admin/":
            return framework == "django"
        case "/wp-login.php" | "/wp-admin" | "/wp-admin/":
            return framework == "wordpress"
        case "/login":
            return framework == "laravel"
        case "/users/sign_in":
            return framework == "rails"
    return False


def _is_expected_open(path: str, framework: str, paths_settings: PathsSettings) -> bool:
    if path in PUBLIC_BY_DESIGN:
        return True
    if path in paths_settings.expected_open:
        return True
    return _is_login_surface(path, framework)


def _is_scored_exposure(path: str, note: str) -> bool:
    return note in _EXPOSURE_NOTES and path in SENSITIVE_PATHS


def _severity_for_sensitive(path: str) -> Severity:
    if path in CRITICAL_PATHS:
        return Severity.CRITICAL
    return Severity.HIGH


def _display_item(path: str) -> str:
    return path.lstrip("/") or path


def analyze_paths(
    probe: PathsProbeResult,
    *,
    framework: str,
    paths_settings: PathsSettings,
) -> list[Finding]:
    findings: list[Finding] = []

    for entry in probe.probes:
        path = entry.path
        note = entry.note
        item = _display_item(path)
        evidence = {
            "path": path,
            "raw_status": entry.raw_status,
            "final_status": entry.final_status,
            "note": note,
        }

        if _is_scored_exposure(path, note):
            status = "OPEN" if note == "OPEN" else "LEAKING"
            findings.append(
                Finding.from_check(
                    category="PATHS",
                    item=item,
                    status=status,
                    severity=_severity_for_sensitive(path),
                    detail=(
                        f"Sensitive path reachable — raw {entry.raw_status} → "
                        f"final {entry.final_status} ({note})"
                    ),
                    class_=FindingClass.ACTION,
                    scored=True,
                    evidence=evidence,
                )
            )
            continue

        if note not in _EXPOSURE_NOTES:
            continue

        if _is_expected_open(path, framework, paths_settings):
            label = "login surface" if _is_login_surface(path, framework) else "expected open"
            findings.append(
                Finding.from_check(
                    category="PATHS",
                    item=item,
                    status="OPEN",
                    severity=Severity.INFO,
                    detail=f"{label} — final {entry.final_status}",
                    class_=FindingClass.EXPECTED,
                    scored=False,
                    evidence=evidence,
                )
            )
            continue

        findings.append(
            Finding.from_check(
                category="PATHS",
                item=item,
                status="OPEN",
                severity=Severity.MEDIUM,
                detail=(
                    f"Unexpected open path — raw {entry.raw_status} → "
                    f"final {entry.final_status}; verify public access is intended"
                ),
                class_=FindingClass.VERIFY,
                scored=False,
                evidence=evidence,
            )
        )

    return findings
