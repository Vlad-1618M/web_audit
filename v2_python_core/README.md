# Web Audit v2 — Python Core

**Status:** **2.1.0b4 (Stage 6)** — Tier 1 + Tier 2 depth, WP themes, **Docker CI / GHCR**, **plugin/theme CVE cache**, **SARIF export**. **Next:** live WPScan API, pipx/Homebrew — see [CHANGELOG.md](CHANGELOG.md) `[Unreleased]`. **Tags history:** [VERSIONING_AND_TAGS.md](../VERSIONING_AND_TAGS.md).

> **GHCR / Docker visitors:** Package [`ghcr.io/vlad-1618m/webaudit`](https://github.com/users/Vlad-1618M/packages/container/webaudit) runs **this v2 edition**. Pull and scan — see [Docker quick start](#docker--ghcr-public-usage) below.  
> **Mac site owners (no Docker):** Public `WebAudit-*-macOS.dmg` bundles this engine — [DELIVERY_PATHS.md](../DELIVERY_PATHS.md) row **A**, [macos/README.md](../macos/README.md).  
> **v1 bash script (no Docker):** [Root README — Audit Lite](../README.md#v1-audit-lite--bash-quick-start).  
> **All install paths:** [DELIVERY_PATHS.md](../DELIVERY_PATHS.md).

This directory is the home of **Web Audit v2 (Audit Pro)**. It lives beside the public **v1 bash** tool ([`web_audit.sh`](../web_audit.sh) at the repo root). v1 is **not** being replaced — it stays the zero-install shell edition.

---

## Why bash came first ?
UI developmnet was alwasy outside my purview - was never a thing for me.
The story starts with personal project where I needed a frontend layer on an application that was already hosted, CDN-configured, and fully public on the network. <br>
That meant living with the usual nightmare checks: 
>- bots
>-`robots.txt`
>- admin surface controls
>- "bad actors" scraping data and all the rest.<br>

At some point I started asking **what** my app was leaking to the outside no doubt it does, we've all been there. 
Reality checks came fast — potential data leaks, dev habits left as leftovers on endpoints and configs, things I missed while building. Testing matters everywhere even in _sandboxes_ and side projects. A quick shell script was my first approach. It worked and helped. Then I kept enhancing it, got carried away a bit, and it grew into a the a usual _“that’ll do for now”_ type of deal.

When I realized I had enough, the script was **> 3,500 lines** of code ( _I know — tha is not how you’re supposed to do this_) <br>
The fix and honestly apart of the reason “bored, let me complicate my life some more” — came from a different question.

---

## The problem I actually wanted to solve

How does someone who hires outside devs to build their business online, pays for the website, and has to take it at face value — with no technical knowledge or QA ?<br>
Sure they can get a full team to do the work, pay premium - nothing is wrong with that, but how many small business owners in U.S can actually afford a full stack engineering team ?  
They pay for site - _Admin Support_, _Google Ads_ + _SEO_ optimizations and no business leads show up. <br>
All they hear is: <br> 
- *It'll take more time for Google to index your site.* <br> 
- *We're working on features.* <br> 
- *We'll tag PNGs and put a cool landing page on a new domain.* <br> 
- *Just pay $X more and in X months you'll see leads.* <br> 

But nothing changes except for wasted cash and the same song over and over again. <br>
The only thing one gets is `www.look-how-cool-my-site-is.com`  as Some templatized WordPress copy/paste deal (no offense — just a typical truth nowadays)

<!-- ### _**Wat I want is**_  - simple, manageable way for anyone especially people who have only seen a _terminal_ in the movies — to understand what their public website is actually exposing and a way to establish clarity  -->

_**Wat I want is**_ - A simple, manageable way for anyone - especially people who have only seen a _terminal_ in the movies - to understand what their public website is actually exposing. A tool that delivers results in a way where both the *site owner* and their *developer* or *support team* can find equal clarity and understanding, grounded in the same shared project. This app never logs in anywhere. It only observes what any visitor on the internet can already see. It does not share or upload any data - all reports are saved to the user's Documents folder. The user has full control over what they scan, share or what they keep.

## What v2 is

| | v1 (bash) | v2 (Python) |
|---|-----------|-------------|
| **Location** | Repo root [`web_audit.sh`](../web_audit.sh) | `v2_python_core/webaudit/` package (2.1.0b3) |
| **Audience** | Devs, CI, SSH boxes | Devs **and** non-technical site owners |
| **Install** | curl + openssl + zsh/bash | **Docker** [ghcr.io/vlad-1618m/webaudit](https://github.com/Vlad-1618M/web_audit/pkgs/container/webaudit) or `pip install` from source or [.dmg](https://github.com/Vlad-1618M/web_audit/tags) installer as app|
| **Architecture** | Monolith script | Modular collectors, analyzers, scorers, renderers |
| **Reports** | HTML with browser “Save as PDF” | **`owner`** combined HTML (default) + five standalone variants; native PDF optional |
| **Scope** | External hygiene snapshot | Same philosophy, **deeper signal** (DNS, TLS, DOM, JS, GraphQL) |
| **Hub / compare** | [Root README](../README.md) | This file |


## v1 remains **Audit Lite** — zero dependencies, Unix-first.
## v2 is **Audit Pro** — built properly, installable for broader consumption.

## Docker / GHCR (public usage)

Published image: **`ghcr.io/vlad-1618m/webaudit`** (multi-arch: Intel + Apple Silicon + Linux). Full guide: [docs/docker_ci.md](docs/docker_ci.md).

### Pull only — no git clone | [ghcr.io/vlad-1618m/webaudit](https://github.com/Vlad-1618M/web_audit/pkgs/container/webaudit)

The image ships a **host wrapper** at `/usr/share/webaudit/webaudit-docker.sh`. <br>
It mounts reports on your Mac/Linux and makes `--open html` work in **your** browser (not inside Docker).

**Install once:**

```bash
curl -fsSL https://raw.githubusercontent.com/Vlad-1618M/web_audit/v.tools_main/v2_python_core/scripts/install-webaudit-docker.sh | bash
```

From a git clone: `./scripts/install-webaudit-docker.sh` (adds `~/.local/bin` to `PATH` in your shell profile when needed).

**Scan** (wrapper adds `--js` + `--api` by default; `--shallow` for static-only):

```bash
webaudit-docker scan https://example.com
webaudit-docker --output-dir documents scan https://example.com -v --open html
webaudit-docker version
```

| `--output-dir` | Host folder |
|----------------|-------------|
| `cwd` (default) | `./audit_logs` |
| `home` | `~/WebAudit/audit_logs` |
| `desktop` | `~/Desktop/WebAudit` |
| `documents` | `~/Documents/WebAudit` |

**Do not** run `docker run … --open html` without the wrapper — the container cannot open a browser and reports may not land on your machine.

**CI / automation** — raw `docker run` with a volume and `--open none`:

```bash
docker run --rm -v "$(pwd)/audit_logs:/work/audit_logs" \
  ghcr.io/vlad-1618m/webaudit:latest scan -v --open none https://example.com
```

### From a git clone (developers)

```bash
cd v2_python_core
./scripts/webaudit-docker.sh scan https://example.com -v --open html
```

The [GitHub Packages page](https://github.com/users/Vlad-1618M/packages/container/webaudit) shows the **repo root README** (v1 + v2 hub). This file is the **v2-specific** documentation.

---

## Documentation map

| Document | Purpose |
|----------|---------|
| [docs/implementation_tracker.md](docs/implementation_tracker.md) | **Built vs planned** — module status, extension contract, Stage 2 backlog |
| [CHANGELOG.md](CHANGELOG.md) | Release history; Unreleased = remaining Stage 6 product backlog |
| [docs/getting_started_plain.md](docs/getting_started_plain.md) | **Non-technical** — install, scan, tab completion explained simply |
| [dev-venv.sh](dev-venv.sh) | Local `.venv` setup, activate, teardown (Mac/Linux) |
| [docs/stages.md](docs/stages.md) | Delivery stages; Tier 1 → Tier 2 → Tier 3 stacking |
| [docs/architecture.md](docs/architecture.md) | Module layout, libraries, data flow, diagrams |
| [docs/scoring.md](docs/scoring.md) | Math for Hygiene, Exposure, verdicts, baselines |
| [docs/testing.md](docs/testing.md) | pytest strategy, fixtures, CI gates |
| [docs/docker_ci.md](docs/docker_ci.md) | **Docker WP fixture**, `orchestrate.sh`, CI, webaudit Pro image |
| [docs/release_flow_t3_stage_6.md](docs/release_flow_t3_stage_6.md) | **Release notes** — tag/push/GHCR flow for 2.1.0b3 (working doc) |
| [docs/config.md](docs/config.md) | YAML config — global + per-site + **CVE cache** + **SARIF** (`--sarif`) |
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
./scripts/webaudit-docker.sh scan https://example.com --open html
```

Scan output lands in `./audit_logs/<timestamp>_<host>/` — `audit_run.json`, HTML report, and optionally `audit_run.sarif.json` when `--sarif` or `output.formats` includes `sarif`.

### Optional extras (Tier 2 depth)

Core install is enough for headers, DNS, TLS, paths, extensions, and HTML reports. Two **optional** add-ons need extra packages:

| Extra | Install | Scan flag | What it adds |
|-------|---------|-----------|--------------|
| **`[js]`** | `pip install -e ".[js]"` (or `.[dev,js]`) | `--js` | Playwright post-render pass — DOM links/scripts after JavaScript runs |
| **`[api]`** | included in base install | `--api` | GraphQL introspection + OpenAPI/Swagger probe (no extra pip package) |
| **CVE cache** | included in base install (WordPress) | *(on by default)* | `PLUGIN_CVE` / `THEME_CVE` findings from shipped snapshot + sqlite cache — see [config.md](docs/config.md#plugintheme-cve-cache-tier-3) |
| **SARIF** | included in base install | `--sarif` | `audit_run.sarif.json` for GitHub Code Scanning — see [config.md](docs/config.md#sarif-export-github-code-scanning) |

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
├── webaudit/                   ← Python package (2.1.0b3)
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

# Report Examples -  ***v1-shell based*** VS ***v2-Python Core***
## *v1 left* | *v2 right* - side-by-side preview
![report_view](/v2_python_core/mockups/screenshots/v1_vs_v2_report_view_0.png)

## *v1 left* | *v2 right* - side-by-side preview
![report_view](/v2_python_core/mockups/screenshots/v1_vs_v2_report_view_1.png)

## *v1 left* | *v2 right* - side-by-side preview
![report_view](/v2_python_core/mockups/screenshots/v1_vs_v2_report_view_2.png)

<!-- ### **Some mockups Ideas for Web Audit v2.**
![0](/v2_python_core/mockups/screenshots/idea_0.png)<br><br>
![1](/v2_python_core/mockups/screenshots/idea_1.png)<br><br>
![2](/v2_python_core/mockups/screenshots/idea_2.png)<br><br>


*— memo & TODO: for Vlad by Vlad repo owner.* -->
