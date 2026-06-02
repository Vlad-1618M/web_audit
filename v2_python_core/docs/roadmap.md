# Web Audit v2 — Roadmap

*First-person plan. v1 bash stays public and unchanged.*

---

## My goal

Build **Web Audit v2** as a modular Python application that:

1. **Matches v1** where it matters — same ethical scope, familiar Hygiene/Exposure story, compatible config concepts.
2. **Exceeds v1** in reported data — DNS, deep TLS, real HTML parsing, optional JS pass, native PDF.
3. **Serves two audiences** — me in the terminal, and a site owner who never wants to see a terminal.
4. **Ships in tiers** — Tier 1 is usable early; Tier 2/3 stack on without rewrites.

---

## What v1 already does well (I keep this)

From `web_audit.sh` v2.5:

- External path probes (`.env`, `.git`, framework admin routes, etc.)
- HTTP security headers (HSTS, CSP, X-Frame-Options, …)
- TLS version probes + certificate expiry via OpenSSL
- Cookie flag checks (HttpOnly, Secure, SameSite)
- Login rate-limit heuristics (GET burst + invalid POSTs)
- robots.txt / security.txt / sitemap artifact parsing
- CORS checks on API paths
- Framework-specific heuristics (WordPress, Django, Laravel, Rails)
- Designer/creator attribution scan
- Miscellaneous URL inventory (security probes vs internal routes)
- Image inventory on sampled pages
- Hygiene + Exposure scores
- HTML / JSON / TXT reports
- Per-site INI config (`site.conf.template` concepts)
- Browser “Save as PDF” via `window.print()` (works, but browser-dependent)

I am not throwing this away conceptually. v2 **reimplements** it cleanly, then **extends** it.

---

## Where v1 hits a wall (why Python)

| Limitation in bash | What v2 adds |
|--------------------|--------------|
| `grep`/`sed` HTML parsing | **BeautifulSoup / lxml** — forms, scripts, SRI, mixed content |
| No DNS at all | **dnspython** — SPF, DMARC, CAA, AAAA, DNSSEC |
| Basic TLS handshake yes/no | **cryptography + ssl** — chain, ciphers, SAN, OCSP |
| No JavaScript | **Playwright** (optional `--js`) — SPA links, client bundles |
| Monolithic ~4k lines | **Packages** — one module per concern, pytest per module |
| PDF = browser print dialog | **WeasyPrint** (or similar) — server-side PDF, no Chrome required |
| Weak baseline/diff story | **sqlite + structured diff** — “what changed since last run” |
| Regex CSP/HSTS | Dedicated **policy parsers** — structured weak-CSP findings |
| v1 plugin readme only, blind high-risk list | **Framework profiles** + wp.org compare + optional CVE cache ([plugin research](plugin_vulnerability_research.md)) |

I have used **httpx** and **dnspython** before; they are proven choices for me, not experiments.

---

## v2 capability map (high level)

### Core platform (all tiers)

- CLI: `webaudit scan`, `webaudit report`, `webaudit diff`, `webaudit config validate`
- Config: global YAML + per-site YAML (INI import optional for v1 migration)
- Artifact: **`audit_run.json`** — single contract between collect → analyze → score → render
- Reports: Jinja2 templates in `templates/reports/` — **not** inside Python modules
- Outputs: HTML, JSON, TXT, **PDF** (native)
- Scoring: Hygiene, Exposure, overall **Verdict** (see [scoring.md](scoring.md))
- Tests: pytest from day one of code (see [testing.md](testing.md))

### Improvements over v1 by area

**Transport & HTTP**

- HTTP/2 awareness via httpx
- Redirect chain with per-hop header capture
- Response size limits and anomaly flags

**Headers & policy**

- Deep CSP analysis (unsafe-inline, wildcards, missing directives)
- COOP / COEP / CORP presence
- Permissions-Policy parsing

**TLS & certificates**

- Full chain validation
- Weak cipher / key size detection
- HSTS preload list check
- CAA record report

**DNS & domain hygiene**

