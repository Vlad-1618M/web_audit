# Web Audit v2 — Python Core

**Status:** **2.1.0b2+ (Stage 6 in progress)** — Tier 1 + Tier 2 depth, Tier 2b extensions **+ WordPress theme fingerprint**, owner report. **Next:** CVE cache, packaging — see [CHANGELOG.md](CHANGELOG.md) `[Unreleased]`.

This directory is the blueprint for **Web Audit v2**. It lives beside the public **v1 bash** tool (`web_audit.sh` at the repo root). I am **not replacing v1** — people use it today, and it stays frozen as the zero-install shell edition.

---

## Why bash came first ?

I am not a UI developer. I do not like UIs. I have been a terminal person for over twenty years, and that is where I am comfortable.

The story starts with personal project  **muzar.io**. I needed a frontend layer on an application that was already hosted, CDN-configured, and fully public on the network. That meant living with the usual nightmare checks: bots, `robots.txt`, admin surface controls, bad actors scraping data, and all the rest. At some point I started asking **what** my app was leaking to the outside world, no doubt it does,we've all been there. 

Reality checks came fast — potential data leaks, dev habits left as leftovers on endpoints and configs, things I missed while building. Tests matter everywhere, including pet projects and sandboxes. A quick shell script was my first approach. It worked. It helped. Then I kept enhancing it, got carried away a bit, and it grew into something more than I expected — the usual “that’ll do for now” type of deal.

When I realized I had enough, the script was **over 3,000 lines** of code (I know — tha is not how you’re supposed to do this) LOL. <br>
The fix and honestly apart of the reason “bored, let me complicate my life some more” — came from a different question.

---

## The problem I actually wanted to solve

How does someone who hires outside devs to build their business online, pays for the website, and has to take it at face value — with no technical knowledge — vet or QA what they paid for?

They pay for site support, Google Ads, SEO optimizations. No business leads show up. <br>All they hear is: <br> - *It'll take more time for Google to index your site.* <br> - *We're working on features.* <br> - *We'll tag PNGs and put a cool landing page on a new domain.* <br> - *Just pay $X more and in X months you'll see leads.* <br> But nothing changes except wasted money and the same song over and over again. <br>The only thing one gets is `www.look-how-cool-my-site-is.com` = Some templatized WordPress copy/paste deal (no offense — just a typical truth nowadays)

<!-- They pay for site support, Google Ads, SEO optimizations. No business leads show up. <br>All they hear is: <br> - *It’ll take more time for Google to index your site. <br> - We’re working on features.<br> - We’ll tag PNGs and put a cool landing page on a new domain. <br>-  Just pay $X more and in X months you’ll see leads.* <br> But, nothing changes except wasted money and  same song over and over again. <br>The only item one gets is `www.look how cool my site is.com` = SOme templetized WordPress copy paste deal ( no affence people just typical truth now days) -->

**Wat I want is simple, manageable way for anyone — especially people who have only seen a terminal in the movies — to understand what their public website is actually exposing.**

That is v2.
---
#### Report Examples -  ***v1-shell based*** VS ***v2-Python Core***
- *v1 left* | *v2 right* - side-by-side preview
![report_view](/v2_python_core/mockups/screenshots/v1_vs_v2_report_view_0.png)
- *v1 left* | *v2 right* - side-by-side preview
![report_view](/v2_python_core/mockups/screenshots/v1_vs_v2_report_view_1.png)
- *v1 left* | *v2 right* - side-by-side preview
![report_view](/v2_python_core/mockups/screenshots/v1_vs_v2_report_view_2.png)

## What v2 is

| | v1 (bash) | v2 (Python) |
|---|-----------|-------------|
| **Location** | Repo root `web_audit.sh` | `v2_python_core/webaudit/` package (2.1.0b2) |
| **Audience** | Devs, CI, SSH boxes | Devs **and** non-technical site owners |
| **Install** | curl + openssl + zsh/bash | `pipx install webaudit` (or similar) |
| **Architecture** | Monolith script | Modular collectors, analyzers, scorers, renderers |
| **Reports** | HTML with browser “Save as PDF” | **`owner`** combined HTML (default) + five standalone variants; native PDF optional |
| **Scope** | External hygiene snapshot | Same philosophy, **deeper signal** (DNS, TLS, DOM, optional JS) |

