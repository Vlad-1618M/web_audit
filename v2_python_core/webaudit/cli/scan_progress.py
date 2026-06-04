"""Colored scan progress — verbosity levels for ``webaudit scan``."""

from __future__ import annotations

import re
from enum import IntEnum
from typing import Any

from rich.console import Console
from rich.markup import escape as markup_escape

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
    "_step_js": ("js", "Playwright JS render pass"),
    "_step_links": ("links", "Broken internal link sample"),
    "_step_api": ("api", "GraphQL / OpenAPI discovery"),
    "_step_extensions": ("extensions", "Framework extensions / packages"),
    "_step_vuln": ("vuln", "Plugin/theme CVE cache lookup"),
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
        case "_step_js":
            return settings.collectors.js.enabled
        case "_step_links":
            return (
                settings.collectors.seo_surface.enabled
                and settings.collectors.seo_surface.check_broken_links
            )
        case "_step_api":
            return settings.collectors.api.enabled
        case "_step_extensions":
            return settings.collectors.extensions.enabled
        case "_step_vuln":
            return settings.collectors.vuln.enabled
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


def _format_path_probe_verbose_line(probe: dict[str, Any]) -> str:
    """One verbose detail line — path in orange, note/status dimmed."""
    path = markup_escape(str(probe.get("path") or "?"))
    note = str(probe.get("note") or "?")
    final_status = probe.get("final_status")
    if final_status is not None:
        note = f"{note} · HTTP {final_status}"
    note = markup_escape(note)
    # Trailing space before [/tag] — paths like /.env must not end adjacent to [/ (Rich false close).
    return f"[dark_orange]{path} [/dark_orange][dim]{note}[/dim]"


def summarize_step(
    step_name: str,
    findings: list[Finding],
    artifact_parts: dict[str, dict[str, Any]],
    *,
    verbose: bool = False,
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
        probes = [p for p in (art.get("paths") or []) if isinstance(p, dict)]
        open_paths = [
            p.get("path")
            for p in probes
            if p.get("note") in {"OPEN", "LEAKING"}
        ]
        summary = f"{count} probes · {note.replace('[yellow]', '').replace('[/yellow]', '')}"
        if open_paths:
            details.append(f"exposed: {', '.join(open_paths[:5])}")
        elif count:
            details.append("no sensitive paths openly readable")
        if verbose:
            for probe in probes:
                details.append(_format_path_probe_verbose_line(probe))

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

    elif step_name == "_step_js":
        art = artifact_parts.get("inventory", {}).get("js", {})
        if art.get("skipped"):
            summary = f"skipped · {note.replace('[yellow]', '').replace('[/yellow]', '')}"
        elif art.get("error"):
            summary = f"error · {note.replace('[yellow]', '').replace('[/yellow]', '')}"
        else:
            summary = (
                f"{art.get('link_count', 0)} rendered link(s) · "
                f"{note.replace('[yellow]', '').replace('[/yellow]', '')}"
            )

    elif step_name == "_step_links":
        art = artifact_parts.get("inventory", {}).get("links", {})
        broken = art.get("broken_count", 0)
        sampled = art.get("sampled", 0)
        summary = (
            f"{sampled} sampled · {broken} broken · "
            f"{note.replace('[yellow]', '').replace('[/yellow]', '')}"
        )

    elif step_name == "_step_api":
        art = artifact_parts.get("inventory", {}).get("api", {})
        gql = sum(1 for p in (art.get("graphql") or []) if p.get("introspection_enabled"))
        oas = sum(1 for p in (art.get("openapi") or []) if p.get("openapi_detected"))
        summary = (
            f"GraphQL introspection {gql} · OpenAPI {oas} · "
            f"{note.replace('[yellow]', '').replace('[/yellow]', '')}"
        )

    elif step_name == "_step_extensions":
        art = artifact_parts.get("extensions", {})
        count = art.get("extension_count", 0)
        unit = art.get("unit", "extension")
        fw = art.get("framework", "?")
        themes = art.get("themes") or {}
        active = themes.get("active") or {}
        theme_bit = ""
        if active.get("slug"):
            theme_bit = f" · theme {active.get('slug')}"
            if active.get("is_child_theme"):
                theme_bit += " (child)"
        summary = (
            f"{fw} · {count} {unit}(s){theme_bit} · "
            f"{note.replace('[yellow]', '').replace('[/yellow]', '')}"
        )
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


_PATH_NOTES_STREAM_NORMAL = frozenset({"OPEN", "LEAKING"})


class ScanProgress:
    """Rich console progress for pipeline steps."""

    def __init__(self, console: Console, verbosity: Verbosity) -> None:
        self.console = console
        self.verbosity = verbosity
        self._paths_label = "paths"
        self._paths_streamed = False

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
        if label == "paths":
            self._paths_label = label
            self._paths_streamed = False
        if self.verbosity == Verbosity.VERBOSE:
            self.console.print(f"  [cyan]▸[/cyan] [bold]{label:<12}[/bold] [dim]{description}[/dim]")
        else:
            self.console.print(f"  [cyan]▸[/cyan] [bold]{label:<12}[/bold] [dim]{description}…[/dim]")

    def paths_probe_start(self, total: int) -> None:
        """Called once before path probes; enables live counter / streaming lines."""
        if self.verbosity == Verbosity.QUIET or total <= 0:
            return
        self._paths_streamed = True

    def paths_probe_done(self, probe: dict[str, Any], index: int, total: int) -> None:
        """Stream each path probe as it completes (counter in normal, full list in verbose)."""
        if self.verbosity == Verbosity.QUIET:
            return
        label = self._paths_label
        if self.verbosity == Verbosity.VERBOSE:
            self.console.print(
                f"      [dim]→[/dim] {_format_path_probe_verbose_line(probe)}",
                highlight=False,
            )
            return
        self.console.print(
            f"  [cyan]▸[/cyan] [bold]{label:<12}[/bold] [dim]probing {index}/{total}…[/dim]",
            end="\r",
            highlight=False,
        )
        note = str(probe.get("note") or "")
        if note in _PATH_NOTES_STREAM_NORMAL:
            path = markup_escape(str(probe.get("path") or "?"))
            status = probe.get("final_status")
            status_bit = f" · HTTP {status}" if status is not None else ""
            self.console.print(
                f"      [yellow]→[/yellow] exposed: [dark_orange]{path} [/dark_orange]"
                f"[dim]{markup_escape(status_bit)}[/dim]",
                highlight=False,
            )

    def step_done(
        self,
        step_name: str,
        label: str,
        findings: list[Finding],
        artifact_parts: dict[str, dict[str, Any]],
    ) -> None:
        if self.verbosity == Verbosity.QUIET:
            return
        summary, details = summarize_step(
            step_name,
            findings,
            artifact_parts,
            verbose=self.verbosity == Verbosity.VERBOSE,
        )
        self.console.print(f"  [green]✔[/green] [bold]{label:<12}[/bold] {summary}")
        if self.verbosity == Verbosity.VERBOSE:
            for line in details:
                if step_name == "_step_paths" and self._paths_streamed and "[dark_orange]" in line:
                    continue
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
