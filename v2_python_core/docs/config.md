# Web Audit v2 — Configuration System

*YAML-driven scanner settings — global defaults, per-site overrides, no magic constants buried in Python.*

**Stage 1 status:** `load_settings()` merges shipped `defaults.yaml` → `~/.config/webaudit/config.yaml` → project `webaudit.yaml` → `--config` / `--site-config` CLI flags. Framework profile auto-load is **live (2.1.0a1)**.

---

## Why YAML (not INI, not Python dicts)

- Nested sections — DNS, TLS, report, scoring in one file
- Comments for humans (site owners sharing configs with devs)
- pydantic validation at load time
- Same files work for CLI, CI, and future GUI config editor

v1 INI (`site.conf.template`) maps to v2 in Tier 3 via `webaudit config migrate`. Until then, I document the v2 shape fresh.

---

## Config files (four layers)

| File | Scope | Example path |
|------|-------|--------------|
| **Global defaults** | Shipped with package | `webaudit/config/defaults.yaml` |
| **User config** | My machine defaults | `~/.config/webaudit/config.yaml` |
| **Site profile** | One hostname | `site_configs/example.com.yaml` |
| **Framework profile** | Auto when WP/Django/… detected | `profiles/wordpress/extensions.yaml` |

Merge order (later wins): defaults → user → `--config` → site profile → **framework profile** → `site.extensions` → CLI flags.

Framework profile detail: [framework_profiles.md](framework_profiles.md).

---

## Full schema overview

```yaml
# See mockups/config/webaudit.example.yaml for global
# See mockups/config/site.example.yaml for per-site

webaudit_version: "2.0"

target:
  url: ""                    # or pass on CLI
  framework: auto            # auto | django | wordpress | laravel | rails | php | unknown

framework_profiles:
  auto_load: true            # load profiles/{detected}/extensions.yaml
  min_confidence: 0.65       # below → generic/php profile
  profile_dir: null          # null = shipped webaudit/profiles/

extensions:                  # site-level override (merged after framework profile)
  inherit_profile: true
  probe:
    mode: observed_only      # fix v1 blind readme GETs
  extra_watch: []
  ignore: []
  expected: []

runtime:
  timeout_seconds: 15
  max_concurrency: 8
  probe_delay_ms: 0
  user_agent: "WebAudit/2.0 (+https://github.com/Vlad-1618M/web_audit)"

paths:
  sensitive_builtin: true      # use built-in sensitive list
  extra_get: []              # v1 [paths] extra=
  expected_open: {}          # v1 [expected_open]
  max_probe_urls: 250

rate_limit:
  enabled: true
  get_burst: 6
  post_invalid_attempts: 15
  post_targets: []           # v1 [rate_limit_post]

misc:
  max_pages_sample: 8
  max_html_bytes: 65536
  max_html_img_bytes: 98304
  show_probe_urls: true
  show_internal_urls: true
  max_probe_urls_display: 250
  max_internal_urls_display: 250

collectors:
  extensions:
    enabled: true            # Tier 2b — multi-framework (2.1.0a1)
  vuln:
    enabled: true            # Tier 3 — WordPress PLUGIN_CVE / THEME_CVE (shipped snapshot)
    source: cache            # cache | wpscan | wporg_only (wpscan = snapshot today)
    cache_enabled: true
    cache_path: ""           # default ~/.local/share/webaudit/vuln_cache.db
    cache_ttl_days: 14
    snapshot_path: ""        # default webaudit/data/vuln_snapshot.json
  dns:
    enabled: true
    check_spf: true
    check_dmarc: true
    check_dkim: false
    check_caa: true
    check_dnssec: true
    check_aaaa: true
    check_a: true
    check_mx: true
    check_ns: true
    check_asn: true            # Team Cymru DNS — no dig required
    use_host_tools: true       # detect dig/whois/host/mtr; run whois when present
  html:
    prefer_full_homepage_fetch: true   # full body stored as scan_html — used by extensions + attribution
    max_sitemap_urls: 500
  tls:
    enabled: true
    check_deprecated_versions: true
    check_chain: true
    check_ciphers: true
    check_ocsp: true
  js:
    enabled: false           # Tier 2 — requires playwright
    wait_seconds: 3
  api:
    enabled: false           # Tier 2
    graphql_probe: true
    openapi_paths: ["/swagger", "/api/docs", "/openapi.json"]
  seo_surface:
    enabled: true            # Tier 2c — INFO/VERIFY only
    check_meta_robots: true
    check_canonical: true
    check_meta_description: true
    check_open_graph: false
    check_broken_links: true
    max_internal_links_sample: 20

scoring:
  hygiene_weights:           # override defaults
    CRITICAL: 25
    HIGH: 10
    MEDIUM: 4
    LOW: 1
  hygiene_caps:              # Tier 2b — prevent extension pile-on
    PLUGIN: 30
    PLUGIN_CVE: 30
    PACKAGE: 30
    GEM: 30
  show_risk_index: false     # Tier 2
  hard_stops:
    - env_exposed
    - git_exposed
    - cert_expired
  plugin_worst_wins: true    # one worst plugin finding drives cap bucket
  seo_surface_affects_scores: false   # Tier 2c — must stay false in shipped defaults

report:
  variant: owner             # owner | executive | technical | minimal | dashboard | digest
  theme: dark                # dark | light | print
  language: en

output:
  directory: ./audit_logs    # or next to config
  formats: [html, json, txt, pdf, sarif]   # sarif → audit_run.sarif.json
  open_browser: false
  pdf:
    enabled: true
    engine: weasyprint       # weasyprint | xhtml2pdf

baseline:
  enabled: false             # Tier 2
  store: sqlite
  path: ~/.local/share/webaudit/baselines.db

ci:
  fail_under_hygiene: null
  fail_under_exposure: null

privacy:
  redact_ips: false
  redact_emails_in_report: true
```

