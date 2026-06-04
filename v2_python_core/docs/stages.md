# Web Audit v2 — Stages & Tiers

*How I stack delivery: Tier 1 first, then Tier 2, then Tier 3. Each tier adds modules — no monolith rewrite.*

---

## Stage overview

```text
Stage 0   Documentation & mockups          ✓
Stage 1   Core skeleton + config + CLI     ✓
Stage 2   Tier 1 collectors + v1 parity    ✓
Stage 3   Scoring + analyzers + audit_run  ✓ (parity polish ongoing)
Stage 4   Report templates + PDF           ✓
Stage 5   Tier 2 + Tier 2b modules         ✓ complete (2.1.0b2)
          · extensions, DNS, owner report, baseline diff, JS/API/links ✓
          · WordPress theme fingerprint, live path probe streaming ✓ (2.1.0b3)
Stage 6   Tier 3 modules + packaging         ◐ in progress (2.1.0b3)
          · Docker WP fixture + orchestrate.sh + GitHub Actions ✓
          · GHCR publish (main / v.tools_main / v* tags) ✓
          · pytest HTML QA reports + WP integration tests ✓
          · CVE cache, SARIF, pipx/Homebrew — deferred
```

**Tier 1 (2.0.0b1):** Feature-complete for v2.0 foundation. CDN-aware HSTS downgrade aligned with v1 in **2.1.0b1**.

**Stage 5 (2.1.0b2):** Tier 2 depth + Tier 2b extensions + DNS enrichment + owner report + baseline diff.

**Stage 6 (2.1.0b3+):** CI/Docker harness landed first — see [docker_ci.md](docker_ci.md). Product Tier 3 (CVE cache, SARIF, packaging) still open — [CHANGELOG.md](../CHANGELOG.md) `[Unreleased]`.

Stages are **sequential**. Tiers are **feature bundles** that land across stages but are owned as logical groups.

### Stage 1 delivered (alpha)

- [x] `pyproject.toml` + installable `webaudit` CLI (`webaudit scan URL`)
- [x] YAML config loader (`webaudit/config/settings.py`, `defaults.yaml`)
- [x] Pydantic models: `Finding`, `AuditRun`, scores, artifacts
- [x] Orchestrator → `audit_logs/<timestamp>_<host>/audit_run.json` (schema 2.0)
- [x] Collectors: **headers** (httpx), **DNS** (dnspython)
- [x] Analyzers: headers (v1 `check_headers` parity), DNS (SPF/DMARC scoring policy)
- [x] Scoring engine: Hygiene, Exposure, Verdict
- [x] `dev-venv.sh` — setup / activate / teardown helper
- [x] pytest unit suite (config, collectors, analyzers, scoring, completion CLI)
- [x] `webaudit completion install|status|uninstall` with plain-English output

**Not in Stage 1:** paths, TLS, cookies, HTML reports, PDF, framework profiles, Tier 2b plugins.

Track built vs planned modules: [implementation_tracker.md](implementation_tracker.md) · [CHANGELOG.md](../CHANGELOG.md)

---

## Tier definitions

### Tier 1 — Foundation (must-have for v2.0)

**Purpose:** Replace the bash monolith with a maintainable Python core **and** deliver clearly new signal beyond v1.

| Module | Responsibility | Libraries |
|--------|----------------|-----------|
| `collectors.http` | GET/HEAD probes, redirects, methods | **httpx** |
| `collectors.paths` | Sensitive path list + config extras | httpx |
| `collectors.headers` | Response header capture | httpx |
| `collectors.tls` | Versions, chain, ciphers, cert dates | **ssl**, **cryptography** |
| `collectors.dns` | SPF, DMARC, A, AAAA, MX, NS, CAA, DNSSEC; ASN via Cymru DNS; optional host `whois` | **dnspython** (+ optional `whois` binary) |
| `collectors.cookies` | Set-Cookie parsing | httpx, **http.cookies** |
| `collectors.rate_limit` | Login GET burst + invalid POST | httpx |
| `collectors.artifacts` | robots, security.txt, sitemap | httpx |
| `analyzers.policy` | CSP/HSTS parse | custom + **tldextract** |
| `analyzers.html` | Links, images, forms, mixed content | **beautifulsoup4**, **lxml** |
| `analyzers.framework` | WP/Django/Laravel/Rails heuristics | beautifulsoup4 |
| `analyzers.cors` | Origin reflection / wildcard | httpx |
| `scoring.engine` | Hygiene, Exposure, Verdict | stdlib + pydantic models |
| `render.jinja` | HTML/TXT from templates | **jinja2** |
| `render.pdf` | PDF from HTML | **weasyprint** (optional extra) |
| `config.loader` | YAML validate + defaults | **pydantic**, **pyyaml** |
| `cli` | typer commands | **typer**, **rich** |

**Tier 1 deps (`pyproject.toml` core):**

