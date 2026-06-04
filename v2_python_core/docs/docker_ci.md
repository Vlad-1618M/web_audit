# Docker, CI, and local orchestration

Run **unit tests first**, then optional **WordPress Docker fixture** integration tests, and build the **webaudit Pro** image for Windows/macOS/Linux users who prefer Docker over a local Python venv.

Published images: **`ghcr.io/<your-github-user>/webaudit`** (GitHub Container Registry).

**Diagrams:** [Docker stack](#docker-test-stack-architecture) · [`--all` flow](#local-orchestrator---orchestrateshall---all) · [CI pipeline](#github-actions-ci-githubworkflowsciyml) · [scan paths](#scan-paths--host-vs-container)

---

## Quick start

```bash
cd v2_python_core

# Full local pipeline (pytest → build image → WP fixture → integration → teardown)
./orchestrate.sh --all

# Unit tests only (always run this before opening a PR)
./orchestrate.sh --pytest-only

# CI-style: unit tests, no browser prompt
./orchestrate.sh --pytest-only --no-report-prompt

# WordPress fixture + integration against profile "good"
./orchestrate.sh --job wp-integration --wp-profile good --keep-wp
```

---

## Diagrams

### Docker test stack (architecture)

WordPress needs **two** pulled images plus **two** persistent volumes. Web Audit only talks HTTP — never MariaDB directly.

```mermaid
flowchart TB
  subgraph host["Your machine"]
    CLI["webaudit CLI / browser"]
  end

  subgraph net["Docker network: webaudit-test-net"]
    DB["wp-db<br/>mariadb:10.11"]
    WP["wordpress<br/>wordpress:6.7-apache"]
    INIT["wp-init<br/>wordpress:cli one-shot"]
    AUDIT["webaudit:local<br/>ephemeral scan container"]
  end

  VDB[("volume wp_db_data<br/>MySQL tables")]
  VHTML[("volume wp_html<br/>PHP, plugins, wp-config")]

  CLI -->|"http://127.0.0.1:8080"| WP
  AUDIT -->|"http://wordpress"| WP
  WP <-->|SQL| DB
  DB --- VDB
  WP --- VHTML
  INIT --> VHTML
  INIT --> DB
```

### Local orchestrator — `./orchestrate.sh --all`

Default path runs unit tests first, then Docker jobs, then tears down WP unless `--keep-wp`.

```mermaid
flowchart TD
  START(["./orchestrate.sh --all"]) --> PYTEST["pytest (unit)<br/>coverage + pytest_reports/"]
  PYTEST -->|fail| FAIL([exit 1])
  PYTEST -->|pass| DOCKER{Docker available?}

  DOCKER -->|no| WARN["Skip docker-build,<br/>WP, integration"]
  DOCKER -->|yes| BUILD["docker-build<br/>webaudit:local"]
  BUILD --> WPUP["wp-up<br/>MariaDB + WP + wp-init"]
  WPUP --> INT["integration<br/>tests/integration"]
  INT -->|fail| FAIL
  INT -->|pass| KEEP{--keep-wp?}

  KEEP -->|no| DOWN["wp-down<br/>stop containers"]
  KEEP -->|yes| LEAVE["Leave WP stack running"]
  DOWN --> OK([All jobs completed])
  LEAVE --> OK
  WARN --> OK
```

### WordPress fixture startup (`wp-up`)

```mermaid
sequenceDiagram
  autonumber
  participant O as orchestrate.sh
  participant DB as wp-db MariaDB
  participant WP as wordpress Apache
  participant I as wp-init WP-CLI

  O->>DB: compose up -d (wait healthy)
  O->>WP: compose up -d (wait HTTP OK)
  Note over WP,DB: WP connects via WORDPRESS_DB_HOST=wp-db
  O->>I: compose run --rm wp-init
  I->>I: ensure_fs_writable
  alt not installed
    I->>DB: wp core install
  end
  I->>WP: install plugins + theme
  I->>WP: wp config set DISALLOW_* (profile)
  I-->>O: fixture ready
  O-->>O: scan http://127.0.0.1:8080
```

### WordPress hardening profiles

Applied in `docker/wp-test/init-wordpress.sh` after core install.

```mermaid
flowchart LR
  P{"WEBAUDIT_WP_PROFILE<br/>weak | mid | good"}

  P -->|weak / minimal| W["No DISALLOW_*<br/>parent theme only"]
  P -->|mid / ok| M["DISALLOW_FILE_EDIT<br/>parent theme"]
  P -->|good / strong| G["DISALLOW_FILE_EDIT<br/>DISALLOW_FILE_MODS<br/>child theme webaudit-child"]

  W --> SCAN["webaudit scan<br/>HTTP only"]
  M --> SCAN
  G --> SCAN
```

### Scan paths — host vs container

```mermaid
flowchart LR
  subgraph host_scan["From host (.venv / local webaudit)"]
    H1["webaudit scan<br/>http://127.0.0.1:8080"]
  end

  subgraph container_scan["From webaudit container"]
    C1["docker-scan-wp<br/>http://wordpress"]
    C2["docker-scan-host<br/>http://127.0.0.1:8080 or URL"]
  end

  WP["WordPress fixture"]
  H1 --> WP
  C1 --> WP
  C2 --> WP
```

### GitHub Actions CI (`.github/workflows/ci.yml`)

Three jobs fan out after **unit-tests**; GHCR publish only on **push** to mainlines (not PRs).

```mermaid
flowchart TB
  subgraph trigger["Workflow triggers"]
    PR["pull_request<br/>v2_python_core/**"]
    PUSH["push<br/>main · v.tools_main · t*_*"]
  end

  trigger --> UT["job: unit-tests<br/>pytest tests/unit + coverage.xml"]

  UT --> INT["job: integration-wp<br/>compose up → wp-init → pytest integration"]
  UT --> IMG["job: docker-image<br/>build webaudit:ci + --help smoke"]
  UT --> PUBCHK{push event AND<br/>main / v.tools_main / v* tag?}

  INT --> TEAR["always: compose down -v"]
  PUBCHK -->|PR or feature branch| NOPUB["no publish-ghcr"]
  PUBCHK -->|yes| GHCR["job: publish-ghcr<br/>build + push ghcr.io/…/webaudit"]

  GHCR --> TAGS["tags: version · sha-* · latest"]
```

### CI vs local orchestrator (parity)

```mermaid
flowchart LR
  subgraph local["Local ./orchestrate.sh"]
    L1["--pytest-only"]
    L2["--all"]
    L3["--job wp-integration"]
  end

  subgraph gha["GitHub Actions"]
    G1["unit-tests"]
    G2["integration-wp"]
    G3["docker-image"]
    G4["publish-ghcr<br/>main only"]
  end

  L1 -.->|same pytest scope| G1
  L2 -.->|pytest + WP + integration + build| G1
  L2 -.-> G2
  L2 -.-> G3
  L3 -.->|wp-up + integration| G2
  G4 -.->|not in --all| MANUAL["docker-push-ghcr<br/>manual / merge"]
```

---

## Orchestrator (`orchestrate.sh`)

Colored **JOB →** banners. Pytest uses **`-v -s -x -ra`** plus coverage (`htmlcov/`, `coverage.xml`) and a **dated HTML test report** (`pytest_reports/`).

Full command reference:

```bash
./orchestrate.sh --help    # or -h / --h — all flags, jobs, and colored examples
./orchestrate.sh --list    # job catalog + environment variables
```

| Job | What it does |
|-----|----------------|
| `pytest` | Unit tests under `tests/unit/` |
| `integration` | `tests/integration/` (needs `WEBAUDIT_WP_TEST_URL`) |
| `wp-up` | Start MariaDB + WordPress + `wp-init` |
| `wp-down` | Stop containers |
| `wp-reset` | Stop + delete volumes (fresh install) |
| `docker-build` | Build `webaudit:local` Pro image |
| `docker-push-ghcr` | Push `webaudit:local` to GHCR (after `docker login ghcr.io`) |
| `docker-scan-wp` | Scan `http://wordpress` from inside Docker network |
| `docker-scan-host` | Scan a host URL from webaudit container on `webaudit-test-net` |
| `wp-integration` | `wp-up` → `integration` → `wp-down` (unless `--keep-wp`) |

### Orchestrator flags

| Flag | Purpose |
|------|---------|
| `--all` | pytest → docker-build → wp-up → integration → wp-down |
| `--pytest-only` | Unit tests only (same as `--job pytest`) |
| `--job NAME` | Run one job; repeat for a chain (e.g. `--job docker-build --job wp-up`) |
| `--wp-profile weak\|mid\|good` | WordPress fixture hardening (default: `mid`) |
| `--keep-wp` | Skip `wp-down` after `--all` or `wp-integration` |
| `--no-report-prompt` | Skip “open pytest report in browser?” (CI / scripts) |
| `-y` / `--yes` | Skip GHCR double-confirm on `docker-push-ghcr` only |

### Pytest HTML reports (QA)

Each pytest run writes a **self-contained HTML report** with per-test **Test case** details (from docstrings or `@pytest.mark.test_case(...)`):

| Output | Path |
|--------|------|
| Dated pytest report | `pytest_reports/webaudit_pytest_YYYY-MM-DD_HHMMSS.html` |
| Coverage (separate) | `htmlcov/index.html` |

After pytest, the orchestrator asks whether to open the report in your browser (lists older reports by index). Manage reports standalone:

```bash
./scripts/pytest_reports.sh help
./scripts/pytest_reports.sh list
./scripts/pytest_reports.sh open 0          # newest
WEBAUDIT_SKIP_PYTEST_OPEN=1 ./orchestrate.sh --pytest-only   # no prompt
```

Requires `pytest-html` (`pip install -e '.[dev]'`).

### Python resolution order

1. `v2_python_core/.venv/bin/python` (from `./dev-venv.sh setup`)
2. `python3.12` / `python3` on PATH
3. Fallback: `python:3.12-slim` container for pytest only

### Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `WP_PORT` | `8080` | Host port for WordPress |
| `WEBAUDIT_WP_TEST_URL` | `http://127.0.0.1:8080` | Integration scan target |
| `WEBAUDIT_WP_PROFILE` | `mid` | Fixture hardening profile |
| `WEBAUDIT_IMAGE` | `webaudit:local` | Docker tag for Pro image |
| `GHCR_OWNER` | from `git remote` | GitHub user/org for manual push |
| `WEBAUDIT_SKIP_PYTEST_OPEN` | unset | Set to `1` to skip pytest report browser prompt |
| `WEBAUDIT_PYTEST_REPORTS_DIR` | `pytest_reports/` | Override dated HTML report directory |

---

## WordPress test profiles

Configured in `docker/wp-test/init-wordpress.sh` via WP-CLI after core install.

| Profile | Aliases | wp-config | Theme |
|---------|---------|-----------|-------|
| **weak** | `minimal` | No `DISALLOW_*` | Parent only |
| **mid** | `ok` | `DISALLOW_FILE_EDIT` | Parent only |
| **good** | `strong` | Both constants | Child theme `webaudit-child` |

Plugins installed: **Contact Form 7**, **Yoast SEO (wordpress-seo)**.  
Theme: **Twenty Twenty-Four** (child on `good`).

Web Audit **cannot read wp-config from outside** — profiles let you compare scan output and manual verification on a known local site.

```bash
WEBAUDIT_WP_PROFILE=weak ./orchestrate.sh --job wp-up
webaudit scan http://127.0.0.1:8080 -v --open html
```

---

## webaudit Pro Docker image

### Pull from GHCR (after CI publish or manual push)

Replace `Vlad-1618M` with your GitHub username/org:

```bash
docker pull ghcr.io/Vlad-1618M/webaudit:latest
docker run --rm ghcr.io/Vlad-1618M/webaudit:latest scan https://example.com --open none
```

Tags pushed by CI:

| Tag | When |
|-----|------|
| `2.1.0b2` (package version) | Every publish |
| `latest` | Push to `v.tools_main` or `main` |
| `sha-abc1234` | Git commit short SHA |
| `v2.1.0b2` | Git tag starting with `v` |

### Build locally

```bash
cd v2_python_core
./orchestrate.sh --job docker-build

docker run --rm webaudit:local scan https://example.com --open none
```

Scan local WP fixture (join Docker network):

```bash
docker run --rm --network webaudit-test-net \
  -v "$(pwd)/audit_logs:/work/audit_logs" \
  webaudit:local scan http://wordpress -v --open none
```

Dockerfile: `docker/webaudit/Dockerfile`

---

## GitHub Container Registry (GHCR)

### Do you need to set up the registry first?

**No.** The package is **created automatically on the first push**. No repo checkbox or empty package required.

After the first publish:

1. Open **GitHub → Packages → webaudit**
2. **Package settings → Link repository** → `web_audit`
3. Confirm visibility is **Public** (recommended for a public tool)

### Automatic publish (CI)

Workflow: `.github/workflows/ci.yml` — job **`publish-ghcr`**

Runs when **unit tests pass** and you **push** to:

- `v.tools_main`
- `main`
- Any tag starting with `v` (e.g. `v2.1.0b2`)

**Pull requests:** build + smoke test only — **no push** (so forks cannot publish to your GHCR).

Uses `GITHUB_TOKEN` with `packages: write` — no extra secrets required.

### Manual publish from GitHub UI

Workflow: **Actions → Publish GHCR image → Run workflow**

Optional extra tag input. Always pushes version from `webaudit/__version__.py` and `latest`.

### Manual publish from your machine

While testing locally:

```bash
cd v2_python_core

# 1. Build
./orchestrate.sh --job docker-build

# 2. Log in (once per machine)
gh auth login
gh auth token | docker login ghcr.io -u YOUR_GITHUB_USER --password-stdin

# 3. Push (prompts twice — public GHCR package; use --yes to skip in scripts)
./orchestrate.sh --job docker-push-ghcr

# Or explicitly:
GHCR_OWNER=Vlad-1618M ./orchestrate.sh --job docker-push-ghcr
```

PAT alternative (classic token scopes: `read:packages`, `write:packages`):

```bash
echo "$GITHUB_PAT" | docker login ghcr.io -u YOUR_GITHUB_USER --password-stdin
docker tag webaudit:local ghcr.io/YOUR_GITHUB_USER/webaudit:2.1.0b2
docker push ghcr.io/YOUR_GITHUB_USER/webaudit:2.1.0b2
docker push ghcr.io/YOUR_GITHUB_USER/webaudit:latest
```

**Safety prompts:** `./orchestrate.sh --job docker-push-ghcr` asks **twice** (y/N) before uploading — the image is **public** on GHCR and overwrites `:latest` / version tags. `docker-build` alone never pushes. Use `--yes` only in non-interactive scripts when you mean to publish.

### Docker Hub (optional mirror)

Same image, different registry — tag and push separately if you want `docker pull youruser/webaudit` on Docker Hub. GHCR is enough for most GitHub-hosted projects.

---

## GitHub Actions (PR gate)

See also: [CI pipeline diagram](#github-actions-ci-githubworkflowsciyml) and [local vs CI parity](#ci-vs-local-orchestrator-parity).

| Workflow | Purpose |
|----------|---------|
| `.github/workflows/ci.yml` | Unit tests + WP integration + Docker build + **GHCR publish on main** |
| `.github/workflows/publish-ghcr.yml` | Manual **Run workflow** publish |
| `.github/workflows/security.yml` | CodeQL, pip-audit, dependency review on PRs |
| `.github/dependabot.yml` | Weekly pip + Actions updates |

PRs touching `v2_python_core/**` must pass **unit-tests** before merge.

Local parity with CI:

```bash
./orchestrate.sh --pytest-only
# or non-interactive:
./orchestrate.sh --pytest-only --no-report-prompt
```

QA can review the dated HTML report under `pytest_reports/` — each test row expands to a **Test case** description. Override per test with a docstring or `@pytest.mark.test_case("…")` in unit tests.

---

## Manual Docker Compose (without orchestrator)

```bash
cd v2_python_core
export WEBAUDIT_WP_PROFILE=mid
docker compose -f docker/docker-compose.yml up -d wp-db wordpress
docker compose -f docker/docker-compose.yml run --rm wp-init
curl -I http://127.0.0.1:8080/
WEBAUDIT_WP_TEST_URL=http://127.0.0.1:8080 pytest tests/integration -v -m integration
docker compose -f docker/docker-compose.yml down -v
```

---

## What integration tests assert

See `tests/integration/test_wp_docker_scan.py`:

- Framework detected as **wordpress**
- At least one **plugin** observed
- **Theme** slug from HTML / `style.css`
- **Child theme** on `good` profile
- **wp-config hardening VERIFY** when wp-login is reachable (mentions `DISALLOW_FILE_EDIT` and `DISALLOW_FILE_MODS`)

---

## Related docs

- [testing.md](testing.md) — unit vs integration pyramid
- [getting_started_plain.md](getting_started_plain.md) — non-technical overview
- [wordpress_theme_threat_model.md](wordpress_theme_threat_model.md) — theme / DISALLOW_* rationale
