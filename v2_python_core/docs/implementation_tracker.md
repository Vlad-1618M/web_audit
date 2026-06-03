# Web Audit v2 — Implementation Tracker

*Single source of truth for what is built, what is reserved, and how to extend without breaking the plan.*

Update this file **whenever** a module lands or a contract changes. Cross-check [stages.md](stages.md) and [architecture.md](architecture.md).

---

## Version

| Tag | Date | Notes |
|-----|------|-------|
| **2.1.0b1** | 2026-06 | **Stage 5 beta** — Tier 2b/2c, owner report, CDN HSTS parity, Discoverability block; beta polish in `[Unreleased]` |
| **2.1.0a1** | 2026-05 | **Stage 5 alpha** — Tier 2b extensions, DNS enrichment, report polish, baseline diff |
| **2.0.0b1** | 2026-06 | **Tier 1 complete** — all v1-equivalent modules, reports, CLI polish |
| **2.0.0a1** | 2026-05 | Stage 1 alpha — CLI, config, headers + DNS, scoring, `audit_run.json` |

See [CHANGELOG.md](../CHANGELOG.md) for release notes.

---

## Module status (Tier 1)

| Module | Collector | Analyzer | Orchestrator | Tests | Stage |
|--------|-----------|----------|--------------|-------|-------|
| **headers** | `collectors/headers.py` ✓ | `analyzers/headers.py` ✓ | wired ✓ | ✓ | 1 |
| **dns** | `collectors/dns.py` ✓ (+ `asn.py`, `net_tools.py`) | `analyzers/dns.py` ✓ | wired ✓ | ✓ | 1 / 5 |
| **paths** | `collectors/paths.py` ✓ | `analyzers/paths.py` ✓ | wired ✓ | ✓ | **2** |
| **tls** | `collectors/tls.py` ✓ | `analyzers/tls.py` ✓ | wired ✓ | ✓ | **2** |
| **policy** (CSP/HSTS parse) | — (uses headers artifact) | `analyzers/policy.py` ✓ | wired ✓ | ✓ | **2** |
| **cookies** | `collectors/cookies.py` ✓ | `analyzers/cookies.py` ✓ | wired ✓ | ✓ | **2** |
| **artifacts** | `collectors/artifacts.py` ✓ | `analyzers/artifacts.py` ✓ | wired ✓ | ✓ | **2** |
| **rate_limit** | `collectors/rate_limit.py` ✓ | `analyzers/rate_limit.py` ✓ | wired ✓ | ✓ | **2** |
| **cors** | `collectors/cors.py` ✓ | `analyzers/cors.py` ✓ | wired ✓ | ✓ | **2** |
| **framework** detect | `collectors/framework.py` ✓ | `analyzers/framework.py` ✓ | wired ✓ | ✓ | **2–3** |
| **html** (DOM inventory) | `collectors/html.py` ✓ (+ `sitemap.py`, `site_discovery.py`; stores `scan_html`) | `analyzers/html.py` ✓ | wired ✓ | ✓ | **2–3 / 5** |
| **attribution** (designer credit) | `collectors/attribution.py` ✓ (footer/context rules) | report card via `render/context.py` ✓ | wired ✓ | ✓ | **5** ✓ |
| **scoring** | n/a | n/a | `scoring/engine.py` ✓ | ✓ | 1 (partial 3) |
| **render** | n/a | `render/html.py`, `render/txt.py`, `render/pdf.py`, `render/reports.py` ✓ | wired ✓ | ✓ | **4** ✓ |
| **render helpers** | n/a | `dns_display`, `probe_status`, `extension_display`, `discoverability_display`, `robots_display`, `report_metrics`, `focus_pie`, `finding_display`, `system_info` ✓ | wired ✓ | ✓ | **4 / 5** ✓ |
| **bot_challenge** | `collectors/bot_challenge.py` ✓ | used by framework/html/site_discovery ✓ | wired ✓ | ✓ | **5** ✓ |
| **js** (Playwright) | `collectors/js.py` ✓ | `analyzers/js.py` ✓ | wired ✓ | ✓ | **5 / 2** ✓ |
| **api** (GraphQL/OpenAPI) | `collectors/api.py` ✓ | `analyzers/graphql.py`, `openapi.py` ✓ | wired ✓ | ✓ | **5 / 2** ✓ |
| **links** (broken sample) | `collectors/links.py` ✓ | `analyzers/links.py` ✓ | wired ✓ | ✓ | **5 / 2c** ✓ |
| **profiles** (WP/Django/Laravel/Rails YAML) | `profiles/loader.py` ✓ | — | wired ✓ | ✓ | **5 / 2b** ✓ |
| **extensions** (multi-framework) | `collectors/extensions/` ✓ | `analyzers/extensions.py` ✓ | wired ✓ | ✓ | **5 / 2b** ✓ |
| **wp_plugins** (WP HTML/readme) | via `collectors/extensions/wordpress.py` ✓ | via unified analyzer ✓ | wired ✓ | ✓ | **5 / 2b** ✓ |
| **seo_surface** | — (uses framework HTML + artifacts) | `analyzers/seo_surface.py` ✓ | wired ✓ | ✓ | **5 / 2c** ✓ |
| **diff** | n/a | n/a | `scoring/diff.py` + `cli/diff_cmd.py` ✓ | ✓ | **5 / 2** ✓ |

