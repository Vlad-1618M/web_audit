# v1 → v2 parity matrix

Reference: repo root `web_audit.sh` (read-only). v2 code lives in `v2_python_core/webaudit/`.

**Tier 1 sign-off (2.0.0b1):** All v1-equivalent checks are implemented in Python. Intentional deltas are listed below.

**Stage 5 (2.1.0b1):** Tier 2b extensions + DNS enrichment + owner report + baseline diff. Beta polish (bot protection, finding colors, dynamic focus pie) tracked in [CHANGELOG.md](../../CHANGELOG.md) `[Unreleased]`.

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
| HTML inventory | regex + misc URL scan | `collectors/html` + `site_discovery` + `sitemap` (BeautifulSoup) | ✓ improved |
| Designer credit | `extract_designer_from_html()` | `collectors/attribution` + report card (footer/context rules) | ✓ hardened (2.1.0a1) |
| Image inventory | sampled page images | `collectors/html` (favicon, og:image, lazy-load) | ✓ improved |
| Scoring | Hygiene / Exposure | `scoring/engine.py` | ✓ |
| Reports | HTML/JSON/TXT | Jinja templates + `audit_run.json` | ✓ improved |
| Plugin versions | `check_plugin_versions()` | `collectors/extensions/` + `analyzers/extensions` (HTML from `scan_html`) | ✓ improved (2.1.0a1) |
| DNS | — | `collectors/dns` + `analyzers/dns` | **new in v2** |
| ASN / WHOIS | — | `collectors/asn` + `collectors/net_tools` | **new in v2** |

## Intentional deltas

| Area | v1 | v2 (2.1.0b1) | Follow-up |
|------|-----|--------------|-----------|
| HSTS missing at CDN edge | VERIFY when CDN detected (unscored) | VERIFY when CDN detected | ✓ parity (2.1.0b1) |
| WAF / bot protection (captcha interstitial) | n/a | VERIFY when homepage blocked; framework hint from `robots.txt` | v2-only (Unreleased) |
| PDF export | Browser `window.print()` only | Browser print (default) + optional WeasyPrint | By design |
| Plugin/CVE probes | Hardcoded readme.txt list for high-risk slugs | Observed-only + framework profiles; no blind readme GET | Tier 2b ✓; CVE cache deferred |
| Plugin compare scope | WordPress readme + WPScan hints | WP + Django/Laravel/Rails registry compare | v2-only extension |
| INI site config | `site.conf` | YAML (`webaudit.yaml`, `--site-config`) | Tier 3 migrator |
| Output layout | User-chosen dir in v1 | `audit_logs/<stamp>_<host>/` | Documented |
| Designer findings | ATTRIBUTION checks in JSON | Same checks + dedicated report section | v2 UX only |
| Link discovery depth | Homepage + limited sampling | Full homepage fetch + sitemap index children | v2 improved |

## v2-only additions (not parity gaps)

- DNS: SPF, DMARC, CAA, A, AAAA, MX, NS, DNSSEC
- ASN lookup (Team Cymru DNS) for site IPv4/IPv6
- Optional domain WHOIS when `whois` binary exists on audit host
- Host net-tool detection note in report (`dig`, `whois`, `host`, `mtr`, `traceroute`)
- Structured `audit_run.json` (schema 2.0)
- Six HTML report variants + TXT + `webaudit report` (default **`owner`**: combined dashboard + executive + technical tab)
- Owner guide section: how to read the report, tool comparison, dev/QA suggestions
- Metric chips, plain-English DNS cards, leak-protection **/100** score labels in UI
- Framework extension intelligence (WordPress plugins, Django/Laravel packages, Rails gems)
- SEO surface analyzer (INFO/VERIFY only)
- `webaudit diff` baseline comparison
- Scan progress: default step logs, `-v` / `-q`
- Post-scan `--open` (html/json/all/none)

## How to regression-check

```bash
cd v2_python_core
.venv/bin/webaudit scan https://example.com --open none
# Compare findings categories vs v1 on same target (manual spot-check)
.venv/bin/python -m pytest -q
```

Automated v1-vs-v2 golden fixtures: planned; unit tests mock I/O today (~169 unit tests).
