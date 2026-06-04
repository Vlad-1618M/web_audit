# Web Audit v2 — in plain English

*For site owners, PMs, or anyone who does not live in a terminal. Developers: see [README](../README.md) for the technical quick start.*

---

## What is Web Audit?

Web Audit looks at your **public website** the way a stranger on the internet would — and tells you, in simple scores, whether basic security hygiene looks okay or needs work.

It is **not** a full penetration test. It is a **health check**: headers, DNS email protection, and (as v2 grows) TLS, exposed files, and more.

You type a command with your site URL. You get a short summary and a saved report file you can open or send to your developer.

### Scan Example Report - Wikipedia Set:
- Executive Summary
![wiki_scan_1](/v2_python_core/mockups/screenshots/wiki_page_1.png)
- Technical Summary
![wiki_scan_2](/v2_python_core/mockups/screenshots/wiki_page_2.png)
- Technical Summary
![wiki_scan_3](/v2_python_core/mockups/screenshots/wiki_page_3.png)

---

## “Installing” the tool — what that actually means

When a developer runs setup (for example `./dev-venv.sh setup` or `pip install`), they are **putting the Web Audit program on the computer** so the command `webaudit` works.

Think of it like installing an app on your phone:

| Step | Plain English |
|------|----------------|
| **Setup / pip install** | The app is installed. You can open it (run `webaudit scan …`). |
| **Virtual environment (`.venv`)** | A small, separate toolbox used only for this project — so it does not clash with other Python projects on the same machine. |
| **`webaudit scan https://yoursite.com`** | Run a check on that site. Results are saved under `audit_logs/`. |

**Important:** Until someone runs setup on that machine, `webaudit` will not work there. It is not automatic for every user on the internet — it runs from **your** computer (or your CI server) with **your** permission to test the site.

---

## What `webaudit completion install` means (and what it does *not* mean)

Recommended command (replaces the older `--install-completion` flag):

```bash
webaudit completion install
```

You will see a plain-English panel explaining what changed on your system.

### What it does **not** mean

- It does **not** install Web Audit again.
- It does **not** put the tool “inside the shell” as a permanent system module.
- It does **not** change your website or server in any way.
- It is **optional** — scans work fine without it.
- **Deleting `.venv` does not remove Tab completion** — completion lives in your home folder (see below).

### What it **does** mean

It adds a **small file in your home directory** so the terminal can suggest commands when you press **Tab** (like autocomplete on a phone keyboard).

| Shell | Typical file location |
|-------|------------------------|
| zsh (macOS default) | `~/.zfunc/_webaudit` |
| bash | `~/.bash_completions/webaudit.sh` |
| fish | `~/.config/fish/completions/webaudit.fish` |

After you restart the terminal (or open a new window):

- Type `webaudit ` and press **Tab** → the shell may suggest `scan`, `completion`, etc.
- Type `webaudit scan --` and press **Tab** → it may suggest flags like `--json`.

### Check status

```bash
webaudit completion status
```

Shows whether those files exist and reminds you that `.venv` and completion are separate.

### Uninstall Tab completion only

```bash
webaudit completion uninstall
```

Removes the autocomplete file(s) from your home directory. **The `webaudit` command itself stays installed** until you remove the Python venv (`./dev-venv.sh teardown` or delete `.venv`).

### Remove the tool entirely (not the same as completion uninstall)

| Goal | What to run |
|------|-------------|
| Stop Tab suggestions only | `webaudit completion uninstall` |
| Remove Web Audit from this machine | `./dev-venv.sh teardown` or delete `v2_python_core/.venv` |

That is all. Tab completion is a **convenience for people who type commands often**, not a requirement to use the product.

---

## Running a scan — what you will see

Example:

```bash
webaudit scan https://example.com
```

Typical output:

| Line | Meaning |
|------|---------|
| **Hygiene** (0–100) | How well the site is configured (headers, DNS, etc.). Higher is better. |
| **Leak protection** (0–100) | Same as the **Exposure** score in JSON — whether sensitive files look reachable from outside. **100/100 = nothing obvious leaked** (good). |
| **Verdict** | Plain label: **PASS**, **NEEDS ATTENTION**, or **AT_RISK**. |
| **Findings** | Count of individual checks (missing header, missing DMARC, etc.). |

### Scan Example Report - Zillow Set:
- Executive Summary
![zillow_scan_1](/v2_python_core/mockups/screenshots/z_page_1.png)
- Executive Summary
![zillow_scan_2](/v2_python_core/mockups/screenshots/z_page_2.png)
- Technical Summary
![zillow_scan_3](/v2_python_core/mockups/screenshots/z_page_3.png)
- Technical Summary
![zillow_scan_4](/v2_python_core/mockups/screenshots/z_page_4.png)

The full detail is in a JSON file:

```text
audit_logs/<date>_<your-site>/audit_run.json
```
### JSON data Example:
```json
{
  "schema_version": "2.0",
  "meta": {
    "target_url": "https://www.zillow.com",
    "started_at": "2026-06-03T15:39:06+00:00",
    "finished_at": "2026-06-03T15:40:45+00:00",
    "webaudit_version": "2.1.0b2",
    "framework": "unknown"
  },
  "config_snapshot": {
    "runtime": {
      "timeout_seconds": 15,
      "max_concurrency": 8,
      "probe_delay_ms": 0,
      "user_agent": "WebAudit/2.0 (+https://github.com/Vlad-1618M/web_audit)"
    },
    "paths": {
      "enabled": true,
      "sensitive_builtin": true,
      "max_probe_urls": 250,
      "extra_paths": [],
      "expected_open": []
    },
    "policy": {
      "enabled": true,
      "hsts_min_max_age_seconds": 15552000,
      "csp_detail_max_length": 500
    },
    "collectors": {
      "dns": {
        "enabled": true,
        "check_spf": true,
        "check_dmarc": true,
        "check_dkim": false,
        "check_caa": true,
        "check_dnssec": true,
        "check_aaaa": true,
        "check_a": true,
        "check_mx": true,
        "check_ns": true,
        "check_asn": true,
        "use_host_tools": true
      },
      "tls": {
        "enabled": true,
        "check_deprecated_versions": true,
        "check_chain": true,
        "check_ciphers": false,
        "check_ocsp": false,
        "expiry_warn_days": 30
      },
      "cookies": {
        "enabled": true
      },
      "artifacts": {
        "enabled": true,
        "check_robots": true,
        "check_security_txt": true,
        "check_sitemap": true,
        "max_robots_bytes": 12000,
        "max_security_txt_bytes": 8000,
        "max_sitemap_bytes": 16000,
        "max_sitemap_urls": 150
      },
      "rate_limit": {
        "enabled": true,
        "get_burst_count": 6,
        "post_burst_count": 15
      },
      "cors": {
        "enabled": true,
        "probe_origin": "https://evil.example.com",
        "api_paths": [
          "/api/",
          "/api/v1/"
        ]
      },

```

Your developer can turn that into an HTML report (default **owner** variant: Security dashboard + Executive summary on one page, Technical details on a second tab). Mockups of standalone variants are in [mockups/reports/](../mockups/reports/).

