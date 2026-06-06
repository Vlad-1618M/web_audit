# Web Audit - v1 Bash & Web Audit Pro - v2 Python + Swift

External security hygiene checks for **public websites** you own or have permission to test.

This repository ships **two product editions** (v1 bash + v2 Python) and **several ways to run v2**.
Same philosophy applies -  passive, unauthenticated, external-only scans.

| | **v1 Audit Lite** | **v2 Audit Pro** |
|---|-------------------|------------------|
| **What** | Single shell script | Python package + HTML reports |
| **Location** | [`web_audit.sh`](web_audit.sh) (repo root) | [`v2_python_core/`](v2_python_core/) |
| **Install** | `git clone` + zsh/bash — **no pip, no Docker** | See [**delivery paths**](DELIVERY_PATHS.md) — Docker, venv, Mac app, or bundled `.dmg` |
| **Best for** | SSH boxes, CI, minimal deps | Site owners, richer reports, WP themes, DNS/TLS depth |
| **Docs** | This file (below) | [**v2 README**](v2_python_core/README.md) · [**How to run**](DELIVERY_PATHS.md) · [Docker / CI](v2_python_core/docs/docker_ci.md) · [Tags](VERSIONING_AND_TAGS.md) |

> **This tool is not:**
> - A penetration test
> - An authenticated scanner or replacement for OWASP ZAP or nuclei
>
> **Use responsibly:**
> - Only scan sites you own or have explicit permission to test
> - Helps improve clarity during conversations with your Dev/Admin team or support staff

---

## How to run v2 — pick your path

**Full matrix:** [**DELIVERY_PATHS.md**](DELIVERY_PATHS.md)