v1 remains **Audit Lite** — zero dependencies, Unix-first, public forever.

v2 is **Audit Pro** — built properly for broader consumption, free as any tool should be, installable without living in a terminal.

---

## Documentation map

| Document | Purpose |
|----------|---------|
| [docs/implementation_tracker.md](docs/implementation_tracker.md) | **Built vs planned** — module status, extension contract, Stage 2 backlog |
| [CHANGELOG.md](CHANGELOG.md) | Release history; Unreleased = Stage 6 backlog |
| [docs/getting_started_plain.md](docs/getting_started_plain.md) | **Non-technical** — install, scan, tab completion explained simply |
| [dev-venv.sh](dev-venv.sh) | Local `.venv` setup, activate, teardown (Mac/Linux) |
| [docs/stages.md](docs/stages.md) | Delivery stages; Tier 1 → Tier 2 → Tier 3 stacking |
| [docs/architecture.md](docs/architecture.md) | Module layout, libraries, data flow, diagrams |
| [docs/scoring.md](docs/scoring.md) | Math for Hygiene, Exposure, verdicts, baselines |
| [docs/testing.md](docs/testing.md) | pytest strategy, fixtures, CI gates |
| [docs/docker_ci.md](docs/docker_ci.md) | **Docker WP fixture**, `orchestrate.sh`, CI, webaudit Pro image |
| [docs/config.md](docs/config.md) | YAML config system — global + per-site + framework profiles |
| [docs/framework_profiles.md](docs/framework_profiles.md) | Detect → load profile; WordPress/Django/Laravel |
| [docs/plugin_vulnerability_research.md](docs/plugin_vulnerability_research.md) | WP plugin CVE research + v2 criteria refinements |
| [docs/seo_surface.md](docs/seo_surface.md) | Tier 2c discoverability — INFO/VERIFY only, not scored |
| [docs/diagrams.md](docs/diagrams.md) | Mermaid architecture diagrams (dark theme) |
| [mockups/diagrams/index.html](mockups/diagrams/index.html) | **Live diagram viewer** (browser) |
| [tests/parity/PARITY.md](tests/parity/PARITY.md) | v1 bash ↔ v2 Pro parity matrix |
| [mockups/reports/README.md](mockups/reports/README.md) | HTML report variants + [gallery index](mockups/reports/index.html) (live default: **`owner`**) |
| [mockups/config/](mockups/config/) | Example YAML configs + [framework profiles](mockups/config/profiles/) |

---

## Design principles (non-negotiable for me)

1. **No mixed salad** — Python core orchestrates; HTML/CSS/Jinja templates live elsewhere; config is YAML, not embedded strings.
2. **v1 untouched** — parity tests compare v2 JSON to v1 where checks overlap; v1 keeps shipping.
3. **Same ethical line** — external, unauthenticated hygiene only; not a pentest replacement.
4. **Terminal-first CLI** — rich HTML/PDF for humans who hate terminals; CLI for me and CI.
5. **Modular tiers** — ship Tier 1 first; Tier 2/2b/3 plug in without rewriting the core.
6. **Framework profiles** — if WordPress detected, load WordPress extension config; Django gets its own profile, not WP plugin logic forced on it.
7. **SEO surface is informational** — Tier 2c helps owners who were sold SEO; it never competes with Hygiene/Exposure scores ([seo_surface.md](docs/seo_surface.md)).

---

## Quick start (dev)

```bash
cd v2_python_core
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
webaudit scan https://example.com
./orchestrate.sh --pytest-only    # unit tests + coverage (same as CI gate)
pytest
```

**Docker / CI:** see [docs/docker_ci.md](docs/docker_ci.md) — WordPress test container, `./orchestrate.sh`, GHCR image publish, GitHub Actions on PRs.

