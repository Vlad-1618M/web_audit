"""Colored scan progress — verbosity levels for ``webaudit scan``."""

from __future__ import annotations

import re
from enum import IntEnum
from typing import Any

from rich.console import Console

from webaudit.config.settings import Settings
from webaudit.models.finding import Finding
from webaudit.models.run import AuditScores

STEP_LABELS: dict[str, tuple[str, str]] = {
    "_step_headers": ("headers", "HTTP security headers"),
    "_step_framework": ("framework", "Stack fingerprint"),
    "_step_dns": ("dns", "DNS records (SPF, DMARC, …)"),
    "_step_paths": ("paths", "Sensitive path probes"),
    "_step_tls": ("tls", "TLS versions and certificate"),
    "_step_policy": ("policy", "CSP / HSTS policy parse"),
    "_step_cookies": ("cookies", "Set-Cookie flags"),
    "_step_rate_limit": ("rate_limit", "Login rate-limit heuristics"),
    "_step_artifacts": ("artifacts", "robots.txt, security.txt, sitemap"),
    "_step_cors": ("cors", "CORS reflection probes"),
    "_step_html": ("html", "DOM inventory and mixed content"),
    "_step_extensions": ("extensions", "Framework extensions / packages"),
    "_step_seo_surface": ("seo_surface", "Discoverability (INFO only)"),
}


class Verbosity(IntEnum):
    QUIET = 0
    NORMAL = 1
    VERBOSE = 2


def resolve_verbosity(*, verbose: bool, quiet: bool) -> Verbosity:
    if verbose and quiet:
        raise ValueError("Use either --verbose (-v) or --quiet (-q), not both")
    if verbose:
        return Verbosity.VERBOSE
    if quiet:
        return Verbosity.QUIET
    return Verbosity.NORMAL


def step_enabled(step_name: str, settings: Settings) -> bool:
    match step_name:
        case "_step_headers":
            return True
        case "_step_framework":
            return settings.collectors.framework.enabled
        case "_step_dns":
            return settings.collectors.dns.enabled
        case "_step_paths":
            return settings.paths.enabled
        case "_step_tls":
            return settings.collectors.tls.enabled
        case "_step_policy":
            return settings.policy.enabled
        case "_step_cookies":
            return settings.collectors.cookies.enabled
        case "_step_rate_limit":
            return settings.collectors.rate_limit.enabled
        case "_step_artifacts":
            return settings.collectors.artifacts.enabled
        case "_step_cors":
            return settings.collectors.cors.enabled
        case "_step_html":
            return settings.collectors.html.enabled
        case "_step_extensions":
            return (
                settings.collectors.extensions.enabled
                and settings.target.framework in {"wordpress", "django", "laravel", "rails", "php"}
            )
        case "_step_seo_surface":
            return settings.collectors.seo_surface.enabled
    return True


def _finding_note(findings: list[Finding]) -> str:
    if not findings:
        return "0 findings"
    action = sum(1 for f in findings if f.class_.value == "ACTION")
    if action:
        return f"{len(findings)} findings · [yellow]{action} action[/yellow]"
    return f"{len(findings)} findings"