| You are… | Start here |
|----------|------------|
| **Mac site owner** (no Terminal, no Docker) | Download **`WebAudit-*-macOS.dmg`** — engine bundled in app · [macos/README.md](macos/README.md) |
| **Mac/Linux site owner** (OK with one-time Terminal setup) | Docker + `webaudit-docker` — [section below](#docker--github-packages--v2-audit-pro) |
| **Mac developer** (repo UI + Docker or venv) | `macos/WebAuditMac/run-dev.sh` or dev DMG |
| **Python developer** (no Docker) | `v2_python_core/dev-venv.sh` → `webaudit scan …` |
| **CI / server** | `docker run ghcr.io/vlad-1618m/webaudit …` |
| **Minimal shell** | [v1 `web_audit.sh`](#v1-audit-lite--bash-quick-start) — no Docker, no Python package |

---

## Docker / GitHub Packages — v2 Audit Pro

**If you opened the [GHCR package `webaudit`](https://github.com/users/Vlad-1618M/packages/container/webaudit)** or ran `docker pull ghcr.io/vlad-1618m/webaudit`, you want **v2**, not the bash script below.

**Requirements:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac/Windows) or Docker Engine (Linux). Image name must be **lowercase**: `ghcr.io/vlad-1618m/webaudit`.

Browsers **cannot** open from inside the container. Do **not** use `docker run … --open html` alone — use the **host wrapper** below (mounts reports on your Mac/Linux and opens the browser when done). No `docker cp`, no git clone.

### Pull only — recommended for site owners

**One-time setup** (install the small host helper from the image you already pulled):

```bash
docker pull ghcr.io/vlad-1618m/webaudit:latest

mkdir -p ~/.local/bin
docker run --rm --entrypoint cat ghcr.io/vlad-1618m/webaudit:latest \
  /usr/share/webaudit/webaudit-docker.sh > ~/.local/bin/webaudit-docker
chmod +x ~/.local/bin/webaudit-docker
```

Ensure `~/.local/bin` is on your `PATH` (macOS Terminal often includes it; otherwise add to `~/.zshrc`).

**Every scan:**

```bash
# Scan + prompt y/N to open report.html
webaudit-docker scan https://example.com

# Verbose scan, save under ~/Documents/WebAudit, open HTML when done
webaudit-docker --output-dir documents scan https://example.com -v --api --open html
```

Reports stay on **your machine** (`~/Documents/WebAudit`, `./audit_logs`, etc.). Multi-arch image: Intel Mac, Apple Silicon, Linux.

### CI / automation (no browser)

```bash
mkdir -p audit_logs
docker run --rm \
  -v "$(pwd)/audit_logs:/work/audit_logs" \
  ghcr.io/vlad-1618m/webaudit:latest \
  scan -v --api --open none https://example.com
```

Then open `audit_logs/*/report.html` yourself, or use SARIF (`--sarif`) for pipelines.

### Developers (git clone)

If you work from the repo, the same wrapper lives at `v2_python_core/scripts/webaudit-docker.sh`:

```bash
git clone git@github.com:Vlad-1618M/web_audit.git
cd web_audit/v2_python_core
./scripts/webaudit-docker.sh scan https://example.com -v --open html
```

| Resource | Link |
|----------|------|
| **v2 full README** (reports, optional `--js`, dev setup) | [v2_python_core/README.md](v2_python_core/README.md) |
| **Docker, CI, GHCR publish** | [v2_python_core/docs/docker_ci.md](v2_python_core/docs/docker_ci.md) |
| **Plain-English guide** (non-developers) | [v2_python_core/docs/getting_started_plain.md](v2_python_core/docs/getting_started_plain.md) |
| **macOS app** (public `.dmg` + dev builds) | [macos/](macos/) · [delivery paths](DELIVERY_PATHS.md) · [Swift guide](macos/WebAuditMac/SWIFT_APP_GUIDE.md) |
| **v1 bash script** (zero-install shell edition) | [↓ v1 section below](#v1-audit-lite--bash-quick-start) |

---

# Web Audit Pro App - .dmg View
>![home](/v2_python_core/mockups/screenshots/app_home.png)

>![onmac](/v2_python_core/mockups/screenshots/installed_app.png)

>![report](/v2_python_core/mockups/screenshots/scanned.png)

>![share](/v2_python_core/mockups/screenshots/report.png)

# Web Audit Pro Report View 
>![report](/v2_python_core/mockups/screenshots/report_main.png)

>![report](/v2_python_core/mockups/screenshots/tech_view_reporet.png)


## v1 Audit Lite — bash quick start

**Zero Install** — one shell script, `curl` + `openssl` only.

Probe headers, TLS, paths, cookies, robots.txt, CORS, and login rate limits.<br> 
Gets **Hygiene** and **Exposure** scores with HTML, JSON, and terminal reports. Supports **Django**, **WordPress**, **Laravel**, **Rails**, and generic PHP.

**Requirements:** zsh (macOS) or bash 4+, `curl`, `openssl`, standard Unix utilities. No pip/npm/Docker.

**Looking for v2 / Docker instead?** See [Docker / GitHub Packages](#docker--github-packages--v2-audit-pro) or [v2_python_core/README.md](v2_python_core/README.md).

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

## Web Audit v1 -  Report Sample View
![sample_0](/png/wiki_audit_preview.png) <br><br>
<!-- ![sample_1](/png/zillo_view.png) -->

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
| **Miscellaneous** | Split URL inventory (security probes vs internal site routes/links); image count on up to 8 sampled pages |

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

**`[paths] extra=`** routes are probed (GET), sampled for link/image discovery (up to **8 pages** with homepage), and listed under **Internal URLs** in the report (`site_config` source) — not under Security Probe URLs.

**Important:** If you decline the config prompt or run without `--config`, only built-in probes and homepage sampling apply. Use `--config site_configs/<host>.conf` or answer **Y** to load your routes.

### Manual config

```bash
cp site.conf.template my-site.conf
```

| INI section | Effect |
|-------------|--------|
| `[paths]` `extra=/path/` | Add GET probe paths + misc page/image sampling; report tag **`site_config`** (Internal URLs) |
| `[expected_open]` `/path/=label` | Mark intentional 200s (not Exposure leaks) |
| `[rate_limit_post]` `/path/=type` | Extra POST abuse probes |
| `[misc]` | Cap/show probe vs internal URL lists; optional HTML scan byte limits for links/images |

Edit any auto-generated file anytime — see `site.conf.template` and [run_notes.md](run_notes.md#with-config-vs-without-config).

Example:

```ini
[paths]
extra=/projects/
extra=/contact/

[expected_open]
/projects/=public_seo

[rate_limit_post]
/api/chat/=json

[misc]
# max_html_bytes=65536      # link scan window per page (default)
# max_html_img_bytes=98304  # image scan window per page (default)
```

Pass manual configs with `--config ./my-site.conf`.

---

## Reports

- **HTML** — findings, remediation hints, artifact details, **Miscellaneous** (designer credit, split URL lists, images), **Save as PDF** (dark theme; enable **Background graphics** in print dialog)
- **JSON** — `report_schema: "2.5"`, scores, checks, `artifacts`, `miscellaneous`, optional `compare`
- **TXT** — plain-text summary
- **Session index** — when auditing multiple URLs in one run

### Miscellaneous in reports

| HTML section | Contents |
|--------------|----------|
| **Discovered Security Probe URLs** | Built-in sensitive paths only (`.env`, `/wp-admin/`, …) — source `security_probe` |
| **Discovered Internal URLs** | Your `[paths] extra=` routes (`site_config`), plus same-origin links from homepage/sitemap/sampled pages (`homepage_links`, `page_links`, …) |
| **Images on sampled pages** | Unique `<img src>` found in server HTML (no JavaScript execution) |

JSON shape (under `miscellaneous.urls`):

```json
{
  "total": 165,
  "probe_total": 54,
  "internal_total": 111,
  "security_probes": { "total": 54, "items": [ … ] },
  "internal": { "total": 111, "items": [ … ] },
  "items": [ … ]
}
```

Legacy flat `items` is kept for backward compatibility. Hash-only nav (`/#section`) is not sent to the server — use real path routes in `[paths] extra=`.

Report header shows **Website** and, when detected in an acceptable place, **Designer / Creator** next to it.

<!-- --- -->

<!-- ## Out of scope - TBD

- Authenticated / logged-in areas
- JavaScript / SPA crawling
- CVE exploit templates (use [nuclei](https://github.com/projectdiscovery/nuclei))
- Full sitemap crawl
- Compliance certification (PCI/SOC2/HIPAA)

POST rate-limit probes send **real invalid login traffic** — use responsibly. -->

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

| Path | Role |
|------|------|
| `web_audit.sh` | **v1** — main bash audit tool |
| `v2_python_core/` | **v2** — Python package, Docker image source, docs |
| `v2_python_core/docker/webaudit/Dockerfile` | Builds `ghcr.io/vlad-1618m/webaudit` |
| `macos/` | **macOS** — SwiftUI app, packaging, built `.dmg` in `macos/installers/` |
| `macos/WebAuditMac/` | Swift source — one UI, two engine policies (bundled vs external) |
| `DELIVERY_PATHS.md` | **Which install path?** — app, Docker, venv, shell (no Docker) |
| `VERSIONING_AND_TAGS.md` | Git tags, GHCR, Mac release versions |
| `designs/swift/` | HTML wireframes + user-flow diagrams for the Mac app |
| `site.conf.template` | v1 per-site config template |
| `README.md` | **This hub** — v1 quick start + v2/Docker pointers |
| `v2_python_core/README.md` | v2 Audit Pro — full product README |
| `run_notes.md` | v1 extended reference + scoring pipeline |
| `audit_logs/` | Generated reports (gitignored) |
| `site_configs/` | v1 auto-generated per-host configs (gitignored) |

---

#### Legal
##### For **authorized security assessment only**. <br>Unauthorized scanning may violate terms of service or local law.

---

## Author

Created by **Vlad.M** — [muzar.io](https://muzar.io/) · [GitHub](https://github.com/Vlad-1618M)

MIT License — see [LICENSE](LICENSE).