**Do not rename** shipped modules (`headers`, `dns`) — tests and `audit_run.json` artifacts depend on keys.

---

## Stage 2 backlog (ordered — avoid reordering without updating this doc)

1. ~~**paths**~~ ✓ — Exposure score; v1 `is_sensitive_path()` parity  
   - Files: `collectors/paths.py`, `collectors/path_lists.py`, `analyzers/paths.py`  
   - Config: `PathsSettings` (`enabled`, `extra_paths`, `expected_open`)  
   - Artifact key: `artifacts.inventory.paths` (nested under `inventory` in `AuditArtifacts`)
   - Finding category: `PATHS`

2. ~~**tls**~~ ✓ — cert dates, versions, chain  
   - Files: `collectors/tls.py`, `analyzers/tls.py`  
   - Artifact key: `artifacts.tls`  
   - Deps: `cryptography` in `pyproject.toml`  
   - Config: `collectors.tls.*` (`enabled`, `check_deprecated_versions`, `expiry_warn_days`)

3. ~~**policy**~~ ✓ — CSP/HSTS deep parse (v1 `check_policy_parse`)  
   - Files: `analyzers/policy.py` (reads `artifacts.headers`, no new collector)  
   - Finding category: `POLICY`  
   - Artifact key: `artifacts.policy` (`hsts_detail`, `csp_detail`)

4. ~~**cookies**, **artifacts**, **rate_limit**, **cors**~~ ✓ — v1 parity modules wired in pipeline  
   - Artifacts under `artifacts.inventory.{cookies,artifacts,cors,rate_limit}`

5. ~~**framework** + **html**~~ ✓ — fingerprint before paths; DOM inventory + mixed content  
   - Artifacts: `artifacts.inventory.framework`, `artifacts.inventory.html`  
   - Auto `target.framework` updated when config is `auto`/`unknown`  
   - Deps: `beautifulsoup4`

6. ~~**render** (HTML reports)~~ ✓ — six Jinja2 variants (`owner` default)  
   - Files: `render/context.py`, `render/html.py`, `render/txt.py`, `render/reports.py`, `templates/reports/` + `_shared/` partials  
   - Output: `report.html` + `report.css`, optional `report.txt`  
   - Config: `report.variant` (`owner` | executive | technical | minimal | dashboard | digest), `output.formats` includes `html`, `txt`

7. ~~**render** (PDF + re-render CLI)~~ ✓  
   - Browser **Print / Save as PDF** in HTML (default)  
   - Optional headless: `pdf` in `output.formats` + `webaudit[pdf]`  
   - `webaudit report audit_run.json [--variant …] [--formats html,txt,pdf]`

---

## Extension contract (orchestrator)

All scan modules follow the same pattern. **Do not** put HTTP I/O in analyzers or scoring in collectors.

```text
1. collector → dataclass with .to_artifact() → dict
2. analyzer  → list[Finding]
3. orchestrator.run_audit() appends findings + merges artifacts
4. score_findings(all_findings) once at end
5. write_audit_run()
```

Register new work in `webaudit/pipeline.py` (preferred) or append in `orchestrator.py` following existing headers/DNS blocks.

**Finding rules:**

- Use `Finding.from_check()` for v1 parity auto-downgrade  
- Categories must match [scoring.md](scoring.md) (`HEADERS`, `DNS`, `PATHS`, `TLS`, `POLICY`, …)  
- Tier 2c `SEO_SURFACE` — never ACTION/scored by default  
- Tier 2b `PLUGIN*` — see [plugin_vulnerability_research.md](plugin_vulnerability_research.md)

**Artifact keys** (reserved in `AuditArtifacts` — do not repurpose):

