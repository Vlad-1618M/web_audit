# Web Audit.

**Zero Install external security hygiene checks for public websites** — one shell script, `curl` + `openssl` only.

Probe headers, TLS, paths, cookies, robots.txt, CORS, and login rate limits.<br> 
Gets **Hygiene** and **Exposure** scores with HTML, JSON, and terminal reports. Supports **Django**, **WordPress**, **Laravel**, **Rails**, and generic PHP.

> **Not** A: <br>Penetration test<br> Authenticated scanner <br>or a Replacement for OWASP ZAP / nuclei. <br>Use on sites you own or have explicit permission to test !

---

## Quick start

**Requirements:** zsh (macOS) or bash 4+, `curl`, `openssl`, standard Unix utilities. No pip/npm/Docker.

```bash
git clone git@github.com:Vlad-1618M/web_audit.git
cd web-audit

# Non-interactive (CI / SSH)
OPEN_BROWSER=0 zsh ./web_audit.sh --framework django https://example.com

# With per-site config
cp site.conf.template my-site.conf
OPEN_BROWSER=0 zsh ./web_audit.sh --config ./my-site.conf --framework django https://example.com
```

Reports are written to `audit_logs/` **next to the script** (cwd-independent).

---

## What it checks

| Area | Examples |
|------|----------|
| **Headers** | HSTS, CSP, X-Frame-Options, Referrer-Policy, version leaks |
| **TLS** | TLS 1.0–1.3, cert expiry, deprecated protocols |
| **Paths** | `.env`, `.git`, `wp-config.php`, `settings.py`, framework admin/API routes |
| **Cookies** | HttpOnly, Secure, SameSite (with framework-aware CSRF exceptions) |
| **Rate limits** | 6 rapid GETs + 15 invalid POSTs on login (+ config POST targets) |
| **Artifacts** | robots.txt parse + cross-check; security.txt fields; sitemap URL sample |
| **Policy** | HSTS max-age; CSP unsafe-inline / wildcards |
| **Transport** | Redirect chain; HTTP→HTTPS downgrade |
| **CORS** | Wildcard or reflected `Origin` on `/api/` paths |
| **Framework** | WP users enum, Django debug, Laravel debug, Rails info, plugin versions |
| **Attribution** | Designer/creator credits (Designed by, Powered by, …) — placement vs SEO |
| **Miscellaneous** | URL inventory (sitemap + probes + links), image count on sampled pages |

---

## How a site is evaluated (simple)

Think of the audit as **three passes** over your public URL:

>**1**. **Knock on doors (path probes)** — The script requests dozens of common paths (`.env`, `/wp-admin/`, `/api/`, etc.) and records what comes back: open (200), forbidden (403), missing (404), redirect, or error.<br></br>
>**2**. **Run security checks** — Separate modules test headers, TLS versions, cookies, login rate limits, robots.txt, CORS, redirects, and framework-specific issues. <br> Each result is tagged **ACTION**, **VERIFY**, **EXPECTED**, or **INFO**.<br></br>
>**3**. **Score and report** — Two numbers summarize the outcome: **Hygiene** (how well the site is hardened) and **Exposure** (whether sensitive files are reachable).<br>Everything else — remediation hints, artifacts, designer credits, URL/image lists — goes into HTML, JSON, and TXT reports.

Nothing runs JavaScript or logs in. <br>
You only see what an anonymous visitor (or bot) could see from the outside.

