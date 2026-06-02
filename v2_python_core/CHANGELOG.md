# Changelog

All notable changes to **Web Audit v2** (`v2_python_core/`) are documented here.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/). v1 (`web_audit.sh`) is unchanged and not listed here.

---

## [Unreleased]

---

## [2.0.0b1] — 2026-06-02

**Tier 1 complete** — v1-equivalent checks in Python, DNS/TLS depth, reports, CLI polish. See [tests/parity/PARITY.md](tests/parity/PARITY.md).

### Added

- **paths** collector + analyzer — v1 sensitive path probes; Exposure scoring via `PATHS` findings
- Built-in path lists (`collectors/path_lists.py`); config: `paths.enabled`, `extra_paths`, `expected_open`
- **tls** collector + analyzer — TLS 1.0–1.3 probes, certificate subject/issuer/expiry/chain
- **policy** analyzer — HSTS max-age/includeSubDomains and CSP unsafe-inline/eval/wildcard checks
- **cookies**, **artifacts**, **rate_limit**, **cors** — v1 parity collectors + analyzers
- **framework** + **html** — stack fingerprint and DOM inventory/mixed content
- **HTML reports** — Jinja2 `technical`, `executive`, `minimal`, `dashboard`, `digest` variants
- **`webaudit report`** — re-render HTML/TXT/PDF from saved `audit_run.json`
- **TXT reports** — `report.txt` when `txt` in `output.formats`
- **PDF** — browser Print / Save as PDF (dark theme print CSS); optional WeasyPrint via `webaudit[pdf]`
- **Scan progress** — colored step output by default; `-v` verbose, `-q` quiet
- **Post-scan `--open`** — interactive or explicit open html/json/txt/all/none
- **`load_audit_run()`** + shared `write_run_reports()` pipeline
- pytest suite expanded (~85 tests); parity matrix in `tests/parity/PARITY.md`

### Changed

- Scan CLI output: compact summary + run folder listing (replaces score table + long PDF hint)
- `run_pipeline()` / `run_audit()` accept optional progress logger

### Known parity deltas (documented)

- HSTS at CDN edge: v2 still ACTION if missing (v1 downgrades to VERIFY when CDN detected)
- Plugin/CVE probes: deferred to Tier 2b (framework profiles)

### Next

- Stage 5: Tier 2 / 2b (WordPress profiles, plugin intelligence, SEO surface, Playwright, baseline diff)

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

[2.0.0b1]: https://github.com/Vlad-1618M/web_audit/compare/2.0.0a1...2.0.0b1
[2.0.0a1]: https://github.com/Vlad-1618M/web_audit/releases/tag/2.0.0a1
