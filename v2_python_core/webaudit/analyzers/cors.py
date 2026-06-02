"""CORS analyzer — wildcard and origin reflection (v1 ``check_cors()`` parity).

What: ``analyze_cors()`` classifies ``Access-Control-Allow-Origin`` probe responses.
Where: Called from ``pipeline._step_cors`` after ``collect_cors()``.
How: WILDCARD → ACTION HIGH; reflected probe origin → CRITICAL; else INFO if ACAO present.
"""

from __future__ import annotations

from webaudit.collectors.cors import CorsProbeEntry, CorsProbeResult
from webaudit.config.settings import CorsCollectorSettings
from webaudit.models.finding import Finding, FindingClass, Severity


def analyze_cors(probe: CorsProbeResult, settings: CorsCollectorSettings) -> list[Finding]:
    if not settings.enabled:
        return []

    findings: list[Finding] = []
    has_acao = False

    for entry in probe.probes:
        finding = _entry_finding(entry, probe.origin_sent)
        if finding:
            findings.append(finding)
            if entry.acao:
                has_acao = True

    if not has_acao:
        findings.append(
            Finding.from_check(
                category="CORS",
                item="API paths",
                status="NONE",
                severity=Severity.OK,
                detail="No Access-Control-Allow-Origin on probed API paths",
            )
        )

    return findings


def _entry_finding(entry: CorsProbeEntry, probe_origin: str) -> Finding | None:
    acao = entry.acao
    if not acao:
        return None

    path = entry.path
    evidence = {"path": path, "acao": acao, "acac": entry.acac}

    if "*" in acao:
        return Finding.from_check(
            category="CORS",
            item=path,
            status="WILDCARD",
            severity=Severity.HIGH,
            detail=f"Access-Control-Allow-Origin: * on {path}",
            class_=FindingClass.ACTION,
            scored=True,
            evidence=evidence,
        )

    origin_host = probe_origin.replace("https://", "").replace("http://", "").split("/")[0]
    if origin_host.lower() in acao.lower():
        return Finding.from_check(
            category="CORS",
            item=path,
            status="REFLECTED",
            severity=Severity.CRITICAL,
            detail=f"Origin reflected in ACAO on {path} — credentialed CORS risk if cookies used",
            class_=FindingClass.ACTION,
            scored=True,
            evidence=evidence,
        )

    return Finding.from_check(
        category="CORS",
        item=path,
        status="OPEN",
        severity=Severity.INFO,
        detail=f"CORS headers present: {acao[:80]}",
        class_=FindingClass.INFO,
        scored=False,
        evidence=evidence,
    )