---

## Per-site profile (`site.example.yaml`)

Maps directly from my v1 `site_configs/muzar.io.conf` mental model:

```yaml
host: muzar.io
framework: auto

paths:
  extra_get:
    - /about/
    - /portfolio/
    - /contact/

expected_open:
  /about/: app_surface
  /portfolio/: app_surface
  /robots.txt: public_seo

rate_limit:
  post_targets:
    - path: /api/contact
      probe_type: json

misc:
  max_pages_sample: 12

report:
  variant: technical

extensions:
  inherit_profile: true
  extra_watch:
    - custom-agency-plugin
  expected:
    - slug: wordfence
      note: "Client pays for premium license"
  ignore:
    - hello-dolly
```

---

## CLI overrides

```bash
webaudit scan https://muzar.io \
  --site-config site_configs/muzar.io.yaml \
  --report-variant executive \
  --sarif \
  --no-pdf \
  --fail-under-hygiene 80
```

| CLI flag | Config key | Notes |
|----------|------------|-------|
| `--sarif` | appends `sarif` to `output.formats` | Writes `audit_run.sarif.json` (SARIF 2.1.0) |
| `--json` | stdout only | Does not replace on-disk `audit_run.json` |
| `--js` | `collectors.js.enabled: true` | Playwright pass |
| `--api` | `collectors.api.enabled: true` | GraphQL / OpenAPI probes |

Flag → config key mapping documented in `webaudit scan --help`.

---

## Plugin/theme CVE cache (Tier 3)

**WordPress only.** After extensions/themes are fingerprinted, `_step_vuln` matches observed plugin/theme **versions** against a **shipped JSON snapshot** (`webaudit/data/vuln_snapshot.json`). Results appear as `PLUGIN_CVE` / `THEME_CVE` findings in `audit_run.json` and HTML reports (findings tables).

**Passive limit:** CVE matching requires a parseable version from public HTML/readme — same constraint as plugin fingerprinting. No wp-admin inventory.

### Config (`defaults.yaml`)

```yaml
collectors:
  vuln:
    enabled: true
    source: cache          # cache | wpscan | wporg_only
    cache_enabled: true
    cache_path: ""         # ~/.local/share/webaudit/vuln_cache.db when empty
    cache_ttl_days: 14
    snapshot_path: ""      # bundled snapshot when empty
```

WordPress profile override (`profiles/wordpress/extensions.yaml`):

```yaml
vuln:
  enabled: true
  source: cache
  cache_ttl_days: 14
  auth_required_default_class: VERIFY
  exposure_on_unauth_cve_only: true
```

### Auth-aware classes (see [scoring.md](scoring.md))

| CVE auth requirement | Finding class | Scored on Hygiene? | Exposure impact |
|----------------------|---------------|--------------------|-----------------|
| None / unauthenticated | ACTION | Yes | Critical unauth CVE: −25 Exposure |
| Contributor / Subscriber | VERIFY | No | No |
| Admin | INFO | No | No |

### Live WPScan API

`source: wpscan` is reserved for a future live API integration. **Today** all sources use the offline shipped snapshot (no network call, no API key).

Research basis and fixture table: [plugin_vulnerability_research.md](plugin_vulnerability_research.md) · theme CVEs: [wordpress_theme_threat_model.md](wordpress_theme_threat_model.md).

---