def summarize_step(
    step_name: str,
    findings: list[Finding],
    artifact_parts: dict[str, dict[str, Any]],
) -> tuple[str, list[str]]:
    """Return one-line summary and optional verbose detail lines."""
    note = _finding_note(findings)
    details: list[str] = []

    if step_name == "_step_headers":
        art = artifact_parts.get("headers", {})
        status = art.get("status_code", "?")
        count = len(art.get("headers") or {})
        summary = f"HTTP {status} · {count} headers · {note.replace('[yellow]', '').replace('[/yellow]', '')}"
        if art.get("final_url") and art.get("final_url") != art.get("target_url"):
            details.append(f"redirect → {art['final_url']}")
        for key in ("Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options"):
            if key in (art.get("headers") or {}):
                val = art["headers"][key]
                details.append(f"{key}: {val[:80]}{'…' if len(val) > 80 else ''}")
            else:
                details.append(f"{key}: [dim]missing[/dim]")

    elif step_name == "_step_framework":
        art = artifact_parts.get("inventory", {}).get("framework", {})
        fw = art.get("effective_framework", "unknown")
        conf = art.get("confidence", "—")
        summary = f"{fw} ({conf}) · {note.replace('[yellow]', '').replace('[/yellow]', '')}"
        if art.get("cdn"):
            details.append(f"CDN: {art['cdn']}")
        if art.get("signals") and art["signals"] != "no signals":
            details.append(f"signals: {art['signals'][:120]}")

    elif step_name == "_step_dns":
        art = artifact_parts.get("dns", {})
        records = art.get("records") or {}
        parts = []
        for key, label in (("spf", "SPF"), ("dmarc", "DMARC"), ("caa", "CAA"), ("aaaa", "AAAA")):
            val = records.get(key)
            parts.append(f"{label}: {'✓' if val else '—'}")
        summary = f"{' · '.join(parts)} · {note.replace('[yellow]', '').replace('[/yellow]', '')}"
        for key in ("spf", "dmarc"):
            val = records.get(key)
            if val:
                details.append(f"{key.upper()}: {str(val)[:100]}")

    elif step_name == "_step_paths":
        art = artifact_parts.get("inventory", {}).get("paths", {})
        count = art.get("probe_count", 0)
        open_paths = [
            p.get("path")
            for p in (art.get("paths") or [])
            if isinstance(p, dict) and p.get("note") in {"OPEN", "LEAKING"}
        ]
        summary = f"{count} probes · {note.replace('[yellow]', '').replace('[/yellow]', '')}"
        if open_paths:
            details.append(f"exposed: {', '.join(open_paths[:5])}")
        elif count:
            details.append("no sensitive paths openly readable")

    elif step_name == "_step_tls":
        art = artifact_parts.get("tls", {})
        cert = art.get("certificate") or {}
        versions = [
            v.get("version")
            for v in (art.get("versions") or [])
            if isinstance(v, dict) and v.get("supported")
        ]
        days = cert.get("days_left")
        issuer = cert.get("issuer_display") or cert.get("issuer") or "—"
        status = cert.get("status") or "—"
        days_part = f"~{days}d left" if days is not None else "expiry unknown"
        summary = (
            f"{issuer} · {status} · {days_part} · TLS {', '.join(versions) or '?'} · "
            f"{note.replace('[yellow]', '').replace('[/yellow]', '')}"
        )
        if cert.get("hostname_match") is False:
            details.append(f"hostname mismatch: {cert.get('hostname_note', '')[:100]}")
        if cert.get("not_after"):
            details.append(f"expires: {cert.get('not_after', '')[:40]}")

    elif step_name == "_step_policy":
        art = artifact_parts.get("policy", {})
        hsts = art.get("hsts_detail")
        csp = art.get("csp_detail")
        hsts_part = "—"
        if isinstance(hsts, str) and hsts:
            match = re.search(r"max-age=(\d+)", hsts, re.IGNORECASE)
            hsts_part = f"max-age={match.group(1)}" if match else "present"
        csp_part = "yes" if csp else "no"
        summary = (
            f"HSTS {hsts_part} · CSP {csp_part} · "
            f"{note.replace('[yellow]', '').replace('[/yellow]', '')}"
        )
        if isinstance(hsts, str) and hsts:
            details.append(hsts[:120])
        if isinstance(csp, str) and csp:
            details.append(csp[:120])

    elif step_name == "_step_cookies":
        art = artifact_parts.get("inventory", {}).get("cookies", {})
        count = len(art.get("cookies") or [])
        summary = f"{count} cookie(s) · {note.replace('[yellow]', '').replace('[/yellow]', '')}"

    elif step_name == "_step_rate_limit":
        art = artifact_parts.get("inventory", {}).get("rate_limit", {})
        summary = f"login probes done · {note.replace('[yellow]', '').replace('[/yellow]', '')}"
        get = art.get("get") or {}
        if get.get("limit_status"):
            details.append(f"GET burst limited at attempt {get.get('limited_at')} → HTTP {get['limit_status']}")

    elif step_name == "_step_artifacts":
        art = artifact_parts.get("inventory", {}).get("artifacts", {})
        flags = []
        if (art.get("robots") or {}).get("present"):
            flags.append("robots.txt")
        if (art.get("security_txt") or {}).get("present"):
            flags.append("security.txt")
        if (art.get("sitemap") or {}).get("present"):
            flags.append("sitemap")
        summary = f"{', '.join(flags) or 'no well-known files'} · {note.replace('[yellow]', '').replace('[/yellow]', '')}"

    elif step_name == "_step_cors":
        art = artifact_parts.get("inventory", {}).get("cors", {})
        probes = len(art.get("probes") or [])
        summary = f"{probes} origin probe(s) · {note.replace('[yellow]', '').replace('[/yellow]', '')}"

    elif step_name == "_step_html":
        art = artifact_parts.get("inventory", {}).get("html", {})
        inv = art.get("inventory") or {}
        summary = (
            f"{art.get('pages_scanned', 0)} page(s) · "
            f"{inv.get('link_count', 0)} links · {note.replace('[yellow]', '').replace('[/yellow]', '')}"
        )

    elif step_name == "_step_extensions":
        art = artifact_parts.get("extensions", {})
        count = art.get("extension_count", 0)
        unit = art.get("unit", "extension")
        fw = art.get("framework", "?")
        summary = f"{fw} · {count} {unit}(s) · {note.replace('[yellow]', '').replace('[/yellow]', '')}"
        for item in (art.get("extensions") or [])[:5]:
            if isinstance(item, dict):
                name = item.get("name", "?")
                ver = item.get("version") or "?"
                details.append(f"{name} v{ver}")
        for signal in (art.get("signals") or [])[:3]:
            if isinstance(signal, dict):
                details.append(f"signal: {signal.get('key')} ({signal.get('status')})")

    elif step_name == "_step_seo_surface":
        art = artifact_parts.get("seo_surface", {})
        checks = art.get("checks_run", 0)
        summary = f"{checks} check(s) · {note.replace('[yellow]', '').replace('[/yellow]', '')}"

    else:
        summary = note.replace("[yellow]", "").replace("[/yellow]", "")

    # Re-apply rich markup for finding note in summary if needed
    if findings and any(f.class_.value == "ACTION" for f in findings):
        base = summary.rsplit(" · ", 1)[0] if " · " in summary else summary
        summary = f"{base} · {_finding_note(findings)}"

    return summary, details