```bash
# Run from source
./orchestrate.sh --job wp-integration --wp-profile good

# Or pull published image (after push to GHCR)
docker run --rm ghcr.io/Vlad-1618M/webaudit:latest scan https://example.com --open none
```

Scan output lands in `./audit_logs/<timestamp>_<host>/audit_run.json`.

### Optional extras (Tier 2 depth)

Core install is enough for headers, DNS, TLS, paths, extensions, and HTML reports. Two **optional** add-ons need extra packages:

| Extra | Install | Scan flag | What it adds |
|-------|---------|-----------|--------------|
| **`[js]`** | `pip install -e ".[js]"` (or `.[dev,js]`) | `--js` | Playwright post-render pass — DOM links/scripts after JavaScript runs |
| **`[api]`** | included in base install | `--api` | GraphQL introspection + OpenAPI/Swagger probe (no extra pip package) |

**Playwright browsers** (~100 MB) are downloaded separately — use the **same Python/venv** that runs `webaudit`:

```bash
cd v2_python_core
pip install -e ".[js]"                    # once: Python package
.venv/bin/python -m playwright install chromium chromium-headless-shell
webaudit scan https://example.com --js
```

Browsers live in Playwright’s user cache by default (`~/Library/Caches/ms-playwright` on macOS). They are **not** committed to git (see `.gitignore`). If a scan says Chromium is missing, run the install line above from your venv — not a global `playwright` CLI unless that CLI uses the same Python.

**CI / tests:** unit tests mock Playwright; CI does not need browsers installed.

Or use the helper script (lists existing envs, age, setup/teardown):

```bash
./dev-venv.sh setup      # create .venv + install
eval "$(./dev-venv.sh activate --print)"   # zsh/bash: activate in this window (best for p10k)
./dev-venv.sh shell      # optional: minimal quiet subshell (skips ~/.zshrc)
./dev-venv.sh teardown   # remove .venv when finished
```

### In plain English (non-developers)

**Installing** (`pip install` or `./dev-venv.sh setup`) puts the `webaudit` command on your computer — like installing an app. After that you can run:

```bash
webaudit scan https://your-site.com
```

**`webaudit completion install`** adds optional **Tab autocomplete** (see friendly panel after install). **`webaudit completion uninstall`** removes it. **Deleting `.venv` does not remove completion** — they live in different places (`~/.zfunc/` vs project folder).

Full friendly guide: **[docs/getting_started_plain.md](docs/getting_started_plain.md)** — share with site owners or PMs.

---

## Package layout

```text
v2_python_core/
├── dev-venv.sh
├── pyproject.toml
├── webaudit/                   ← Python package (2.1.0b2)
│   ├── cli/                    # scan, report, diff, completion
│   ├── config/                 # settings.py + defaults.yaml
│   ├── collectors/             # headers, dns, paths, tls, extensions/, …
│   ├── analyzers/
│   ├── profiles/               # wordpress, django, laravel, rails, generic YAML
│   ├── render/                 # html, txt, pdf + display helpers
│   ├── scoring/
│   ├── pipeline.py
│   └── models/
├── templates/reports/          # Jinja HTML + CSS (owner default + five standalone)
├── tests/unit/ + tests/parity/
├── mockups/
└── docs/
```

Live module status: [docs/implementation_tracker.md](docs/implementation_tracker.md).

---

## How to read the mockups

Open the gallery or any variant in a browser:

```bash
open v2_python_core/mockups/reports/index.html
open v2_python_core/mockups/diagrams/index.html
```

---

## License & relationship to v1

Same spirit as v1: free, open, use on sites you own or have permission to test. <br>
v2 docs are part of the same repository; implementation will cite v1 behavior where I intentionally mirror it.

---

### **Some mockups Ideas for Web Audit v2.**
![0](/v2_python_core/mockups/screenshots/idea_0.png)<br><br>
![1](/v2_python_core/mockups/screenshots/idea_1.png)<br><br>
![2](/v2_python_core/mockups/screenshots/idea_2.png)<br><br>


*— memo & TODO: for Vlad by Vlad repo owner.*
