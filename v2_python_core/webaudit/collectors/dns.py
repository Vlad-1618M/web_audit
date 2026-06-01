"""DNS record collector — SPF, DMARC, CAA, AAAA, DNSSEC.

What: ``collect_dns()`` queries the registrable domain and hostname via dnspython.
Where: Called from ``orchestrator`` when ``collectors.dns.enabled``; stored in ``artifacts.dns``.
How: Driven by ``DnsCollectorSettings`` flags; returns ``DnsProbeResult`` for ``analyzers/dns.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import dns.exception
import dns.resolver
import tldextract


@dataclass
class DnsProbeResult:
    domain: str
    records: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    def to_artifact(self) -> dict[str, Any]:
        return {"domain": self.domain, "records": self.records, "errors": self.errors}


def _registrable_domain(hostname: str) -> str:
    ext = tldextract.extract(hostname)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    return hostname


def _txt_records(resolver: dns.resolver.Resolver, name: str) -> list[str]:
    answers = resolver.resolve(name, "TXT")
    out: list[str] = []
    for rdata in answers:
        parts = [p.decode() if isinstance(p, bytes) else str(p) for p in rdata.strings]
        out.append("".join(parts))
    return out


def _query(resolver: dns.resolver.Resolver, name: str, rdtype: str) -> list[str]:
    answers = resolver.resolve(name, rdtype)
    return [rdata.to_text() for rdata in answers]


def collect_dns(
    target_url: str,
    *,
    timeout_seconds: int,
    check_spf: bool = True,
    check_dmarc: bool = True,
    check_caa: bool = True,
    check_dnssec: bool = True,
    check_aaaa: bool = True,
) -> DnsProbeResult:
    from urllib.parse import urlparse

    host = urlparse(target_url).hostname or target_url
    domain = _registrable_domain(host)

    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout_seconds
    resolver.lifetime = timeout_seconds

    result = DnsProbeResult(domain=domain)

    if check_spf:
        try:
            txts = _txt_records(resolver, domain)
            spf = [t for t in txts if t.lower().startswith("v=spf1")]
            result.records["spf"] = spf[0] if spf else None
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout) as exc:
            result.records["spf"] = None
            result.errors["spf"] = type(exc).__name__
        except dns.exception.DNSException as exc:
            result.errors["spf"] = str(exc)

    if check_dmarc:
        dmarc_name = f"_dmarc.{domain}"
        try:
            txts = _txt_records(resolver, dmarc_name)
            dmarc = [t for t in txts if t.lower().startswith("v=dmarc1")]
            result.records["dmarc"] = dmarc[0] if dmarc else None
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
            result.records["dmarc"] = None
        except dns.exception.DNSException as exc:
            result.errors["dmarc"] = str(exc)

    if check_caa:
        try:
            result.records["caa"] = _query(resolver, domain, "CAA")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
            result.records["caa"] = []
        except dns.exception.DNSException as exc:
            result.errors["caa"] = str(exc)

    if check_aaaa:
        try:
            result.records["aaaa"] = _query(resolver, host, "AAAA")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
            result.records["aaaa"] = []
        except dns.exception.DNSException as exc:
            result.errors["aaaa"] = str(exc)

    if check_dnssec:
        try:
            _query(resolver, domain, "DNSKEY")
            result.records["dnssec"] = "DNSKEY_PRESENT"
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
            result.records["dnssec"] = "UNSIGNED"
        except dns.exception.DNSException as exc:
            result.errors["dnssec"] = str(exc)

    return result
