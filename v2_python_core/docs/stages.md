# Web Audit v2 — Stages & Tiers

*How I stack delivery: Tier 1 first, then Tier 2, then Tier 3. Each tier adds modules — no monolith rewrite.*

---

## Stage overview

```text
Stage 0   Documentation & mockups          ← we are here
Stage 1   Core skeleton + config + CLI
Stage 2   Tier 1 collectors + v1 parity
Stage 3   Scoring + analyzers + audit_run.json
Stage 4   Report templates + PDF
Stage 5   Tier 2 + Tier 2b modules
Stage 6   Tier 3 modules + packaging
```

Stages are **sequential**. Tiers are **feature bundles** that land across stages but are owned as logical groups.

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
| `collectors.dns` | SPF, DMARC, AAAA, CAA, DNSSEC | **dnspython** |
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

**Tier 1 exit criteria:**

- [ ] Parity checklist vs v1 checks (documented deltas)
- [ ] DNS section in report (new)
- [ ] TLS chain section (new)
- [ ] DOM-based misc inventory (better than regex)
- [ ] Five HTML templates wired
- [ ] PDF generates without browser
- [ ] pytest coverage on scoring + config + parsers

---

### Tier 2b — Framework extension intelligence (v2.1+, WordPress first)

**Purpose:** Data-driven plugin/package detection via **framework profiles** — fixes v1 blind readme probing, adds version compare and optional CVE cache.

| Module | Responsibility | Libraries |
|--------|----------------|-----------|
| `config.profiles` | Detect framework → load `profiles/{fw}/extensions.yaml` | pyyaml, pydantic |
| `collectors.wp_plugins` | Slug/version from HTML `?ver=`, readme.txt | httpx, beautifulsoup4 |
| `analyzers.wp_plugins` | wp.org latest compare, stale heuristics | httpx, **packaging** |
| `analyzers.plugin_vuln` | CVE match from cache / WPScan | httpx, sqlite |
| `storage.vuln_cache` | `(slug, version)` TTL cache | sqlite3 |

**Research basis:** [plugin_vulnerability_research.md](plugin_vulnerability_research.md) · [framework_profiles.md](framework_profiles.md)

**Profile mockups:** [mockups/config/profiles/](../mockups/config/profiles/)

**Tier 2b additional deps:**

```text
packaging>=24.0
```

**Tier 2b exit criteria:**

- [ ] WordPress auto-detect loads `profiles/wordpress/extensions.yaml`
- [ ] `probe.mode: observed_only` — no readme GET for undetected slugs (v1 fix)
- [ ] Free plugins compared to wordpress.org API
- [ ] Premium slugs → VERIFY findings, not false “stale”
- [ ] Auth-required CVEs default to VERIFY class
- [ ] `hygiene_caps.PLUGIN: 30` enforced in scoring tests
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

- [ ] All `SEO_SURFACE` findings default to INFO or VERIFY — never ACTION
- [ ] `scoring.seo_surface_affects_scores: false` enforced in tests
- [ ] Executive report shows one informational “Discoverability” block
- [ ] No “SEO success %” or ranking language anywhere in UI
- [ ] pytest: `noindex` homepage → VERIFY; missing meta description → INFO

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

- [ ] `--js` flag runs Playwright pass when installed
- [ ] Baseline diff in CLI and report
- [ ] GraphQL / OpenAPI findings when exposed
- [ ] Integration tests with recorded httpx cassettes (**pytest-httpx** or **vcrpy**)

---

### Tier 3 — Ecosystem (v2.2+)

**Purpose:** CI integration, passive intelligence, polish for “massive consumption.”

| Module | Responsibility | Libraries |
|--------|----------------|-----------|
| `export.sarif` | GitHub Code Scanning format | json schema |
| `analyzers.cve` | Version → CVE hint (VERIFY class) | **nvdlib** or cached CPE map |
| `analyzers.plugin_vuln` | WP plugin CVE from shipped snapshot | sqlite + weekly JSON |
| `analyzers.takeover` | CNAME → known-bad SaaS targets | dnspython + rules yaml |
| `collectors.whois` | Registrar expiry | **python-whois** |
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
| **1 — Skeleton** | config, cli, models | — | — |
| **2 — Collect** | all Tier 1 collectors | — | — |
| **3 — Analyze/Score** | analyzers, scoring | — | — |
| **4 — Render** | templates + PDF | — | — |
| **5 — Extend** | polish | JS, API, baseline, **Tier 2b WP profiles**, **Tier 2c SEO surface** | — |
| **6 — Ship wide** | pipx | — | SARIF, packaging |

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
| 5 | integration scan against `example.com` / local wiremock |
| 6 | packaging smoke install in CI |

---

## v1 PDF vs v2 PDF

**v1:** HTML toolbar → `window.print()` → user picks “Save as PDF” → depends on browser, background graphics toggle, dark theme quirks.

**v2 Tier 1:** After HTML render, **WeasyPrint** (or fallback **xhtml2pdf**) produces PDF in `audit_logs/` automatically when `output.pdf: true` in config. No browser. Same CSS `@media print` rules reused where possible.

---

*Related: [architecture.md](architecture.md) · [scoring.md](scoring.md) · [config.md](config.md) · [framework_profiles.md](framework_profiles.md) · [seo_surface.md](seo_surface.md)*