| Key | Owner stage | Status |
|-----|-------------|--------|
| `headers` | 1 | live |
| `dns` | 1 / 5 | live — records + optional `whois` + `net_tools` |
| `tls` | 2 | live |
| `policy` | 2 | live |
| `inventory` | 2–3 | live (paths) |
| `plugins` | 5 / 2b | live (WP mirror of extensions) |
| `extensions` | 5 / 2b | live |
| `seo_surface` | 5 / 2c | live |

---

## Config contract

Merge order (do not change without updating [config.md](config.md)):

```text
defaults.yaml → ~/.config/webaudit/config.yaml → ./webaudit.yaml → --config → --site-config
```

| YAML section | Pydantic model | Wired to orchestrator |
|--------------|----------------|------------------------|
| `runtime.*` | `RuntimeSettings` | ✓ |
| `collectors.dns.*` | `DnsCollectorSettings` | ✓ |
| `paths.*` | `PathsSettings` | ✓ |
| `collectors.tls.*` | `TlsCollectorSettings` | ✓ |
| `collectors.*` (cookies, cors, …) | `CollectorsSettings` | ✓ |
| `scoring.*` | `ScoringSettings` | ✓ |
| `report.*` | `ReportSettings` | ✓ |
| `output.*` | `OutputSettings` | ✓ (json, html; txt/pdf opt-in) |

Adding a collector: extend `CollectorsSettings`, add defaults in `defaults.yaml`, snapshot appears in `config_snapshot` automatically via `model_dump()`.

---

## JSON schema stability

- `schema_version`: `"2.0"` — bump only on breaking `audit_run.json` shape changes  
- New artifact keys: **additive only** until 3.0  
- New finding categories: additive; scoring must ignore unknown categories safely  

---

## v1 parity reference

When implementing Stage 2 modules, mirror behavior from repo root `web_audit.sh` (read-only reference — **never import or source v1**):

| v2 module | v1 function (approx.) |
|-----------|------------------------|
| headers | `check_headers()` |
| policy | `check_policy_parse()` |
| paths | `is_sensitive_path()`, path probe loop |
| tls | `check_tls()`, `openssl_cert_info()` |
| cookies | cookie flag checks in v1 |
| dns | new in v2 (no v1 equivalent) |

Document intentional deltas in this file under **Parity deltas** when behavior differs.

### Parity deltas (known)

| Area | v2 today | v1 | Notes |
|------|----------|-----|-------|
| HSTS at CDN edge | VERIFY if missing (CDN detected from headers) | VERIFY if CDN detected | ✓ parity (2.1.0b1) |
| Permissions-Policy missing | INFO, unscored | same | ✓ |
| DNS | scored SPF/DMARC + report cards (A/MX/NS/ASN) | n/a | new signal |
| PDF | browser print default | browser print | optional WeasyPrint |
| Plugins/extensions | unified `extensions` pipeline + profiles; HTML from `scan_html` | readme.txt blind probes | Tier 2b ✓ (CVE cache deferred) |
| Plugin count in report | artifact row count + honest empty state | v1 N/A | v2 UX only |
| Attribution | footer/context linked credits only | grep-style HTML scan | hardened 2.1.0a1 |
| WAF / bot protection | VERIFY when captcha interstitial; framework hint from robots.txt | n/a | SiteGround HTTP 202 |
| Dashboard focus pie | slice size ∝ hygiene + exposure + SEO findings | n/a | docs pie 70/25/5 = scoring focus model, not chart |
| Site config | YAML | INI `site.conf` | Tier 3 migrator |

Full matrix: [tests/parity/PARITY.md](../tests/parity/PARITY.md).

---

## Tier 1 release checklist (2.0.0b1)

- [x] All Tier 1 modules in **Module status** table wired + tested
- [x] Stages 1–4 complete (collectors, analyzers, scoring, reports)
- [x] Parity matrix documented (`tests/parity/PARITY.md`)
- [x] CHANGELOG + version bump (`2.0.0b1`)
- [ ] Automated v1 golden fixtures (optional; manual spot-check OK for beta)

---

## Checklist before merging Stage 2+ PRs

- [ ] Row added/updated in **Module status** table above  
- [ ] `pipeline.py` or orchestrator wired; no scoring logic in collector  
- [ ] Unit tests with mocks (no live internet in CI)  
- [ ] `defaults.yaml` + `PathsSettings` / collector settings if new flags  
- [ ] [CHANGELOG.md](../CHANGELOG.md) Unreleased section  
- [ ] Parity delta noted if v1 behavior intentionally differs  

---

*Last updated: Tier 2 depth — JS pass, API probes, broken link sampler (2026-05).*