## SARIF export (GitHub Code Scanning)

SARIF **2.1.0** output for CI pipelines and GitHub Advanced Security code scanning integration.

**Enable either way:**

```bash
webaudit scan https://example.com --sarif --open none
```

```yaml
output:
  formats: [json, html, sarif]
```

**Output file:** `audit_logs/<timestamp>_<host>/audit_run.sarif.json`

**Contents:** Scored ACTION findings (headers, paths, TLS, `PLUGIN_CVE`, etc.) with rule IDs like `webaudit/plugin_cve/match`. VERIFY/INFO findings are omitted by default. Run metadata includes target URL, hygiene, exposure, verdict.

**Docker:** `./scripts/webaudit-docker.sh scan URL --sarif -v --open none` — flag passes through to the container; SARIF file is written into the mounted `audit_logs` volume.

Implementation: `webaudit/export/sarif.py`.

**Default product path:** HTML + `audit_run.json` for owner audits. SARIF is **opt-in** (`--sarif`). A sample GitHub Actions upload workflow is **TODO revisit later** — useful when scans run in CI on a schedule or when authenticated inventory makes SARIF more valuable for SecOps. See [implementation_tracker.md](implementation_tracker.md) § SARIF + CI / auth-aware scale.

---

**Planned (TODO — not implemented):** `--framework wordpress|django|…` scan flag and `webaudit config init --framework …` to emit a prebuilt site YAML (watchlist, paths, collectors) for editing. See [implementation_tracker.md](implementation_tracker.md) § Backlog / brainstorm. Without auth, prebuilt configs force the right *pipeline*, not full wp-admin plugin inventory.

---

## Validation rules (pydantic)

- `timeout_seconds`: 1–120
- `max_concurrency`: 1–32
- `report.variant`: enum
- `paths.extra_get`: must start with `/`
- `expected_open` labels: enum (`app_surface`, `public_seo`, `login_surface`, `staging`, `internal`)
- Unknown keys: **warn** in loose mode, **error** in `--strict-config`

---

## v1 INI → v2 YAML mapping

| v1 INI | v2 YAML |
|--------|---------|
| `[paths] extra=/foo/` | `paths.extra_get: [/foo/]` |
| `[expected_open] /foo/=app_surface` | `expected_open: {/foo/: app_surface}` |
| `[rate_limit_post] /x/=json` | `rate_limit.post_targets: [{path: /x/, probe_type: json}]` |
| `[misc] max_probe_urls=250` | `misc.max_probe_urls_display: 250` |
| `[misc] max_html_bytes=65536` | `misc.max_html_bytes: 65536` |

---

## Config mockup files

Working examples I can copy and edit:

- [../mockups/config/webaudit.example.yaml](../mockups/config/webaudit.example.yaml) — global/user
- [../mockups/config/site.example.yaml](../mockups/config/site.example.yaml) — per-site
- [../mockups/config/scoring_rules.example.yaml](../mockups/config/scoring_rules.example.yaml) — tunable finding severity
- [../mockups/config/profiles/](../mockups/config/profiles/) — framework profile examples (WordPress, Django, Laravel, generic)

---

## Framework profile examples

| Framework | Mockup path |
|-----------|-------------|
| WordPress | [profiles/wordpress/plugins.example.yaml](../mockups/config/profiles/wordpress/plugins.example.yaml) |
| Django | [profiles/django/packages.example.yaml](../mockups/config/profiles/django/packages.example.yaml) |
| Laravel | [profiles/laravel/packages.example.yaml](../mockups/config/profiles/laravel/packages.example.yaml) |
| Generic PHP | [profiles/generic/php.example.yaml](../mockups/config/profiles/generic/php.example.yaml) |

---

## Future: config validate command

```bash
webaudit config validate site_configs/muzar.io.yaml
# OK — 12 paths, framework auto, report variant technical

webaudit config explain scoring.hygiene_weights
# prints docstring + defaults
```

No scan, no network — for dev shops reviewing a config before handoff.

---

## Pipeline artifacts (HTML → extensions)

| Key | Set by | Used by |
|-----|--------|---------|
| `artifacts.inventory.html.scan_html` | `_step_html` when homepage fetched | `_step_extensions`, attribution in report |
| `artifacts.inventory.framework.body` | `_step_framework` (~8 KB sample) | Framework scoring only; extensions fallback |

Keep `collectors.html.prefer_full_homepage_fetch: true` unless you intentionally reuse the framework sample only.

---

*Related: [architecture.md](architecture.md) · [mockups/config/](../mockups/config/) · [framework_profiles.md](framework_profiles.md) · [seo_surface.md](seo_surface.md)*
