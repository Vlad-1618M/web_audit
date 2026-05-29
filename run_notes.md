# Web Security Audit Tool — extended reference

> **Start here:** [README.md](README.md) — quick start, CI examples, and repo overview.  
> This file is the full reference (same tool, more detail).

**Script:** `web_audit.sh` (v2.5)  
**Related:** `site.conf.template`, optional per-site `*.conf`

External security hygiene checks for public websites — mostly passive GET probes, plus deliberate POST abuse tests on login and configured API endpoints.

**This is not:**

- A penetration test
- Authenticated scanning
- A replacement for OWASP ZAP, nuclei, or professional audit platforms

Generated HTML/JSON reports include vendor branding (see `web_audit.sh`); usage and config examples below are generic.

---

## Requirements

| Requirement | Notes |
|-------------|--------|
| **Shell** | **zsh** (recommended on macOS) or **bash 4+**. macOS default bash 3.2 is too old — the script auto-re-execs with zsh if available. |
| **curl** | HTTP probes, headers, cookies, redirects. Usually preinstalled. |
| **openssl** | TLS version handshakes (1.0–1.3) and certificate subject/issuer/expiry. Usually preinstalled. |
| **sed, grep, mktemp, date, mkdir, hostname** | Standard Unix utilities. |
| **Network** | Outbound HTTP/HTTPS to the target URL(s). |
| **Authorization** | Only scan sites you own or have **explicit permission** to test. POST rate-limit probes send invalid login/API traffic. |

Nothing to install via pip/npm. No database, daemon, or API keys.

The script is **cwd-independent**: logs are written next to `web_audit.sh`, so you can run it from any directory or copy the folder elsewhere.

```bash
cd /path/to/web_audit          # directory containing web_audit.sh

# Non-interactive (recommended for CI / SSH)
OPEN_BROWSER=0 zsh ./web_audit.sh \
  --framework django \
  https://example.com

# With optional site config
OPEN_BROWSER=0 zsh ./web_audit.sh \
  --config ./my-site.conf \
  --framework django \
  https://example.com

# Multiple URLs in one session
OPEN_BROWSER=0 zsh ./web_audit.sh \
  --framework wordpress \
  https://example.com https://staging.example.com
```

**Non-interactive checklist:** pass at least one URL **and** `--framework` (or `-f`). Without `--framework`, the script prompts on stdin even when URLs are provided.

### Optional environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPEN_BROWSER` | `1` (browser opens) | Set to `0` to skip opening HTML reports and live sites after the run |
| `TMPDIR` | `/tmp` | Temp files for POST rate-limit probes |

### CLI flags

| Flag | Purpose |
|------|---------|
| `--config FILE` | Load optional INI (see below). **Never auto-selected by hostname.** Skips auto site-config prompts. |
| `--no-site-config` | Never load or create `site_configs/<host>.conf` |
| `--framework`, `-f` | `django` \| `wordpress` \| `laravel` \| `rails` \| `php` \| `auto` |
| `--no-browser` | Same as `OPEN_BROWSER=0` |
| `--quiet` | Minimal terminal output (errors still shown) |
| `--json-stdout` | Print path to last target JSON report on stdout when done |
| `--dry-run` | Show probe/check plan without sending HTTP traffic |
| `--compare FILE` | Compare scores to a previous audit JSON (drift section in report) |
| `--fail-under-hygiene N` | Exit code **1** if Hygiene &lt; N |
| `--fail-under-exposure N` | Exit code **1** if Exposure &lt; N |
| `--throttle MS` | Sleep between path probes (polite mode) |
| `-h`, `--help` | Usage text |

```bash
# CI gate (native exit codes)
OPEN_BROWSER=0 zsh ./web_audit.sh \
  --quiet --json-stdout \
  --framework django \
  --fail-under-hygiene 80 \
  --fail-under-exposure 100 \
  https://staging.example.com

# Drift check vs last run
OPEN_BROWSER=0 zsh ./web_audit.sh \
  --framework django \
  --compare audit_logs/prev/example.com/audit_*.json \
  https://example.com

# Plan only (no traffic, no reports)
zsh ./web_audit.sh --dry-run --framework django https://example.com
```

