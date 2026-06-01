"""DNS hygiene analyzer — email/auth and informational DNS signals.

What: ``analyze_dns()`` maps ``DnsProbeResult`` to ``Finding`` list (category DNS).
Where: Called from ``orchestrator`` after ``collect_dns()`` when DNS collector is enabled.
How: Scoring policy per ``docs/scoring.md`` — DMARC/SPF missing are ACTION; DNSSEC/AAAA/CAA are INFO.
"""

from __future__ import annotations

from webaudit.collectors.dns import DnsProbeResult
from webaudit.config.settings import DnsCollectorSettings
from webaudit.models.finding import Finding, FindingClass, Severity


def analyze_dns(probe: DnsProbeResult, settings: DnsCollectorSettings) -> list[Finding]:
    findings: list[Finding] = []
    records = probe.records

    if settings.check_spf:
        spf = records.get("spf")
        if spf:
            findings.append(
                Finding.from_check(
                    category="DNS",
                    item="SPF",
                    status="PRESENT",
                    severity=Severity.OK,
                    detail=spf[:120],
                    evidence={"record": spf},
                )
            )
        else:
            findings.append(
                Finding.from_check(
                    category="DNS",
                    item="SPF",
                    status="MISSING",
                    severity=Severity.LOW,
                    detail="No SPF TXT record at apex domain",
                    class_=FindingClass.ACTION,
                )
            )

    if settings.check_dmarc:
        dmarc = records.get("dmarc")
        if dmarc:
            findings.append(
                Finding.from_check(
                    category="DNS",
                    item="DMARC",
                    status="PRESENT",
                    severity=Severity.OK,
                    detail=dmarc[:120],
                    evidence={"record": dmarc},
                )
            )
        else:
            findings.append(
                Finding.from_check(
                    category="DNS",
                    item="DMARC",
                    status="MISSING",
                    severity=Severity.MEDIUM,
                    detail="No DMARC record at _dmarc.<domain>",
                    class_=FindingClass.ACTION,
                )
            )

    if settings.check_dnssec:
        dnssec = records.get("dnssec")
        if dnssec == "DNSKEY_PRESENT":
            findings.append(
                Finding.from_check(
                    category="DNS",
                    item="DNSSEC",
                    status="PRESENT",
                    severity=Severity.OK,
                    detail="DNSKEY records found for registrable domain",
                )
            )
        else:
            findings.append(
                Finding.from_check(
                    category="DNS",
                    item="DNSSEC",
                    status="UNSIGNED",
                    severity=Severity.INFO,
                    detail="No DNSKEY records detected (informational)",
                    class_=FindingClass.INFO,
                    scored=False,
                )
            )

    if settings.check_caa:
        caa = records.get("caa") or []
        if caa:
            findings.append(
                Finding.from_check(
                    category="DNS",
                    item="CAA",
                    status="PRESENT",
                    severity=Severity.INFO,
                    detail=f"{len(caa)} CAA record(s)",
                    class_=FindingClass.INFO,
                    scored=False,
                    evidence={"records": caa},
                )
            )
        else:
            findings.append(
                Finding.from_check(
                    category="DNS",
                    item="CAA",
                    status="MISSING",
                    severity=Severity.INFO,
                    detail="No CAA records (informational)",
                    class_=FindingClass.INFO,
                    scored=False,
                )
            )

    if settings.check_aaaa:
        aaaa = records.get("aaaa") or []
        if aaaa:
            findings.append(
                Finding.from_check(
                    category="DNS",
                    item="AAAA",
                    status="PRESENT",
                    severity=Severity.INFO,
                    detail=f"{len(aaaa)} AAAA record(s) for hostname",
                    class_=FindingClass.INFO,
                    scored=False,
                    evidence={"records": aaaa},
                )
            )
        else:
            findings.append(
                Finding.from_check(
                    category="DNS",
                    item="AAAA",
                    status="NOT_PUBLISHED",
                    severity=Severity.INFO,
                    detail="No AAAA records for hostname (informational)",
                    class_=FindingClass.INFO,
                    scored=False,
                )
            )

    return findings
