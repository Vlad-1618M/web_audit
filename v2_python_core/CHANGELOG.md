# Changelog

All notable changes to **Web Audit v2** (`v2_python_core/`) are documented here.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/). v1 (`web_audit.sh`) is unchanged and not listed here.

---

## [Unreleased]

### Deferred (Stage 6 / Tier 3)

- Theme CVE match via WPScan cache (version compare + child-theme detection implemented)
- Plugin CVE cache / WPScan (`analyzers.plugin_vuln`)
- httpx cassette integration tests (pytest-httpx / vcrpy) for Tier 2 collectors

### Added

- **WordPress theme fingerprint** — active theme slug from HTML; `style.css` version + child theme (`Template:`) parse; wp.org version compare for free themes; premium watchlist + update-trap VERIFY for parent-only Avada/Divi-style installs; DISALLOW_FILE_EDIT advisory when wp-admin is reachable (`collectors/wp_themes.py`, `analyzers/wp_themes.py`, `render/theme_display.py`)
- **Theme report section** — Technical tab panel beside Plugins/Extensions with version table and hardening advisory

---

## [2.1.0b2] — 2026-06-03

**Stage 5 beta complete** — Tier 2 depth (Playwright JS, API probes, broken links), report UX polish, bot protection.

### Added

- **Finding table colors** — Verify/Expected/Action status tones; TLS certificate/hostname row colors; dashboard alert strip by severity (`render/finding_display.py`)
- **Bot protection detection** — SiteGround/captcha interstitials (HTTP 202, `sgcaptcha`); HTML VERIFY when homepage blocked; WordPress hint from `robots.txt` when framework fingerprint fails (`collectors/bot_challenge.py`)
- **Dynamic focus pie** — dashboard Scan focus chart slice sizes from live hygiene, exposure, and SEO finding weights (not fixed 70/25/5)
- **Priority timeline colors** — category stays violet; severity/status label matches timeline bullet tone
- **Playwright JS pass** — `collectors/js.py` + `--js` CLI flag (optional `webaudit[js]` extra); technical report section + inventory rows; Playwright errors normalized (no raw paths in HTML — full detail in `audit_run.json`)
- **JS discovery panel** — success stats grid in owner report when Playwright completes; friendly install hints (`error_code`, `fix_steps`) when browsers missing (`render/js_display.py`)
- **GraphQL / OpenAPI probes** — `collectors/api.py` + analyzers; `--api` CLI flag; introspection and Swagger/OpenAPI exposure as VERIFY findings
- **Broken link sampler** — `collectors/links.py` + `analyzers/links.py`; enable via `collectors.seo_surface.check_broken_links`
- **Owner report navigation** — action bar (Print + Executive/Technical tabs); sidebar back button and scan-target label

### Fixed

- **Site discovery enrich** — HTTP client created when only homepage needs fetch (fixes crash on no-sitemap sites)
- **Site discovery scroll** — paired probe/site URL fold panels restore max-height scroll (was expanding to full list height)
- **Metric chip labels** — long labels (e.g. Sensitive leaks) wrap inside chip instead of overflowing
- **Watchlist tier badge** — `critical` watchlist tier uses light blue (not error red) when plugin status is CURRENT
- **Focus pie template** — pre-render chart markup in Python; legend swatches use CSS classes (IDE/linter clean)
- **Extensions step gate** — plugins step runs when framework inferred from `robots.txt` after WAF block

### Changed

- **Verbose scan (`-v`)** — lists every probed path in progress output

---

## [2.1.0b1] — 2026-06-03

**Stage 5 beta** — Tier 2b extensions, DNS enrichment, SEO surface, owner report, baseline diff, and v1 parity polish.

### Added (Stage 5 — Tier 2b / 2c / baseline diff + report polish)

- **Owner combined report** — default `owner` variant: framed **Security dashboard** + unified **Executive summary** (digest timeline merged in); **Scan focus pie** (hygiene/exposure/SEO); Technical tab with draggable sidebar
- **Fold panels** — probe URLs, site URLs, images, and path probes **unfolded by default**; clearer chevron toggle bars (“Click to fold or unfold”)
- **Shared report partials** — `digest_body`, `executive_body`, `technical_main` reused by standalone variants
- **DNS enrichment** — A, MX, NS records via dnspython; **ASN** via Team Cymru DNS (`collectors/asn.py`); optional host **`whois`** when binary present (`collectors/net_tools.py`); host tool detection stored in artifact + report footer note
- **DNS report cards** — plain-English summaries for SPF/DMARC/CAA/A/AAAA/MX/NS/ASN/DNSSEC + optional WHOIS registration card (`render/dns_display.py`)
- **Site discovery** — full homepage fetch, sitemap index expansion, multi-page link sampling (`collectors/sitemap.py`, `site_discovery.py`); favicon/og/twitter/lazy-load image collection
- **Report UX** — HTTP status convention colors vs semantic outcome (`render/probe_status.py`); metric chips row; parsed robots.txt section; extensions section with registry links (all frameworks); designer attribution card; muzar.io footer; clickable target URLs; path probes legend/collapse fixes
- **Executive Discoverability block** — owner/executive summary shows `SEO_SURFACE` findings (INFO/VERIFY) in plain language; does not affect scores
- **Framework profiles** — `webaudit/profiles/{wordpress,django,laravel,rails,generic}/extensions.yaml` + `profiles/loader.py`
- **Unified extensions pipeline** — `collectors/extensions/` dispatches by framework:
  - **WordPress** — HTML asset slugs + readme.txt + wp.org compare (plugins)
  - **Django** — DEBUG/traceback signals + Django/package version hints + PyPI compare
  - **Laravel** — Whoops/debug signals + Packagist compare for `laravel/framework`
  - **Rails** — asset/CSRF signals + RubyGems compare for `rails` and watchlist gems
  - **PHP/generic** — Server / X-Powered-By version disclosure signals