```text
httpx>=0.27
dnspython>=2.6
cryptography>=42
beautifulsoup4>=4.12
lxml>=5.0
jinja2>=3.1
pydantic>=2.6
pyyaml>=6.0
typer>=0.12
rich>=13.7
tldextract>=5.0
```

**Optional extras:**

```text
webaudit[pdf]      → weasyprint
```

**Tier 1 exit criteria (2.0.0b1):**

- [x] Parity checklist vs v1 checks — [tests/parity/PARITY.md](../tests/parity/PARITY.md)
- [x] DNS section in report + `audit_run.json`
- [x] TLS chain section in report + artifacts
- [x] DOM-based HTML inventory (BeautifulSoup)
- [x] Five HTML templates wired
- [x] PDF — browser print (default); optional WeasyPrint headless
- [x] pytest on scoring, config, collectors, analyzers, render (~201 unit tests + WP Docker integration)

---

### Tier 2b — Framework extension intelligence (v2.1+, multi-framework)

**Purpose:** Data-driven plugin/package/gem detection via **framework profiles** — fixes v1 blind readme probing, adds version compare and optional CVE cache.

| Module | Responsibility | Libraries |
|--------|----------------|-----------|
| `config.profiles` | Detect framework → load `profiles/{fw}/extensions.yaml` | pyyaml, pydantic |
| `collectors.extensions` | Unified dispatch: WP plugins, Django/Laravel packages, Rails gems | httpx, beautifulsoup4 |
| `analyzers.extensions` | Registry compare (wp.org, PyPI, Packagist, RubyGems) | httpx, **packaging** |
| `collectors.wp_themes` | WP active theme + style.css + child theme | httpx |
| `analyzers.wp_themes` | wp.org theme compare, update-trap VERIFY, hardening advisory | httpx, **packaging** |
| `analyzers.plugin_vuln` | CVE match from cache / WPScan | httpx, sqlite |
| `storage.vuln_cache` | `(slug, version)` TTL cache | sqlite3 |

**Research basis:** [plugin_vulnerability_research.md](plugin_vulnerability_research.md) · [framework_profiles.md](framework_profiles.md)

**Profile mockups:** [mockups/config/profiles/](../mockups/config/profiles/)

**Tier 2b additional deps:**

```text
packaging>=24.0
```

**Tier 2b exit criteria:**

- [x] WordPress auto-detect loads `profiles/wordpress/extensions.yaml`
- [x] Django / Laravel / Rails profiles shipped with passive signals + registry compare
- [x] `probe.mode: observed_only` — no readme GET for undetected slugs (v1 fix)
- [x] Plugin fingerprint from **full homepage HTML** (`collectors.html` → `scan_html`), not truncated framework body
- [x] Free plugins compared to wordpress.org API
- [x] Premium slugs → VERIFY findings, not false “stale”
- [x] Report chip + empty state honest when zero plugins observed (decoupled frontends)
- [ ] Auth-required CVEs default to VERIFY class (deferred — `plugin_vuln` module)
- [x] `hygiene_caps.PLUGIN: 30` enforced in scoring tests
- [ ] CVE fixtures from research doc drive pytest golden files

---

### Tier 2c — SEO surface (v2.1+, informational only)

**Purpose:** Small slice for owners sold “SEO” — **INFO/VERIFY only**, zero impact on Hygiene/Exposure/Verdict by default.

| Module | Responsibility | Libraries |
|--------|----------------|-----------|
| `analyzers.seo_surface` | Meta robots, canonical, description, OG; robots/sitemap cross-check | beautifulsoup4, lxml |
| `analyzers.links` | Sampled broken internal links → INFO | httpx |

**Spec:** [seo_surface.md](seo_surface.md)

**Tier 2c exit criteria:**

- [x] All `SEO_SURFACE` findings default to INFO or VERIFY — never ACTION
- [x] `scoring.seo_surface_affects_scores: false` enforced in tests
- [x] Executive report shows one informational “Discoverability” block
- [x] No “SEO success %” or ranking language anywhere in UI
- [x] pytest: `noindex` homepage → VERIFY; missing meta description → INFO

---

### Tier 2 — Depth (v2.1+)

**Purpose:** Modern apps, SPAs, APIs, and time-series comparison.

| Module | Responsibility | Libraries |
|--------|----------------|-----------|
| `collectors.js` | Post-render DOM + bundle scan | **playwright** (optional `[js]` extra) |
| `collectors.api` | GraphQL introspection, OpenAPI fetch | httpx |
| `collectors.subdomain` | Passive subdomain list | httpx + CT API (crt.sh) |
| `analyzers.graphql` | Introspection enabled finding | json |
| `analyzers.openapi` | Swagger exposure summary | httpx, pyyaml |
| `analyzers.tech` | Wappalyzer-style fingerprint rules | yaml rules file |
| `analyzers.links` | Broken link checker (sampled) | httpx |
| `storage.baseline` | sqlite run history | **sqlite3** (stdlib) |
| `scoring.diff` | Compare two audit_run.json files | pydantic |

