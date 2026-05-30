# Web Audit v2 — Configuration System

*How I plan to control the entire scanner from YAML — global defaults, per-site overrides, no magic constants buried in Python.*

---

## Why YAML (not INI, not Python dicts)

- Nested sections — DNS, TLS, report, scoring in one file
- Comments for humans (site owners sharing configs with devs)
- pydantic validation at load time
- Same files work for CLI, CI, and future GUI config editor

v1 INI (`site.conf.template`) maps to v2 in Tier 3 via `webaudit config migrate`. Until then, I document the v2 shape fresh.

---

## Config files (three layers)

| File | Scope | Example path |
|------|-------|--------------|
| **Global defaults** | Shipped with package | `webaudit/config/defaults.yaml` |
| **User config** | My machine defaults | `~/.config/webaudit/config.yaml` |
| **Site profile** | One hostname | `site_configs/example.com.yaml` |

Merge order (later wins): defaults → user → `--config` → site profile → CLI flags.

---

## Full schema overview

```yaml
# See mockups/config/webaudit.example.yaml for global
# See mockups/config/site.example.yaml for per-site

webaudit_version: "2.0"

target:
  url: ""                    # or pass on CLI
  framework: auto            # auto | django | wordpress | laravel | rails | php | unknown

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
  dns:
    enabled: true
    check_spf: true
    check_dmarc: true
    check_dkim: false
    check_caa: true
    check_dnssec: true
    check_aaaa: true
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

scoring:
  hygiene_weights:           # override defaults
    CRITICAL: 25
    HIGH: 10
    MEDIUM: 4
    LOW: 1
  show_risk_index: false     # Tier 2
  hard_stops:
    - env_exposed
    - git_exposed
    - cert_expired

report:
  variant: executive         # executive | technical | minimal | dashboard | digest
  theme: dark                # dark | light | print
  language: en

output:
  directory: ./audit_logs    # or next to config
  formats: [html, json, txt, pdf]
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
```

---

## CLI overrides

```bash
webaudit scan https://muzar.io \
  --site-config site_configs/muzar.io.yaml \
  --report-variant executive \
  --no-pdf \
  --fail-under-hygiene 80
```

Flag → config key mapping documented in `webaudit scan --help`.

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

*Related: [architecture.md](architecture.md) · [mockups/config/](../mockups/config/)*