- SPF, DMARC, DKIM selector discovery (DKIM optional/off by default)
- A, AAAA, MX, NS records in report + JSON
- ASN / hosting network (Team Cymru DNS lookup)
- Optional domain WHOIS when `whois` binary on audit host
- IPv6 (AAAA) published vs reachable
- Passive subdomain hints (CT API — Tier 2)

**Content & surface**

- Form inventory (method, autocomplete, CSRF token hints)
- Third-party script inventory
- Mixed content detection
- Broken link sampling

**Discoverability (Tier 2c — informational only)**

- Meta robots / noindex, canonical, meta description — **INFO/VERIFY**
- robots.txt vs sitemap cross-check (extends artifacts)
- **No SEO success score** — primary scores stay Hygiene + Exposure
- See [seo_surface.md](seo_surface.md)

**Framework & API**

- GraphQL introspection probe (Tier 2)
- OpenAPI/Swagger discovery (Tier 2)
- Richer WordPress/Django/Laravel signals
- **WordPress plugin intelligence (Tier 2b)** — framework profile auto-load, version compare, auth-aware CVE, no “nulled” accusations in output
- **Django/Laravel/Rails profiles (Tier 2b)** — package/gem registry compare + debug/disclosure VERIFY signals

**UX & audience**

- **Owner** report variant (default) — Security dashboard + Executive summary + Technical tab; owner guide; honest plugin/extension counts
- **Executive** report variant — plain language, traffic-light summary
- **Technical** report variant — findings tables, remediation, evidence
- **Minimal** report variant — one-page printable handoff for dev shops
- PDF export without opening a browser

---

## What v2 is NOT (same as v1)

- Not authenticated scanning
- Not a replacement for OWASP ZAP, nuclei, or a pentest
- Not an SEO ranking / lead-generation tool (Tier 2c is INFO/VERIFY discoverability only)
- Not Scapy-driven packet crafting (I was speculating; out of scope)
- Not Windows support in Tier 1 (Unix + pipx first; Windows later if demand exists)

---

## Milestones (see [stages.md](stages.md) for detail)

| Milestone | Outcome |
|-----------|---------|
| **M0 — Docs** | This directory complete (done when code starts) |
| **M1 — Skeleton** | Package layout, config load, empty scan, JSON shell |
| **M2 — Tier 1 parity+** | v1-equivalent checks in Python + DNS + TLS depth |
| **M3 — Reports** | Three template variants + PDF |
| **M4 — Tier 2** | JS pass, API probes, baselines |
| **M4b — Tier 2b** | Framework profiles, multi-framework extension/version module | ← **2.1.0a1 (alpha)** |
| **M4c — Tier 2c** | SEO surface checks (INFO/VERIFY only) |
| **M5 — Tier 3** | CT subdomains, vuln snapshot, SARIF export |
| **M6 — Install** | pipx, Homebrew formula, docs for non-terminal users |

---

## Success criteria (how I know v2 is “real”)

1. I can audit **muzar.io** with v2 and get **strictly more signal** than v1 in the JSON.
2. A non-dev can run **`webaudit scan https://their-site.com`** after one-line install and open an **Executive HTML** they understand.
3. PDF generates on a **headless CI runner** with no browser.
4. pytest green; parity fixtures document any intentional v1 differences.
5. v1 repo path unchanged — zero edits to `web_audit.sh` for a v2 release.

---

## Dependency philosophy

- Prefer **maintained, boring** libraries over novelty
- Keep **optional deps** isolated (`[js]` extra for Playwright, `[pdf]` for WeasyPrint)
- No template HTML inside `.py` files — ever

Full library list per tier: [stages.md](stages.md) and [architecture.md](architecture.md).

Plugin/extension planning: [plugin_vulnerability_research.md](plugin_vulnerability_research.md) · [framework_profiles.md](framework_profiles.md).

SEO surface (informational): [seo_surface.md](seo_surface.md).

---

*Next: [stages.md](stages.md) — what ships when, and what goes in each tier.*