class ScanProgress:
    """Rich console progress for pipeline steps."""

    def __init__(self, console: Console, verbosity: Verbosity) -> None:
        self.console = console
        self.verbosity = verbosity

    def scan_start(self, target_url: str) -> None:
        if self.verbosity == Verbosity.QUIET:
            return
        self.console.print(f"[bold cyan]Scanning[/bold cyan] {target_url}")

    def step_skipped(self, label: str) -> None:
        if self.verbosity == Verbosity.VERBOSE:
            self.console.print(f"  [dim]⊘ {label:<12}[/dim] skipped (disabled in config)")

    def step_start(self, label: str, description: str) -> None:
        if self.verbosity == Verbosity.QUIET:
            return
        if self.verbosity == Verbosity.VERBOSE:
            self.console.print(f"  [cyan]▸[/cyan] [bold]{label:<12}[/bold] [dim]{description}[/dim]")
        else:
            self.console.print(f"  [cyan]▸[/cyan] [bold]{label:<12}[/bold] [dim]{description}…[/dim]")

    def step_done(
        self,
        step_name: str,
        label: str,
        findings: list[Finding],
        artifact_parts: dict[str, dict[str, Any]],
    ) -> None:
        if self.verbosity == Verbosity.QUIET:
            return
        summary, details = summarize_step(step_name, findings, artifact_parts)
        self.console.print(f"  [green]✔[/green] [bold]{label:<12}[/bold] {summary}")
        if self.verbosity == Verbosity.VERBOSE:
            for line in details:
                self.console.print(f"      [dim]→[/dim] {line}")

    def scoring(self, scores: AuditScores) -> None:
        if self.verbosity == Verbosity.QUIET:
            return
        self.console.print(
            f"  [magenta]▸[/magenta] [bold]scoring     [/bold] "
            f"Hygiene {scores.hygiene} · Exposure {scores.exposure} · {scores.verdict}"
        )

    def writing_reports(self) -> None:
        if self.verbosity == Verbosity.QUIET:
            return
        self.console.print(f"  [magenta]▸[/magenta] [bold]reports     [/bold] [dim]writing outputs…[/dim]")

    def detail(self, message: str) -> None:
        if self.verbosity == Verbosity.VERBOSE:
            self.console.print(f"      [dim]→[/dim] {message}")
