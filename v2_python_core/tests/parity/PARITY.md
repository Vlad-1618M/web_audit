# v1 → v2 parity matrix

Reference: repo root `web_audit.sh` (read-only). v2 code lives in `v2_python_core/webaudit/`.

**Tier 1 sign-off (2.0.0b1):** All v1-equivalent checks are implemented in Python. Intentional deltas are listed below.

## Module mapping

| v1 area | v1 (approx.) | v2 module | Parity |
|---------|--------------|-----------|--------|
| HTTP headers | `check_headers()` | `collectors/headers` + `analyzers/headers` | ✓ |
| CSP/HSTS parse | `check_policy_parse()` | `analyzers/policy` | ✓ |
| Sensitive paths | path probe loop | `collectors/paths` + `analyzers/paths` | ✓ |
| TLS | `check_tls()`, cert info | `collectors/tls` + `analyzers/tls` | ✓ |
| Cookies | Set-Cookie checks | `collectors/cookies` + `analyzers/cookies` | ✓ |
| Rate limit | login burst/POST | `collectors/rate_limit` + `analyzers/rate_limit` | ✓ |
| Artifacts | robots, security.txt | `collectors/artifacts` + `analyzers/artifacts` | ✓ |
| CORS | origin probes | `collectors/cors` + `analyzers/cors` | ✓ |
| Framework | `detect_framework()` | `collectors/framework` + `analyzers/framework` | ✓ |
| HTML inventory | regex misc | `collectors/html` + `analyzers/html` (BeautifulSoup) | ✓ improved |
| Scoring | Hygiene / Exposure | `scoring/engine.py` | ✓ |
| Reports | HTML/JSON/TXT | Jinja templates + `audit_run.json` | ✓ |
| DNS | — | `collectors/dns` + `analyzers/dns` | **new in v2** |
| Plugin versions | `check_plugin_versions()` | — | **Tier 2b** (profiles) |

## Intentional deltas

| Area | v1 | v2 (2.0.0b1) | Follow-up |
|------|-----|--------------|-----------|
| HSTS missing at CDN edge | VERIFY when CDN detected | ACTION (CDN not used for HSTS downgrade yet) | Tier 1 polish or 2.0.0 |
| PDF export | Browser `window.print()` only | Browser print (default) + optional WeasyPrint | By design |
| Plugin/CVE probes | Hardcoded readme.txt list | Not shipped | Tier 2b |
| INI site config | `site.conf` | YAML (`webaudit.yaml`, `--site-config`) | Tier 3 migrator |
| Output layout | User-chosen dir in v1 | `audit_logs/<stamp>_<host>/` | Documented |

## v2-only additions (not parity gaps)

- DNS: SPF, DMARC, CAA, AAAA, DNSSEC
- Structured `audit_run.json` (schema 2.0)
- Five HTML report variants + TXT + `webaudit report`
- Scan progress: default step logs, `-v` / `-q`
- Post-scan `--open` (html/json/all/none)

## How to regression-check

```bash
cd v2_python_core
.venv/bin/webaudit scan https://example.com --open none
# Compare findings categories vs v1 on same target (manual spot-check)
.venv/bin/python -m pytest -q
```

Automated v1-vs-v2 golden fixtures: planned; unit tests mock I/O today.