If you omit URLs, the script prompts interactively for URL(s) and framework.

### Output location

Each run creates a session folder **next to `web_audit.sh`** (not in your current working directory):

```
audit_logs/YYYY-MM-DD_HHMMSS/
  session_*.txt / session_*.json     # index for multi-URL runs
  <host-slug>/
    audit_<host>_<date>_<time>.txt
    audit_<host>_<date>_<time>.json
    audit_<host>_<date>_<time>.html
```

---

## With config vs without config

### Auto site config (`site_configs/<hostname>.conf`)

On **interactive** runs (terminal TTY, not `--quiet`):

1. **No file yet** — script fetches homepage + sitemap(s), writes a **rich** `site_configs/<hostname>.conf`: discovered paths (first 8 **enabled**, rest **commented**), plus commented common/framework extras and `[rate_limit_post]` examples — prompts **Use for this run? [Y/n]**.
2. **File exists** — prompts **Use existing config? [Y/n]**; if yes, prints a colored summary of extra probes, expected-open marks, POST targets vs a config-less run.
3. **Decline (n)** — audit continues with built-in probes only; saved file remains for next time.

**Non-interactive** (`--quiet`, CI, pipes): loads existing `site_configs/<host>.conf` if present (no prompt, no auto-create). Use `--config FILE` to pin a config, or `--no-site-config` to disable.

**`[paths] extra=`** entries are merged into security probes **and** misc page/image sampling (priority after homepage, before sitemap; max 8 pages).

Reference: `resolve_config_for_target()` and `discover_site_paths()` in `web_audit.sh`.

### Without `--config` or site config (default)

Works out of the box for any public HTTP/HTTPS URL.

**You get:**

- Framework detection (or use `--framework` to pin the stack)
- Built-in path lists: **common** + **framework-specific** probes (~50 paths for a single forced framework; ~100+ when detection is inconclusive)
- All security check modules (headers, TLS, cookies, rate limits, etc.)
- Dual scores: **Hygiene** and **Exposure**
- TXT, JSON, and HTML reports

**You do not get:**

- Extra app routes (e.g. `/app/`, `/portal/`) unless they appear in built-in lists
- Custom “expected open” classification for site-specific pages
- Extra POST rate-limit targets (e.g. `/api/chat/`)

**Implications:** Site-specific public pages that return **200** may show as **REVIEW** in the path summary unless they match built-in rules (admin login, `robots.txt`, etc.). **REVIEW does not change Hygiene or Exposure scores** — it is manual triage noise. Only **sensitive** paths (`.env`, `.git`, etc.) lower Exposure.

### With `--config` or site config

Copy the template, use auto-generated `site_configs/<host>.conf`, or pass `--config`:

```bash
cp site.conf.template my-site.conf
# edit my-site.conf, then:
OPEN_BROWSER=0 zsh ./web_audit.sh --config ./my-site.conf --framework django https://example.com
```

| INI section | Effect |
|-------------|--------|
| `[paths]` `extra=/path/` | Add paths to GET probes **and** misc URL/image sampling (up to 8 pages) |
| `[expected_open]` `/path/=label` | Mark intentional 200s — not counted as Exposure leaks. Label `app_surface` gets dedicated report wording; other labels (`public_seo`, `staging`, `internal`, `login_surface`) suppress leak scoring but show as “expected (config)” in the path summary. |
| `[rate_limit_post]` `/path/=type` | Extra POST abuse probes (`json`, `django_admin`, `wordpress`, `laravel`, `rails`, `form`) |

Config via `--config` is explicit. Auto configs live in `site_configs/` (gitignored) unless you pass `--no-site-config`.

Reference sections in `site.conf.template` (SEO, bots, static assets) are **documentation for humans** — only the three sections above are parsed by the script.

