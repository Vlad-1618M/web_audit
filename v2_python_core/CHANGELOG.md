# Changelog

All notable changes to **Web Audit v2** (`v2_python_core/`) are documented here.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/). v1 (`web_audit.sh`) is unchanged and not listed here.

---

## [Unreleased]

### Planned (Stage 2)

- Paths collector + analyzer (Exposure scoring)
- TLS collector + analyzer
- Policy analyzer (CSP/HSTS parse)
- Cookies, artifacts, rate limit, CORS modules

See [docs/implementation_tracker.md](docs/implementation_tracker.md).

---

## [2.0.0a1] — 2026-05-31

### Added

- Installable `webaudit` package (`pyproject.toml`, Python ≥ 3.11)
- CLI: `webaudit scan URL` with `-h`, `--json`, `--config`, `--output`
- CLI: `webaudit completion install|status|uninstall|show`
- YAML config loader with layered merge (`webaudit/config/settings.py`, `defaults.yaml`)
- Models: `Finding`, `AuditRun`, scores, artifacts (`schema_version` 2.0)
- Collectors: HTTP headers, DNS (SPF, DMARC, CAA, AAAA, DNSSEC)
- Analyzers: headers (v1 `check_headers` parity), DNS scoring policy
- Scoring engine: Hygiene, Exposure, Verdict
- Orchestrator + `audit_logs/<timestamp>_<host>/audit_run.json`
- `dev-venv.sh` — venv setup, activate, minimal shell, teardown
- pytest suite (14 tests): config, headers, DNS, scoring, completion CLI
- Docs: `getting_started_plain.md`, synced stages/architecture/scoring

### Not included

- Sensitive path probes, TLS, cookies, HTML reports, PDF, framework profiles, Tier 2b plugins

[2.0.0a1]: https://github.com/Vlad-1618M/web_audit/compare/v.tools_main...HEAD
