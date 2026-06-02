"""Plain-English DNS card content for HTML reports."""

from __future__ import annotations

import re
from typing import Any

OutcomeTone = str

_DNS_META: dict[str, dict[str, str]] = {
    "spf": {
        "label": "SPF",
        "title": "Sender Policy Framework",
        "description": (
            "Tells receiving mail servers which hosts are allowed to send email "
            "using your domain name — helps prevent email spoofing."
        ),
    },
    "dmarc": {
        "label": "DMARC",
        "title": "Domain-based Message Authentication",
        "description": (
            "Builds on SPF (and DKIM) and tells providers what to do with "
            "messages that fail authentication — none, quarantine, or reject."
        ),
    },
    "caa": {
        "label": "CAA",
        "title": "Certificate Authority Authorization",
        "description": (
            "Optional DNS rule listing which certificate authorities (CAs) may "
            "issue TLS/HTTPS certificates for your domain."
        ),
    },
    "aaaa": {
        "label": "AAAA",
        "title": "IPv6 addresses",
        "description": (
            "DNS records that map your hostname to IPv6 addresses — the site may "
            "be reachable over modern IPv6 networks when these exist."
        ),
    },
    "dnssec": {
        "label": "DNSSEC",
        "title": "DNS Security Extensions",
        "description": (
            "Cryptographic signing of DNS responses — reduces DNS spoofing risk. "
            "Many sites operate without it; this is informational."
        ),
    },
    "a": {
        "label": "A",
        "title": "IPv4 addresses",
        "description": (
            "Maps your hostname to IPv4 addresses — where browsers and scanners "
            "connect for HTTPS."
        ),
    },
    "mx": {
        "label": "MX",
        "title": "Mail exchangers",
        "description": (
            "Mail servers that receive email for your domain — often reveals "
            "Google Workspace, Microsoft 365, or your host's mail stack."
        ),
    },
    "ns": {
        "label": "NS",
        "title": "Nameservers",
        "description": (
            "Authoritative DNS servers for your domain — shows who hosts DNS "
            "(registrar, Cloudflare, Route53, …)."
        ),
    },
    "asn": {
        "label": "ASN",
        "title": "Network / hosting (ASN)",
        "description": (
            "Autonomous System Number for the site's IP — identifies the network "
            "operator (Cloudflare, AWS, GoDaddy, …). Looked up via Team Cymru DNS."
        ),
    },
}


def _format_record_value(key: str, value: Any) -> str:
    if value is None or value == "" or value == []:
        return "(no record)"
    if key == "aaaa" and isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if key == "a" and isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if key == "mx" and isinstance(value, list):
        return " · ".join(str(item) for item in value)
    if key == "ns" and isinstance(value, list):
        return " · ".join(str(item) for item in value)
    if key == "asn" and isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(
                    f"AS{item.get('asn', '?')} ({item.get('registry', '').upper()}) "
                    f"— {item.get('ip', '')} {item.get('country', '')}"
                )
        return " · ".join(parts) if parts else "(no ASN data)"
    if key == "caa" and isinstance(value, list):
        return " · ".join(str(item) for item in value)
    return str(value)


def _interpret_spf(value: Any) -> tuple[OutcomeTone, str]:
    if not value:
        return "warn", "No SPF record — others may spoof email from your domain more easily."
    text = str(value).lower()
    if "~all" in text:
        tail = "Soft fail (~all) for unknown senders."
    elif "-all" in text:
        tail = "Hard fail (-all) for unknown senders — stronger."
    elif "?all" in text:
        tail = "Neutral (?all) — weak enforcement."
    else:
        tail = "Review the record with your mail administrator."
    return "good", f"Published — {tail}"


def _interpret_dmarc(value: Any) -> tuple[OutcomeTone, str]:
    if not value:
        return "warn", "No DMARC record — email authentication policy is not published."
    text = str(value).lower()
    policy = "unknown"
    match = re.search(r"\bp=(\w+)", text)
    if match:
        policy = match.group(1)
    if policy == "reject":
        return "good", "Published — strict policy (p=reject) blocks failing mail."
    if policy == "quarantine":
        return "good", "Published — failing mail is quarantined (p=quarantine)."
    if policy == "none":
        return "warn", "Published — monitoring only (p=none); failing mail is not blocked yet."
    return "good", "Published — review policy with your mail administrator."