---

## What the script can do

### HTTP surface mapping

- Probes many URLs with **raw** and **follow-redirect** status codes
- Classifies paths: sensitive leak, login surface, public-by-design, app surface (config), review needed
- Detects CDN (Cloudflare, CloudFront, Fastly, Akamai, Varnish) and stack hints

### Security checks (always run)

| Module | What it checks |
|--------|----------------|
| **Headers** | HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy; X-Powered-By / Server version leaks |
| **TLS** | OpenSSL handshakes for TLS 1.0–1.3; cert subject, issuer, expiry |
| **Cookies** | HttpOnly / Secure / SameSite on Set-Cookie; framework exceptions (Django `csrftoken`, Laravel `XSRF-TOKEN`, Cloudflare cookies) |
| **Rate limiting** | 6 rapid GETs on login URL; 15 invalid POSTs on login (+ config POST targets) |
| **Directory listing** | Index-of style responses on open directory paths |
| **Version disclosure** | WP readme/license, generator tags, framework debug pages, etc. |
| **API / content** | WP REST users, Django API/schema paths, Laravel `/api/user` |
| **Open redirect** | Common `?url=` / `?next=` parameter patterns |
| **Plugin versions** | WordPress plugin readme/version probes (high-risk plugin list) |
| **Framework specifics** | WP xmlrpc/cron/author enum; Django debug/silk signals; Rails info pages |
| **Policy parse** | HSTS max-age / includeSubDomains; CSP unsafe-inline, unsafe-eval, wildcards |
| **Transport** | Redirect chain tracing; HTTP→HTTPS downgrade probe |
| **Artifacts** | **robots.txt** parsed (Disallow/Allow/Sitemap) + cross-check vs probed OPEN paths; **security.txt** field parse + Expires; **sitemap.xml** URL sample |
| **CORS** | `Origin: https://evil.example.com` on `/api/` paths — wildcard/reflected origin |
| **HTTP methods** | TRACE / OPTIONS on homepage and login URL |
| **General** | `/.well-known/security.txt` presence |
| **Attribution** | Designer/creator credits (Designed by, Powered by, …) — placement vs SEO risk |
| **Miscellaneous** | URL inventory (sitemap up to 150 URLs + probes + links); image count on sampled pages |

### Framework support

| `--framework` | Built-in path set | Login POST probe |
|---------------|-------------------|------------------|
| `django` | `/admin/login/`, `/api/`, `/static/`, `/settings.py`, … | CSRF-aware admin login |
| `wordpress` | `/wp-admin/`, `/wp-json/`, `/xmlrpc.php`, … | `wp-login.php` |
| `laravel` | `/telescope`, `/horizon`, `/storage/logs/…`, … | `/login` + `_token` |
| `rails` | `/rails/info`, `/sidekiq`, … | `/users/sign_in` |
| `php` | Generic admin/login/phpmyadmin paths | Generic form POST |
| `auto` | Runs detection, then **one** stack’s paths (+ common) | Best-effort by detection |
| `unknown` / `blocked` | **All** framework lists (noisier) | Best-effort by detection |

- **`auto`** — detect framework from headers/cookies/body, then probe that stack only.
- **`unknown`** — detection found no confident match; all built-in lists run.
- **`blocked`** — site appears to block curl; all lists run (results may be unreliable).

Forced framework (`--framework django`, etc.) skips detection for path selection but still runs CDN/UA probing for headers and cookies.

---

## How the audit runs (pipeline)