**Tier 2 additional deps:**

```text
playwright>=1.42    # extra: webaudit[js]
```

**Tier 2 exit criteria:**

- [x] `--js` flag runs Playwright pass when installed
- [x] Baseline diff in CLI (`webaudit diff`)
- [x] GraphQL / OpenAPI findings when exposed
- [x] WordPress Docker integration tests (`tests/integration/`, `./orchestrate.sh --job wp-integration`) — live HTTP to local fixture
- [ ] httpx **cassette** tests for Tier 2 collectors (optional; unit tests use pytest-httpx mocks today)

---

### Tier 3 — Ecosystem (v2.2+)

**Purpose:** CI integration, passive intelligence, polish for “massive consumption.”

| Module | Responsibility | Libraries |
|--------|----------------|-----------|
| `export.sarif` | GitHub Code Scanning format | json schema |
| `analyzers.cve` | Version → CVE hint (VERIFY class) | **nvdlib** or cached CPE map |
| `analyzers.plugin_vuln` | WP plugin CVE from shipped snapshot | sqlite + weekly JSON |
| `analyzers.takeover` | CNAME → known-bad SaaS targets | dnspython + rules yaml |
| `collectors.whois` | Registrar expiry (library fallback) | **python-whois** — optional; host `whois` binary used first when present (2.1.0a1) |
| `collectors.http3` | QUIC/HTTP3 probe where supported | httpx (when capable) |
| `config.migrate` | Import v1 INI → v2 YAML | custom |
| `packaging` | pipx, Homebrew, deb | external tooling |

**Tier 3 additional deps:**

```text
python-whois>=0.9
nvdlib>=0.7          # optional, rate-limited
```

**Tier 3 exit criteria:**

- [ ] SARIF export tested against GitHub
- [ ] INI → YAML migrator for existing `site_configs/*.conf`
- [ ] Homebrew formula in repo
- [ ] Executive one-pager localized strings stub (i18n-ready)

---

## Stage × Tier matrix

| Stage | Tier 1 | Tier 2 | Tier 3 |
|-------|--------|--------|--------|
| **0 — Docs** | Spec | Spec | Spec |
| **1 — Skeleton** | config, cli, models, headers+DNS slice, scoring, `audit_run.json` | — | — |
| **2 — Collect** | remaining Tier 1 collectors | — | — |
| **3 — Analyze/Score** | remaining analyzers, parity polish | — | — |
| **4 — Render** | templates + PDF | — | — |
| **5 — Extend** | polish | JS, API, baseline, **Tier 2b WP profiles**, **Tier 2c SEO surface**, **WP themes** | — |
| **6 — Ship wide** | pipx | WP Docker integration CI | SARIF, CVE cache, packaging, GHCR ✓ |

---

## Libraries I am explicitly NOT using

| Library | Why not |
|---------|---------|
| **Scapy** | Packet crafting = pentest territory; wrong product boundary |
| **Scrapy** | Heavy crawl framework; httpx async loop is enough for hygiene |
| **Django/Flask** | No web server in core; CLI tool only |
| **Selenium** | Playwright is the modern choice for optional JS |

---

## Module boundaries (no salad bowl)

```text
collectors/     → fetch raw bytes, headers, DNS records → RawArtifact models
analyzers/      → RawArtifact → Finding models (no HTTP calls if avoidable)
scoring/        → Finding[] → Scores + Verdict (pure functions, easy pytest)
render/         → audit_run.json + template name → HTML/TXT/PDF (no scoring logic)
config/         → YAML → Settings (validated once at startup)
cli/            → wires stages; thin orchestration only
```

**Rule:** If a file both fetches HTTP and renders HTML, I split it.

---

## Testing per stage (summary — detail in [testing.md](testing.md))

| Stage | Test focus |
|-------|------------|
| 1 | config validation, pydantic models |
| 2 | collector unit tests with mocked httpx |
| 3 | analyzer fixtures (HTML snippets, header sets) |
| 3 | scoring math — golden files |
| 4 | template snapshot tests (HTML structure) |
| 5 | integration scan against local WP Docker fixture / wiremock |
| 6 | packaging smoke install in CI — **Docker build + GHCR** ✓; pipx/Homebrew pending |

---

## v1 PDF vs v2 PDF

**v1:** HTML toolbar → `window.print()` → user picks “Save as PDF” → depends on browser, background graphics toggle, dark theme quirks.

**v2 Tier 1:** After HTML render, **WeasyPrint** (or fallback **xhtml2pdf**) produces PDF in `audit_logs/` automatically when `output.pdf: true` in config. No browser. Same CSS `@media print` rules reused where possible.

---

*Related: [architecture.md](architecture.md) · [scoring.md](scoring.md) · [config.md](config.md) · [framework_profiles.md](framework_profiles.md) · [seo_surface.md](seo_surface.md)*