def _interpret_caa(value: Any) -> tuple[OutcomeTone, str]:
    if not value or value == []:
        return "neutral", "Not set — any public CA may issue certificates (common)."
    count = len(value) if isinstance(value, list) else 1
    return "good", f"{count} rule(s) published — restricts which CAs may issue HTTPS certificates."


def _interpret_aaaa(value: Any) -> tuple[OutcomeTone, str]:
    if not value or value == []:
        return "neutral", "No IPv6 addresses published — IPv4 only is common."
    count = len(value) if isinstance(value, list) else 1
    return "neutral", f"{count} IPv6 address(es) published for this hostname."


def _interpret_dnssec(value: Any) -> tuple[OutcomeTone, str]:
    if value == "DNSKEY_PRESENT":
        return "good", "DNSKEY records found — DNS responses appear signed."
    return "neutral", "Unsigned — DNSSEC not detected (informational for most sites)."


def _interpret_a(value: Any) -> tuple[OutcomeTone, str]:
    if not value or value == []:
        return "warn", "No IPv4 A records — site may be IPv6-only or misconfigured."
    count = len(value) if isinstance(value, list) else 1
    return "good", f"{count} IPv4 address(es) published for this hostname."


def _interpret_mx(value: Any) -> tuple[OutcomeTone, str]:
    if not value or value == []:
        return "neutral", "No MX records — domain may not receive email directly."
    count = len(value) if isinstance(value, list) else 1
    return "good", f"{count} mail route(s) published — check they match your mail provider."


def _interpret_ns(value: Any) -> tuple[OutcomeTone, str]:
    if not value or value == []:
        return "warn", "No NS records returned — unusual for a live domain."
    count = len(value) if isinstance(value, list) else 1
    return "good", f"{count} authoritative nameserver(s) listed."


def _interpret_asn(value: Any) -> tuple[OutcomeTone, str]:
    if not value or value == []:
        return "neutral", "ASN could not be resolved for the site's IP addresses."
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return (
                "good",
                f"Hosted on AS{first.get('asn', '?')} ({first.get('registry', '').upper()}) "
                f"— network allocated {first.get('allocated', 'unknown')}.",
            )
    return "neutral", "ASN data available — see technical values."


_INTERPRETERS = {
    "spf": _interpret_spf,
    "dmarc": _interpret_dmarc,
    "caa": _interpret_caa,
    "a": _interpret_a,
    "aaaa": _interpret_aaaa,
    "mx": _interpret_mx,
    "ns": _interpret_ns,
    "asn": _interpret_asn,
    "dnssec": _interpret_dnssec,
}


def build_dns_card(key: str, value: Any) -> dict[str, str]:
    meta = _DNS_META[key]
    interpret = _INTERPRETERS[key]
    tone, summary = interpret(value)
    return {
        "key": key,
        "label": meta["label"],
        "title": meta["title"],
        "description": meta["description"],
        "value": _format_record_value(key, value),
        "summary": summary,
        "summary_tone": tone,
    }


def build_dns_cards(records: dict[str, Any]) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    for key in ("spf", "dmarc", "mx", "a", "aaaa", "ns", "asn", "caa", "dnssec"):
        if key not in records:
            continue
        cards.append(build_dns_card(key, records.get(key)))
    return cards


def build_whois_card(whois: dict[str, str]) -> dict[str, str] | None:
    if not whois or not whois.get("registrar"):
        return None
    expiry = whois.get("registry_expiry", "")
    summary = f"Registrar: {whois['registrar']}"
    if expiry:
        summary += f" · registry expiry {expiry}"
    tone: OutcomeTone = "good" if whois.get("registrar") else "neutral"
    return {
        "key": "whois",
        "label": "WHOIS",
        "title": "Domain registration",
        "description": (
            "Public registration data for the domain name — from the ``whois`` "
            "command on the audit host when available."
        ),
        "value": whois.get("registrant_org") or whois.get("registrar") or "(see registrar)",
        "summary": summary,
        "summary_tone": tone,
    }


def format_net_tools(net_tools: dict[str, bool]) -> str:
    if not net_tools:
        return ""
    available = [name for name, ok in sorted(net_tools.items()) if ok]
    missing = [name for name, ok in sorted(net_tools.items()) if not ok]
    parts = []
    if available:
        parts.append(f"available on audit host: {', '.join(available)}")
    if missing:
        parts.append(f"not installed: {', '.join(missing)}")
    return " · ".join(parts)