Plain-language overview: [README.md — How a site is evaluated](README.md#how-a-site-is-evaluated-simple).

End-to-end flow in `run_single_audit()` (~2781–2905 in `web_audit.sh`):

```
load config → build probe list → probe_path (each URL)
  → check_headers … check_artifacts → check_site_miscellaneous → check_cors …
  → compute_scores → write_logs (TXT / JSON / HTML)
```

| Step | What happens | Code |
|------|----------------|------|
| Path probes | GET each path; record raw/final status in `R_PATH` / `R_NOTE` | `probe_path()`, loop ~2852 |
| Security modules | Headers, TLS, cookies, rate limits, artifacts, misc, CORS, … | `check_*()` ~2859–2874 |
| Findings | Each result appended to `SEC_CHECKS` with class + scored flag | `add_check()` ~369–378 |
| Scores | Hygiene from ACTION/scored; Exposure from sensitive OPEN/5xx | `compute_scores()` ~2153–2189 |
| Reports | HTML + JSON + TXT under `audit_logs/` | `write_html_report()` ~2355+, `write_logs()` |

**Path classification helpers:**

- `is_sensitive_path()` (~409–422) — `.env`, `.git`, `settings.py`, `wp-config.php`, dumps, etc.
- `is_expected_open()` (~440–445) — robots, login surfaces, config `expected_open` routes
- `is_scored_exposure()` (~470–475) — only sensitive paths count toward Exposure
- `is_unexpected_exposure()` (~460–468) — non-sensitive 200s (REVIEW in path table; no score hit)

---

## How scoring works (code reference)

Simple math summary: [README.md — Scores](README.md#scores-the-math-in-plain-terms).

### Finding record — `add_check()`

Each finding is stored in `SEC_CHECKS` as:

`CATEGORY|ITEM|STATUS|SEVERITY|CLASS|SCORED|DETAIL`

```365:378:web_audit.sh
# Finding record: CATEGORY|ITEM|STATUS|SEVERITY|CLASS|SCORED|DETAIL
# CLASS: ACTION | VERIFY | EXPECTED | INFO
# SCORED: yes | no (only ACTION findings with scored=yes affect hygiene score)

add_check() {
  local category="$1" item="$2" check_status="$3" severity="$4" detail="$5"
  local class="${6:-ACTION}" scored="${7:-yes}"
  ...
  SEC_CHECKS+=("${category}|${item}|${check_status}|${severity}|${class}|${scored}|${detail}")
}
```

OK/PROTECTED-style statuses are auto-downgraded to **INFO** with `scored=no` (~372–376).

Parse fields in reports with `parse_check()` (~380–388).

### Hygiene — ACTION + scored=yes only

```2160:2175:web_audit.sh
  for check in "${SEC_CHECKS[@]}"; do
    parse_check "$check"
    case "$PC_STATUS" in OK|PROTECTED*|REJECTED|SUPPORTED|PRESENT|SECURE|OFF|NONE_FOUND|EXPECTED) continue ;; esac
    case "$PC_CLASS" in
      ACTION)
        [[ "$PC_SCORED" != "yes" ]] && continue
        case "$PC_SEV" in
          CRITICAL) ... SCORE_HYGIENE=$((SCORE_HYGIENE-25)) ;;
          HIGH)     ... SCORE_HYGIENE=$((SCORE_HYGIENE-10)) ;;
          MEDIUM)   ... SCORE_HYGIENE=$((SCORE_HYGIENE-4)) ;;
          LOW)      ... SCORE_HYGIENE=$((SCORE_HYGIENE-1)) ;;
        esac ;;
      VERIFY)  ... ;;
      EXPECTED) ... ;;
    esac
  done
```

| Severity | Hygiene penalty |
|----------|-----------------|
| CRITICAL | −25 |
| HIGH | −10 |
| MEDIUM | −4 |
| LOW | −1 |

**VERIFY**, **EXPECTED**, and **INFO** never subtract. Path-table **REVIEW** rows (non-sensitive 200s) do not affect Hygiene.

### Exposure — sensitive path leaks only

```2177:2188:web_audit.sh
  for (( i=0; i<total; i++ )); do
    if is_scored_exposure "${R_PATH[$i]}" "${R_NOTE[$i]}"; then
      SCORE_SENSITIVE=$((SCORE_SENSITIVE+1))
      SCORE_EXPOSURE=$((SCORE_EXPOSURE-25))
    elif is_unexpected_exposure "${R_PATH[$i]}" "${R_NOTE[$i]}" && ! is_sensitive_path "${R_PATH[$i]}"; then
      SCORE_EXPOSED=$((SCORE_EXPOSED+1))
    fi
  done

  [[ $SCORE_HYGIENE -lt 0 ]] && SCORE_HYGIENE=0
  [[ $SCORE_EXPOSURE -lt 0 ]] && SCORE_EXPOSURE=0
```

Sensitive list (excerpt):

```409:421:web_audit.sh
is_sensitive_path() {
  case "$1" in
    /.env|/.env.local|/.env.production|/.env.backup \
    |/.git/HEAD|/.git/config \
    |/backup.zip|/backup.tar.gz|/dump.sql|/db.sql \
    |/wp-config.php|/wp-config.php.bak \
    |/config.py|/config.php|/configuration.php \
    |/settings.py|/local_settings.py|/secrets.py \
    ...
```

**−25** per sensitive path with **OPEN** (200) or **5xx**. Admin login, `robots.txt`, and `[expected_open]` config paths are excluded via `is_expected_open()`.

### What does not affect scores

| Item | Why |
|------|-----|
| VERIFY / EXPECTED / INFO | Not ACTION, or `scored=no` |
| MISC URL/image inventory | INFO checks with `scored=no` (~1431–1432) |
| Designer in footer or HTML comment | EXPECTED (~1478–1486) |
| Designer in `<title>` or hidden CSS | ACTION with `scored=yes` — **does** reduce Hygiene (~1488–1495) |
| Non-sensitive OPEN paths | Counted in `SCORE_EXPOSED` for reporting only; no Exposure penalty |

### Worked examples

**Hygiene:** TLS 1.0 (HIGH, −10) + missing CSP (MEDIUM, −4) + HSTS missing (MEDIUM, −4) → **82**.

**Exposure:** `/.env` OPEN + `/.git/HEAD` OPEN → 100 − 50 = **50**. No sensitive leaks → **100**.

---

## Miscellaneous & attribution — `check_site_miscellaneous()`

~1363–1503 in `web_audit.sh`. Runs after `check_artifacts` (sitemap already parsed).

**Designer discovery (stack-agnostic):** Homepage HTML first; if no credit, scans any **OPEN probed path ending in `/`** (and config `[paths] extra=`) — not tied to one CMS. Malformed HTML comments are supported.

**Open path + HTML:** `check_dir_listing()` emits **DIR_LISTING / HTML_DOCUMENT** (INFO) when a directory-style URL returns a full HTML page instead of an index listing.

**Attribution INFO:** **Credit off homepage** when the designer name was read from a non-root URL.

**URL inventory:** Registers probe paths first (~1382–1384), then sitemap URLs (up to **150** from `check_artifacts` ~1137), robots sitemaps, homepage links, and up to **8** sampled pages (~1408–1429). Dedup via `misc_register_url()`.

**Images:** `collect_images_from_html()` / `misc_register_image()` — unique `src` on sampled pages.

**Credit patterns:** Designed by, Created by, Developed by, Built by, Powered by, Made by, Coded by, Theme by, Author:, Creator:, etc. CMS boilerplate filtered via `is_credit_noise()`.

| Placement | Typical class | SEO note |
|-----------|---------------|----------|
| HTML comment | EXPECTED | Not indexed — no harm (~1481–1483) |
| Visible footer / body | EXPECTED | Normal credit (~1485–1486) |
| `<meta>` / JSON-LD | VERIFY | Confirm owner intent (~1491–1492) |
| `<title>` | ACTION (scored) | Can dilute SERP title (~1488–1489) |
| Hidden (CSS) | ACTION (scored) | Hidden-text risk (~1494–1495) |

**Report header:** Always shows **Designer / Creator** — name when found (with proper/risky note), or **Not detected**. Includes path when credit came from a non-homepage URL.

**HTML section:** `html_emit_misc_section()` ~2294+ — designer trace table, clickable URL catalog (source tags: `security_probe`, `sitemap.xml`, `homepage_links`, …), image list (display cap 250).

**JSON:** Top-level `"miscellaneous": { "designer", "urls", "images" }` — not nested under `artifacts`.

**Important:** No designer name in the report means **no credit pattern matched** — not “no SEO issues overall.”

### Finding model (summary)

Each finding has a **class**:

| Class | Affects Hygiene? | Affects Exposure? | Meaning |
|-------|------------------|-------------------|---------|
| **ACTION** (scored=yes) | Yes | No | Fix or harden (CSP missing, TLS 1.0, designer in title, …) |
| **VERIFY** | No | No | Confirm at CDN/app (HSTS behind Cloudflare, meta author, …) |
| **EXPECTED** | No | No | Normal behavior (CSRF cookie, comment-only designer credit, …) |
| **INFO** | No | No | Informational (URL/image counts, designer detected) |

**Hygiene / 100** and **Exposure / 100** — see [How scoring works](#how-scoring-works-code-reference) above.

### Reports

- **Terminal** — colored summary, path table, scores
- **HTML** — grouped Action / Verify / Expected / Info, remediation hints, scores, **Discovered Artifacts**, **Miscellaneous** (designer trace, URL catalog, images), report header with Website + Designer when credible; **Save as PDF** (dark theme — enable **Background graphics** in print dialog)
- **JSON** — `report_schema: "2.5"`, checks, scores, `artifacts`, `miscellaneous`, optional `compare`
- **Session index** — when auditing multiple URLs in one run

### CI integration

Use built-in thresholds instead of parsing JSON manually:

```bash
OPEN_BROWSER=0 zsh ./web_audit.sh \
  --quiet --json-stdout \
  --framework django \
  --fail-under-exposure 100 \
  --fail-under-hygiene 75 \
  https://staging.example.com
echo "exit=$?"   # 0 = pass, 1 = threshold breach
```

With `--json-stdout`, stdout is the path to the last target JSON (one line) — useful for downstream tooling.

### Saving HTML as PDF

Open the HTML report in any browser and click **Save as PDF** (uses `window.print()`). Choose “Save as PDF” / “Microsoft Print to PDF” as the destination. PDF output keeps the **dark theme** — enable **Background graphics** in the print dialog so backgrounds and badge colors render correctly.

---

## What the script cannot do

| Limitation | Detail |
|------------|--------|
| **No authentication** | Cannot test logged-in areas, role-based access, or session fixation after real login |
| **No CDN dashboard access** | Cannot see Cloudflare WAF rules, Page Rules, or origin-only headers — only what the edge returns |
| **No deep app logic** | No business-rule bugs, payment flows, IDOR with real IDs, or multi-step workflows |
| **No JavaScript execution** | No SPA routing audit, client-side secrets, or post-render DOM (use Playwright/browser tools) |
| **robots.txt scope** | Parses Disallow/Allow/Sitemap and cross-checks probed paths; sitemap sample up to 150 URLs — does not crawl the entire site |
| **Limited SEO audit** | Designer/creator **placement** only — not full `<title>`, Open Graph, canonical, or Lighthouse scores |
| **No continuous monitoring** | One-shot manual/CI run; no alerting or drift history (unless you wrap it) |
| **No CVE/exploit scanning** | Plugin version hints only; no nuclei-style exploit templates |
| **Rate-limit probes are coarse** | 15 POSTs may miss slow thresholds; CSRF failures can look “unprotected”; CDN may absorb abuse |
| **False positives / negatives** | Shared hosting, bot challenges, geo blocks, and WAF can skew results |
| **Config reference blocks** | SEO/bot/static sections in `site.conf.template` are checklists — not executed by the script |
| **Not a compliance certificate** | Does not map cleanly to PCI/SOC2/HIPAA without a broader program |

**POST probes:** Invalid credentials on login and JSON POSTs to configured APIs generate **real traffic**. Use only on sites you control; avoid production during sensitive windows if you prefer.

---

## Why shell (bash/zsh)

1. **Zero install footprint** — runs on a developer laptop, CI runner, or SSH box with only curl/openssl.
2. **Ops-friendly** — one file, easy to read, grep, and patch; no virtualenv or container required for a quick check.
3. **Glue language fit** — orchestrating HTTP (`curl`), TLS (`openssl s_client`), text parsing (`grep`, `sed`), and report generation is what shell does well.
4. **Portable across macOS and Linux** — with zsh/bash 4+ handling.
5. **Honest scope** — external checks are mostly subprocess + string matching; a single shell script stays maintainable for a small team.

Shell is a poor fit when you need rich data structures, async concurrency, HTML/DOM parsing, plugin ecosystems, or long-term test suites — hence the boundaries above.

---

## Where to use this vs other tools

### Good fits (this script’s lane)

- Pre-deploy or post-deploy **smoke security checks** on staging/prod URLs
- **Developer laptop** audits before opening a hardening ticket
- **CI gate** with `--fail-under-hygiene` / `--fail-under-exposure` and optional `--compare` drift
- **Multi-site portfolio** spot checks with the same script and different `--config` files
- **Hosting handoff** — HTML report for a contractor (“fix these headers / paths”)
- **Regression after infra changes** — TLS min version, new CDN, new public routes

### When to reach for more powerful tools

| Need | Better options |
|------|----------------|
| Authenticated scanning | OWASP ZAP (auth context), Burp Suite, custom Playwright flows |
| Large template/CVE coverage | [nuclei](https://github.com/projectdiscovery/nuclei), Nikto, commercial scanners |
| JS-heavy SPAs | Playwright/Puppeteer + custom rules or Lighthouse CI |
| SEO / performance / a11y | Lighthouse, Google Search Console, dedicated SEO crawlers |
| Bot/crawler policy validation | Parse `robots.txt` + log analysis; Cloudflare Bot Analytics |
| Continuous monitoring | Scheduled runs + Prometheus/Grafana, Datadog Synthetics, Upptime |
| Deep Django/WordPress hardening | Framework docs, `manage.py check --deploy`, WP hardening plugins, infra-as-code |
| Formal pentest | Engage a qualified tester; this script is recon/hygiene only |

**Practical workflow:** use **`web_audit.sh`** for fast, repeatable **external hygiene**; escalate specific findings to framework config, CDN dashboard, or heavier scanners as needed.

---

## Example — Django site with custom public routes

`my-site.conf` (minimal):

```ini
[paths]
extra=/app/
extra=/tests/

[expected_open]
/app/=app_surface
/tests/=app_surface

[rate_limit_post]
/api/chat/=json
```

```bash
OPEN_BROWSER=0 zsh ./web_audit.sh \
  --config ./my-site.conf \
  --framework django \
  https://example.com
```

**With config:** `/app/` and `/tests/` classified as app surface; POST probe on `/api/chat/`; Hygiene reflects header/TLS/rate-limit gaps; Exposure stays **100** if no sensitive file leaks.

**Without config:** same core checks, but custom routes may appear under **REVIEW** and `/api/chat/` is not POST-probed.

---

## File map

| File | Role |
|------|------|
| `web_audit.sh` | Main audit tool (v2.5) |
| `site.conf.template` | Documented template — copy to `my-site.conf` |
| `README.md` | Quick start, evaluation overview, score math in plain terms |
| `run_notes.md` | Extended reference + pipeline/scoring code refs (this document) |
| `audit_logs/` | Generated reports (beside the script; gitignored) |

---

## Legal / responsible use

Generated reports state: *for authorized security assessment only*.

Unauthorized scanning may violate terms of service or local law.

The POST rate-limit phase is deliberate abuse simulation — keep it on your own infrastructure or with written approval.

---

Created by Vlad.M — [muzar.io](https://muzar.io/) — © 2026