### HTML data Example:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Web Audit — zillow.com (Owner report)</title>
<meta name="color-scheme" content="dark">
<style>
  @media print {
    html, body {
      background: #030306 !important;
      color: #eef2ff !important;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
  }
</style>  <link rel="stylesheet" href="report.css">
</head>
<body>
  <div class="owner-shell">
    <header class="owner-action-bar no-print">
<div class="owner-action-bar-inner">
  <div class="owner-action-primary">
    <button type="button" class="btn-edge-cyan" onclick="window.print()">Print / Save as PDF</button>
    <span class="hint owner-print-hint">Print → Save as PDF. Turn on <strong>Background graphics</strong> for the dark theme.</span>
  </div>
  <nav class="owner-tab-switch" role="tablist" aria-label="Report sections">
    <button type="button" class="owner-tab active" role="tab" data-owner-tab="overview" aria-selected="true">
      Executive summary
    </button>
    <button type="button" class="owner-tab" role="tab" data-owner-tab="technical" aria-selected="false">
      Technical details
    </button>
  </nav>
</div>    </header>

    <div id="page-overview" class="owner-page">
      <div class="owner-overview-wrap">

<section class="block dashboard-block">
  <div class="dashboard-header-row">
    <div class="section-heading-row">
      <h2>Security dashboard</h2>
      <p class="url section-heading-url"><a href="https://www.zillow.com" class="site-link" target="_blank" rel="noopener">https://www.zillow.com</a>
</p>
    </div>
    <div class="tag-row dashboard-tags">
      <span class="tag c">unknown</span>
      <span class="tag m">AT RISK</span>
    </div>
  </div>

  <div class="metrics-grid">
    <div class="metric score-band critical">
      <div class="val">30</div>
      <div class="lbl">Hygiene score</div>
      <div class="metric-hint">Higher = better hardened</div>
    </div>
    <div class="metric score-band poor">
      <div class="val">50</div>
      <div class="lbl">Leak protection</div>
      <div class="metric-hint">Higher = fewer public leaks</div>
    </div>
    <div class="metric gold">
      <div class="val">103</div>
      <div class="lbl">Path probes</div>
    </div>
    <div class="metric violet">
      <div class="val">10</div>
      <div class="lbl">Action items</div>
    </div>
  </div>
```

### Reading the owner report (quick guide)

| Tab / section | What to look at |
|---------------|-----------------|
| **Security dashboard** | Hygiene + **Leak protection** scores, verdict, metric chips (Critical, Plugins, …) |
| **Executive summary** | Plain-language timeline of what mattered |
| **Technical details** | Full findings tables, DNS cards, site discovery URLs, **Plugins / Extensions**, **WordPress theme** (WP sites) |
| **Plugins / Extensions** | WordPress (or other stack) components seen in public HTML — **0 is normal** on sites where the homepage is not WordPress (e.g. Next.js front-end) |
| **WordPress theme** | *(Technical tab, WordPress sites only)* — which visual theme the site uses, whether it looks up to date, and whether a safer “child theme” setup is in place — see below |
| **Bottom guide** | “What this report is (and is not)” — compares Web Audit to ZAP, pentests, SEO tools |
---
- Security dashboard preview
![dashboard](/v2_python_core/mockups/screenshots/dashboard.png)
- Technical details preview
![Technical](/v2_python_core/mockups/screenshots/tech_view.png)
- Bottom guide preview
![Bottom guide](/v2_python_core/mockups/screenshots/is_isnot.png)

Re-render a saved scan without re-running checks:
```bash
webaudit report audit_logs/<folder>/audit_run.json
```

---

## WordPress theme checks (plain English)

If your site runs on **WordPress**, the **Technical details** tab includes a **WordPress theme** section. This is separate from **Plugins / Extensions** — plugins add features; the **theme** controls layout and styling (Avada, Divi, Astra, a custom agency theme, etc.).

Web Audit reads what is **publicly visible** (like a visitor’s browser loading CSS). It does **not** log into wp-admin.

### What you might see

| Report message | Plain English | What to ask your developer |
|----------------|---------------|----------------------------|
| **Child theme detected** | Good practice — custom design changes sit in a “child” layer so the main theme can still receive security updates | Nothing urgent — confirm they plan to keep the **parent** theme updated |
| **Theme is behind latest** (ACTION) | The theme version looks older than the current free release on wordpress.org | “When was the theme last updated? Can we schedule an update and test?” |
| **Premium or unverifiable** (VERIFY) | Common for paid themes (Avada, Divi, …) — the tool cannot compare to a public catalog | “What version are we on? Is our license active? Any known security advisories for this theme?” |
| **Update trap risk** (VERIFY) | A popular premium theme is used **directly** with no child theme — agencies often **freeze updates** forever to avoid breaking custom edits | “Are theme updates disabled? Can we move customizations to a child theme and update the parent?” |
| **Editor status unverifiable** (VERIFY) | WordPress can edit theme files or install plugins from the dashboard; that is dangerous if an admin password is stolen. The scan **cannot** see your `wp-config.php`, but wp-login/wp-admin looks reachable | “Are `DISALLOW_FILE_EDIT` and (for stricter sites) `DISALLOW_FILE_MODS` set in wp-config?” |
| **No theme observed** | Homepage HTML did not expose WordPress theme paths — normal for decoupled front-ends (Next.js, etc.) or heavy caching | If the site **is** WordPress behind the scenes, ask whether the public site hides `/wp-content/themes/` |

### Why this matters for owners

Many hacked WordPress sites had **up-to-date plugins** but a **years-old theme** or **frozen parent theme** that never received security patches. Plugin scanners are common; **theme maintenance** is an easy blind spot — especially on agency-built sites handed off without a update contract.

### What this is **not**

- Not proof that someone **can** edit your theme files right now (that requires admin access).
- Not a list of every theme ever installed — only what this external scan could see on the public homepage.
- Not a replacement for your host’s malware scan or a full penetration test.

For technical background: [wordpress_theme_threat_model.md](wordpress_theme_threat_model.md).

---

## Optional: JavaScript rendering (`--js`)

Some modern sites only show their real links and menus **after JavaScript runs** in a browser. The default scan reads the first HTML response (like a simple bot). That is usually enough.

If your developer wants a **second pass with a real browser** (Chromium via Playwright):

| Step | Who | Plain English |
|------|-----|----------------|
| Install JS support | Developer | `pip install -e ".[js]"` inside the project venv (one-time) |
| Download browser | Developer | `.venv/bin/python -m playwright install chromium chromium-headless-shell` (one-time, ~100 MB) |
| Run scan | Developer | `webaudit scan https://yoursite.com --js` |

**You do not need this** for a first audit. The owner report still works without `--js`. If the browser is missing, the report shows friendly fix steps instead of raw error text.

**GraphQL / API check** (`--api`): optional flag for developers checking whether GraphQL introspection or Swagger docs are exposed. No extra install beyond the normal setup.

---

## Help commands

| Command | Works? | Notes |
|---------|--------|-------|
| `webaudit --help` | Yes | Full list of commands |
| `webaudit -h` | Yes | Same as `--help` |
| `webaudit scan --help` | Yes | Options for a scan |

---

## Who does what

| Role | Typical action |
|------|----------------|
| **Site owner** | Ask for a scan; open the HTML report; read Verdict + Hygiene + Leak protection; on WordPress sites, skim **Technical → WordPress theme** and **Plugins**; use “What this report is (and is not)” at the bottom for context. |
| **Developer / agency** | Run setup once, run scans in CI or locally, fix ACTION items in the report. |
| **You (dev on this repo)** | Use `./dev-venv.sh` to create/remove the local toolbox; run `pytest` before changes. |

---

## One-sentence summary

**Setup installs the checker; `scan` runs the checker on a URL; `webaudit completion install` only adds optional Tab-key suggestions — nothing more.**