- **`analyzers/extensions.py`** + registry compare (`wp.org`, PyPI, Packagist, RubyGems)
- Finding categories: `PLUGIN*` (WP), `PACKAGE*` (Django/Laravel), `GEM*` (Rails)
- **`analyzers/seo_surface`** — meta robots, canonical, description, robots/sitemap cross-check (INFO/VERIFY only)
- **Scoring caps** — `hygiene_caps` for PLUGIN/PACKAGE/GEM + `plugin_worst_wins`
- **`webaudit diff`** — compare two `audit_run.json` files
- Config: `collectors.extensions` (alias `wp_plugins`), `collectors.seo_surface`, `collectors.dns.{check_a,check_mx,check_ns,check_asn,use_host_tools}`, `collectors.html.prefer_full_homepage_fetch`
- Artifact key: `artifacts.extensions` (+ legacy `artifacts.plugins` for WordPress); `artifacts.dns.{records,whois,net_tools}`; `artifacts.inventory.html.scan_html` (full homepage body for extensions + attribution)

### Fixed

- **WordPress plugin detection** — extensions step reads full homepage HTML (`scan_html` from HTML collector), not the truncated framework fingerprint body (~8 KB cap); fixes under-counting on real WP sites
- **Plugin chip count** — dashboard “Plugins” chip uses detected extension rows from artifacts; `PLUGIN_INFO / NONE_OBSERVED` no longer shows as “1 plugin” on decoupled frontends (e.g. Next.js)
- **readme.txt soft-404** — HTML error pages rejected when fetching plugin readme for version hints
- **Attribution false positives** — ignore nav `title="powered by …"` credits; require footer/context for linked designer lines; treat AI “Powered by” as tooling, not site designer
- **CDN HSTS parity (v1)** — missing `Strict-Transport-Security` at Cloudflare (and other detected CDNs) → **VERIFY** / unscored, not ACTION HIGH

### Changed (report UX polish — owner default)

- **Owner guide** — expanded “What this report is (and is not)” for non-devs: how to read scores, tool comparison (ZAP, Nuclei, etc.), dev/QA suggestions (`report_about_section.html`)
- **Branding footer** — three-line footer with finding count; only **muzar.io** linked (`report_branding_footer_body.html`)
- **Score clarity** — Hygiene and **Leak protection** (Exposure in JSON) use color bands (good/fair/poor/critical); Exposure labeled **Leak protection** in UI (higher = safer; 100 = no leaks)
- **Dashboard header** — framework/verdict tags aligned right; white section titles + conventional light-blue URL links
- **Discovery layout** — 50/50 probe/site columns with matched scroll heights; probe status badges inline with URL + hint on second line; compact focus-pie legend
- **Extensions section** — “Plugins / Extensions” heading, registry summary line, fold-panel table; empty state + Next.js note when no plugin paths in public HTML
- **Metric chips** — clickable when count &gt; 0 (anchors to Findings sections); Expected + SEO tables under Technical tab
- **robots.txt** — fold-panel widget aligned with path probe results style
- **Category health** — bottom alert strip for failing categories; scrollable when many items
- **Executive summary** — tighter verdict banner spacing; removed redundant verdict pill (banner + score strip remain)
- **Readability** — brighter prose colors (`--text-soft`) in owner guide section

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

- HSTS at CDN edge: fixed in 2.1.0b1 — VERIFY when CDN detected (was ACTION in early 2.0.0b1)
- Plugin/CVE probes: deferred to Tier 2b (framework profiles) — compare live; CVE cache deferred

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

[2.1.0b2]: https://github.com/Vlad-1618M/web_audit/compare/2.1.0b1...2.1.0b2
[2.1.0b1]: https://github.com/Vlad-1618M/web_audit/compare/2.0.0b1...2.1.0b1
[2.0.0b1]: https://github.com/Vlad-1618M/web_audit/compare/2.0.0a1...2.0.0b1
[2.0.0a1]: https://github.com/Vlad-1618M/web_audit/releases/tag/2.0.0a1
