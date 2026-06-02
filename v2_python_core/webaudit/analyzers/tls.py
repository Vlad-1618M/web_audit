"""TLS analyzer — version policy and certificate expiry (v1 ``check_tls()`` parity).

What: ``analyze_tls()`` turns ``TlsProbeResult`` into TLS findings for Hygiene scoring.
Where: Called from ``pipeline._step_tls`` after ``collect_tls()``.
How: Deprecated 1.0/1.1 accepted → ACTION; cert expiry → EXPIRED/EXPIRING; good versions → INFO.
"""

from __future__ import annotations

from webaudit.collectors.tls import TlsProbeResult, TlsVersionResult
from webaudit.config.settings import TlsCollectorSettings
from webaudit.models.finding import Finding, FindingClass, Severity

_GOOD_VERSIONS = frozenset({"1.2", "1.3"})
_DEPRECATED_SEVERITY = {"1.0": Severity.HIGH, "1.1": Severity.MEDIUM}


def _version_finding(version: TlsVersionResult) -> Finding:
    label = f"TLS {version.version}"
    good = version.version in _GOOD_VERSIONS

    if version.supported:
        if good:
            return Finding.from_check(
                category="TLS",
                item=label,
                status="SUPPORTED",
                severity=Severity.OK,
                detail=f"TLS {version.version} handshake succeeded",
                evidence={"negotiated": version.negotiated},
            )
        return Finding.from_check(
            category="TLS",
            item=label,
            status="ACCEPTED",
            severity=_DEPRECATED_SEVERITY[version.version],
            detail=f"Deprecated TLS {version.version} accepted — should be disabled",
            class_=FindingClass.ACTION,
            scored=True,
            evidence={"negotiated": version.negotiated},
        )

    if not good:
        return Finding.from_check(
            category="TLS",
            item=label,
            status="REJECTED",
            severity=Severity.OK,
            detail=f"Deprecated TLS {version.version} correctly rejected",
            evidence={"error": version.error},
        )

    return Finding.from_check(
        category="TLS",
        item=label,
        status="UNAVAILABLE",
        severity=Severity.LOW,
        detail=f"TLS {version.version} handshake failed",
        class_=FindingClass.VERIFY,
        scored=False,
        evidence={"error": version.error},
    )


def analyze_tls(probe: TlsProbeResult, settings: TlsCollectorSettings) -> list[Finding]:
    if probe.skipped:
        return []

    findings: list[Finding] = []

    if settings.check_deprecated_versions:
        for version in probe.versions:
            findings.append(_version_finding(version))

    cert = probe.certificate
    if cert is None:
        return findings

    if cert.error and not cert.subject:
        findings.append(
            Finding.from_check(
                category="TLS",
                item="Certificate",
                status="UNAVAILABLE",
                severity=Severity.LOW,
                detail=f"Could not read certificate: {cert.error}",
                class_=FindingClass.VERIFY,
                scored=False,
            )
        )
        return findings

    if cert.subject:
        findings.append(
            Finding.from_check(
                category="TLS",
                item="Certificate subject",
                status="PRESENT",
                severity=Severity.OK,
                detail=cert.subject[:120],
                evidence={"subject": cert.subject},
            )
        )

    if cert.issuer:
        findings.append(
            Finding.from_check(
                category="TLS",
                item="Certificate issuer",
                status="PRESENT",
                severity=Severity.OK,
                detail=cert.issuer[:120],
                evidence={"issuer": cert.issuer},
            )
        )

    if cert.days_left is not None:
        if cert.days_left < 0:
            findings.append(
                Finding.from_check(
                    category="TLS",
                    item="Certificate expiry",
                    status="EXPIRED",
                    severity=Severity.CRITICAL,
                    detail=f"Certificate expired: {cert.not_after}",
                    class_=FindingClass.ACTION,
                    scored=True,
                    evidence={"not_after": cert.not_after, "days_left": cert.days_left},
                )
            )
        elif cert.days_left < settings.expiry_warn_days:
            findings.append(
                Finding.from_check(
                    category="TLS",
                    item="Certificate expiry",
                    status="EXPIRING",
                    severity=Severity.HIGH,
                    detail=f"Expires in {cert.days_left}d ({cert.not_after})",
                    class_=FindingClass.ACTION,
                    scored=True,
                    evidence={"not_after": cert.not_after, "days_left": cert.days_left},
                )
            )
        else:
            findings.append(
                Finding.from_check(
                    category="TLS",
                    item="Certificate expiry",
                    status="OK",
                    severity=Severity.OK,
                    detail=f"Valid ~{cert.days_left}d — expires {cert.not_after}",
                    evidence={"not_after": cert.not_after, "days_left": cert.days_left},
                )
            )
    elif cert.not_after:
        findings.append(
            Finding.from_check(
                category="TLS",
                item="Certificate expiry",
                status="PRESENT",
                severity=Severity.INFO,
                detail=cert.not_after,
                class_=FindingClass.INFO,
                scored=False,
            )
        )

    if settings.check_chain and cert.chain_length > 0:
        findings.append(
            Finding.from_check(
                category="TLS",
                item="Certificate chain",
                status="PRESENT",
                severity=Severity.INFO,
                detail=f"{cert.chain_length} certificate(s) in peer chain",
                class_=FindingClass.INFO,
                scored=False,
                evidence={"chain_length": cert.chain_length, "san": cert.san},
            )
        )

    return findings
