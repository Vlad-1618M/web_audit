"""ASN lookup via Team Cymru DNS — no dig/whois binary required."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Any

import dns.exception
import dns.resolver


@dataclass
class AsnRecord:
    ip: str
    asn: str
    prefix: str
    country: str
    registry: str
    allocated: str

    def to_dict(self) -> dict[str, str]:
        return {
            "ip": self.ip,
            "asn": self.asn,
            "prefix": self.prefix,
            "country": self.country,
            "registry": self.registry,
            "allocated": self.allocated,
        }


def _cymru_query_name(ip: str) -> str:
    addr = ipaddress.ip_address(ip)
    if addr.version == 4:
        parts = str(ip).split(".")
        return f"{parts[3]}.{parts[2]}.{parts[1]}.{parts[0]}.origin.asn.cymru.com"
    expanded = addr.exploded.replace(":", "")
    nibbles = ".".join(reversed(expanded))
    return f"{nibbles}.origin6.asn.cymru.com"


def lookup_asn(
    ip: str,
    resolver: dns.resolver.Resolver,
) -> AsnRecord | None:
    try:
        answers = resolver.resolve(_cymru_query_name(ip), "TXT")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout, dns.exception.DNSException):
        return None

    for rdata in answers:
        parts = [p.decode() if isinstance(p, bytes) else str(p) for p in rdata.strings]
        text = "".join(parts).strip('"')
        fields = [field.strip() for field in text.split("|")]
        if len(fields) < 6:
            continue
        asn_num, ip_field, prefix, country, registry, allocated = fields[:6]
        return AsnRecord(
            ip=ip_field or ip,
            asn=asn_num,
            prefix=prefix,
            country=country,
            registry=registry,
            allocated=allocated,
        )
    return None


def lookup_asns_for_ips(
    ips: list[str],
    resolver: dns.resolver.Resolver,
    *,
    limit: int = 4,
) -> list[dict[str, Any]]:
    seen_asn: set[str] = set()
    results: list[dict[str, Any]] = []
    for ip in ips:
        if len(results) >= limit:
            break
        record = lookup_asn(ip, resolver)
        if record is None or record.asn in seen_asn:
            continue
        seen_asn.add(record.asn)
        results.append(record.to_dict())
    return results