**Full pipeline, finding classes, and code references:** see [run_notes.md](run_notes.md#how-scoring-works-code-reference).

---

## Scores (the math in plain terms)

Both scores start at **100** and only go down. They measure different things.

### Hygiene / 100 — “How well is it configured?”

Counts **ACTION** findings that are marked **scored** (fixable config gaps: missing CSP, weak TLS, unprotected login POST, etc.).

| Severity | Points off |
|----------|------------|
| CRITICAL | −25 each |
| HIGH     | −10 each |
| MEDIUM   | −4 each |
| LOW      | −1 each |

**VERIFY**, **EXPECTED**, and **INFO** findings do **not** change Hygiene. Neither do random open pages marked REVIEW in the path table.

Example: 1 HIGH (−10) + 2 MEDIUM (−8) → **Hygiene = 82**.

Floor: **0** (never negative).

### Exposure / 100 — “Are secrets reachable?”

Only **sensitive paths** matter — e.g. `.env`, `.git`, `settings.py`, `wp-config.php`, database dumps (see `is_sensitive_path()` in the script).

| Event | Points off |
|-------|------------|
| Each sensitive path returning **200** or **5xx** | −25 |

Admin login pages, `robots.txt`, and routes you mark as expected-open in config do **not** lower Exposure.

Example: `.env` and `.git/HEAD` both return 200 → **Exposure = 50**. No sensitive leaks → **Exposure = 100**.

Floor: **0**.

## ! What the numbers are not !

- Not a penetration-test grade or compliance certificate.
- Not SEO or performance scores (designer-credit placement is informational only).
- Heuristics from one external snapshot — confirm VERIFY items in your CDN or app settings.

Implementation: `compute_scores()` in `web_audit.sh` — detailed walkthrough in [run_notes.md](run_notes.md#how-scoring-works-code-reference).

### Finding classes

| Class | Affects Hygiene? | Affects Exposure? | Meaning |
|-------|------------------|-------------------|---------|
| **ACTION** | Yes (if scored) | No | Fix or harden |
| **VERIFY** | No | No | May be OK at CDN — confirm manually |
| **EXPECTED** | No | No | Normal for the framework |
| **INFO** | No | No | Informational |

---

## CLI

| Flag | Purpose |
|------|---------|
| `--framework`, `-f` | `django` \| `wordpress` \| `laravel` \| `rails` \| `php` \| `auto` |
| `--config FILE` | Optional INI: extra paths, expected open routes, POST probes (skips auto-config prompts) |
| `--no-browser` | Skip opening HTML reports after the run |
| `--no-site-config` | Never load or create `site_configs/<host>.conf` |
| `--quiet` | Minimal terminal output |
| `--json-stdout` | Print last target JSON path on stdout |
| `--dry-run` | Show probe plan — no HTTP, no reports |
| `--compare FILE` | Drift vs previous audit JSON |
| `--fail-under-hygiene N` | Exit **1** if Hygiene &lt; N |
| `--fail-under-exposure N` | Exit **1** if Exposure &lt; N |
| `--throttle MS` | Sleep between path probes |

**Non-interactive:** pass URL(s) **and** `--framework`.

### CI example

```bash
OPEN_BROWSER=0 zsh ./web_audit.sh \
  --quiet --json-stdout \
  --framework django \
  --fail-under-hygiene 75 \
  --fail-under-exposure 100 \
  https://staging.example.com
```

### Drift example

```bash
OPEN_BROWSER=0 zsh ./web_audit.sh \
  --framework django \
  --compare audit_logs/prev/example.com/audit_*.json \
  https://example.com
```

---

## Site config (optional)

### Auto site config (interactive)

On an **interactive** run (TTY, not `--quiet`), the script can manage per-host configs under `site_configs/`:

| Situation | Behavior |
|-----------|----------|
| First audit of a host | Scans homepage + sitemap, writes a **rich** `site_configs/<hostname>.conf` (discovered URLs enabled + commented cookbook options), prompts **Y/n** |
| Same host again | Prompts to reuse the existing file (colored summary of what config adds vs built-in run) |
| `--quiet` / CI | Loads existing `site_configs/<host>.conf` silently if present; does not create or prompt |
| `--config FILE` | Uses your file for all targets; skips auto-config |
| `--no-site-config` | Built-in probes only |

`[paths] extra=` routes are also **sampled for misc URLs/images** (up to 8 pages total).

Edit any auto-generated file anytime — see `site.conf.template` and [run_notes.md](run_notes.md#with-config-vs-without-config).

### Manual config

```bash
cp site.conf.template my-site.conf
```

| INI section | Effect |
|-------------|--------|
| `[paths]` `extra=/path/` | Add GET probe paths + misc page/image sampling |
| `[expected_open]` `/path/=label` | Mark intentional 200s (not Exposure leaks) |
| `[rate_limit_post]` `/path/=type` | Extra POST abuse probes |

Example:

```ini
[paths]
extra=/design-ideas/

[expected_open]
/design-ideas/=public_seo

[rate_limit_post]
/api/chat/=json
```

Pass manual configs with `--config ./my-site.conf`.

---

## Reports

- **HTML** — findings, remediation hints, artifact details, **Miscellaneous** (URLs, images, designer credit), **Save as PDF** (dark theme; enable **Background graphics** in print dialog)
- **JSON** — `report_schema: "2.5"`, scores, checks, `artifacts`, `miscellaneous`, optional `compare`
- **TXT** — plain-text summary
- **Session index** — when auditing multiple URLs in one run

Report header shows **Website** and, when detected in an acceptable place, **Designer / Creator** next to it.

---

## Out of scope - TBD

- Authenticated / logged-in areas
- JavaScript / SPA crawling
- CVE exploit templates (use [nuclei](https://github.com/projectdiscovery/nuclei))
- Full sitemap crawl
- Compliance certification (PCI/SOC2/HIPAA)

POST rate-limit probes send **real invalid login traffic** — use responsibly.

---

## When to use something else

| Need | Tool |
|------|------|
| Authenticated scanning | OWASP ZAP, Burp, Playwright |
| CVE / template coverage | nuclei, Nikto |
| JS-heavy apps | Playwright, Lighthouse CI |
| Formal pentest | Qualified human tester |

**Workflow:** `web_audit.sh` for fast external hygiene → fix findings → escalate to heavier tools if needed.

---

## Repository layout

| File | Role |
|------|------|
| `web_audit.sh` | Main audit tool (v2.5) |
| `site.conf.template` | Per-site config template |
| `README.md` | Quick start, evaluation overview, score math |
| `run_notes.md` | Extended reference + code-level scoring/pipeline docs |
| `audit_logs/` | Generated reports (gitignored) |
| `site_configs/` | Auto-generated per-host configs (gitignored; interactive create) |

---

## Legal

For **authorized security assessment only**. Unauthorized scanning may violate terms of service or local law.

---

## Author

Created by **Vlad.M** — [muzar.io](https://muzar.io/) · [GitHub](https://github.com/Vlad-1618M)

MIT License — see [LICENSE](LICENSE).
