# Web Audit v2 — Testing Strategy

*I trust pytest, not manual re-runs against random sites. Tests are part of Tier 1, not an afterthought.*

---

## Why testing matters for this project

v1 grew to 3,000+ lines in one file. I could not refactor safely. v2 is modular **because** I want each module testable in isolation.

Goals:

1. **Scoring math never regresses** — golden JSON fixtures.
2. **Collectors don’t hit the live internet in CI** — mocks and cassettes.
3. **Templates render** — snapshot tests without brittle full HTML equality.
4. **v1 parity documented** — comparison tests where behavior should match.

---

## Test pyramid

```text
        ┌─────────────┐
        │  E2E smoke  │  1–2 live URLs, nightly optional
        ├─────────────┤
        │ Integration │  full scan against wiremock / pytest-httpx
        ├─────────────┤
        │    Unit     │  analyzers, scoring, config (majority)
        └─────────────┘
```

---

## Tooling

| Tool | Purpose |
|------|---------|
| **pytest** | Test runner |
| **pytest-asyncio** | Async collectors |
| **pytest-httpx** | Mock httpx requests declaratively |
| **pytest-cov** | Coverage gate (target 85%+ on scoring/analyzers) |
| **pytest-html** | Single dated HTML report with per-test details for QA |
| **orchestrate.sh** | Local CI — pytest first, optional WP Docker fixture ([docker_ci.md](docker_ci.md) · [diagrams](docker_ci.md#diagrams)) |
| **pytest_reports.sh** | List / open archived HTML reports ([docker_ci.md](docker_ci.md#pytest-html-reports-qa)) |
| **freezegun** | Cert expiry edge cases |
| **jsonschema** | Validate `audit_run.json` against schema |

```text
dev dependencies (pyproject.toml today):
  pytest>=8.0
  pytest-httpx>=0.30
  pytest-cov>=5.0
  pytest-html>=4.0

planned (Tier 1 complete):
  pytest-asyncio>=0.23
  freezegun>=1.4
  jsonschema>=4.21
```

---

## HTML reports for QA

Two different HTML outputs — do not confuse them:

| Report | Tool | Path | Contents |
|--------|------|------|----------|
| **Test run report** | pytest-html | `pytest_reports/webaudit_pytest_YYYY-MM-DD_HHMMSS.html` | Every test, pass/fail/skip, expandable **Test case** row |
| **Coverage report** | pytest-cov | `htmlcov/index.html` | Line coverage by module |

### Running locally

```bash
cd v2_python_core

# Recommended — unit tests + both reports + optional browser prompt
./orchestrate.sh --pytest-only

# CI / scripts — skip “open report in browser?”
./orchestrate.sh --pytest-only --no-report-prompt

# Raw pytest (same flags the orchestrator uses)
python -m pytest tests/unit -v -s -x -ra \
  --cov=webaudit --cov-report=html:htmlcov \
  --html=pytest_reports/webaudit_pytest_manual.html --self-contained-html
```

After `./orchestrate.sh --pytest-only`, the orchestrator lists saved reports (newest in **green**, older in **orange**) and asks whether to open one in the browser. Pick by index `0`, `1`, … or decline and copy the path.

Manage reports without re-running tests:

```bash
./scripts/pytest_reports.sh list
./scripts/pytest_reports.sh open 0
WEBAUDIT_SKIP_PYTEST_OPEN=1 ./orchestrate.sh --pytest-only
```

### Test case text in the HTML report

Each test row expands to a **Test case** block (not empty “No log output captured.” for passing tests). Resolution order in `tests/test_case.py` + `tests/conftest.py`:

1. `@pytest.mark.test_case("…")` — explicit QA wording (preferred for complex scenarios)
2. Function docstring — first paragraph shown as-is
3. Auto-generated fallback — `Area:` (module docstring) + `Test case: Ensures …`

**Example — explicit marker:**

```python
import pytest

@pytest.mark.test_case("GraphQL introspection must be flagged when __schema is returned.")
def test_graphql_introspection_detected(httpx_mock):
    ...
```

**Example — docstring (most unit tests today):**

```python
def test_graphql_introspection_detected(httpx_mock):
    """Ensures GraphQL introspection is detected when the endpoint returns schema data."""
    ...
```

To bulk-fill missing docstrings (one-time / after adding new tests):

```bash
python tests/test_case.py   # adds one-line docstrings where absent
```

QA workflow: open latest `pytest_reports/*.html` → filter by Failed/Skipped → expand row → read **Test case** → cross-check against product spec or manual test plan.

---

## Directory layout

```text
tests/
├── conftest.py                 # fixtures, HTML report hooks (Test case rows)
├── test_case.py                # resolve QA description for pytest-html
├── unit/
│   ├── test_config_loader.py
│   ├── test_scoring_hygiene.py
│   ├── test_scoring_exposure.py
│   ├── test_scoring_verdict.py
│   ├── test_analyzer_csp.py
│   ├── test_analyzer_html_forms.py
│   ├── test_analyzer_cookies.py
│   ├── test_dns_parser.py
│   ├── test_config_profiles.py      # Tier 2b — framework profile merge
│   ├── test_wp_themes.py
│   ├── test_wp_plugin_fingerprint.py
│   ├── test_wp_plugin_stale.py
│   ├── test_plugin_vuln_auth_class.py
│   └── test_seo_surface_unscored.py   # Tier 2c
├── integration/
│   ├── test_scan_wiremock.py
│   └── test_render_templates.py
├── parity/
│   └── test_v1_check_mapping.md   # human matrix + automated subset
└── fixtures/
    ├── html/
    ├── headers/
    ├── dns/
    ├── scoring/
    ├── plugins/
    │   ├── html_wp_assets.html
    │   ├── readme_elementor.txt
    │   └── cve_cases.json
    ├── seo/
    │   ├── homepage_noindex.html
    │   └── homepage_no_description.html
    └── v1_samples/
```

---

## Unit tests (by module)

### config/

- Valid minimal YAML loads
- Invalid severity override rejected
- CLI flag overrides merge correctly
- Site profile merges over global config
- Framework profile loads when `framework=wordpress`
- `site.extensions` overrides watchlist / probe.mode
- INI import (Tier 3) produces equivalent YAML

### scoring/

Table-driven tests:

```python
@pytest.mark.parametrize("findings,expected", [
    (load_fixture("case_hygiene_only.json"), 82),
    ...
])
def test_hygiene_score(findings, expected):
    assert compute_hygiene(findings) == expected
```

Cover:

- Floor at 0
- unscored ACTION ignored
- VERIFY/EXPECTED/INFO ignored
- hard-stop verdict overrides
- exposure 5xx vs 403
- PLUGIN hygiene cap at 30 with five stale plugins
- auth-required CVE → VERIFY, not scored

### analyzers/

Fixtures = real-world snippets (anonymized from muzar.io runs):

- CSP parser: unsafe-inline, missing default-src
- HTML: mixed content `<img src="http://...">`
- Cookies: missing Secure on session cookie
- Framework: wp-login body markers

**Plugins (Tier 2b):**

- Slug extract from `/wp-content/plugins/foo/bar.css?ver=1.2.3`
- readme.txt `Stable tag:` parse
- wp.org API mocked — stale vs current
- Premium slug → VERIFY not ACTION
- CVE fixtures from [plugin_vulnerability_research.md](plugin_vulnerability_research.md): unauth XSS → ACTION; Contributor XSS → VERIFY

No network. No live WPScan in unit tests.

**SEO surface (Tier 2c):**

- `noindex` → VERIFY, hygiene unchanged
- Missing description → INFO
- Assert `seo_surface_affects_scores: false` in scorer

### collectors/

Use **pytest-httpx**:

```python
def test_path_probe_200(httpx_mock):
    httpx_mock.add_response(url="https://example.com/.env", status_code=200)
    result = probe_paths(client, ["https://example.com/.env"])
    assert result[0].status_code == 200
```

DNS: mock `dns.resolver.Resolver.resolve` with fake answers.

TLS: fixture PEM certs for chain validation tests.

---

## Integration tests

**Local wiremock** or pytest-httpx sequence:

1. Run orchestrator against `https://test.local/` with 20 mocked responses
2. Assert `audit_run.json` schema valid
3. Assert finding count ≥ N
4. Render executive template — assert contains target hostname, scores

**Optional nightly** (GitHub Actions cron):

```yaml
# .github/workflows/nightly-live.yml (future)
- run: webaudit scan https://example.com --no-pdf
```

Not on every PR — flaky network.

---

## Template / render tests

```python
def test_executive_template_renders(sample_audit_run):
    html = render_html(sample_audit_run, variant="executive")
    assert "Acme Widgets" in html
    assert "NEEDS_ATTENTION" in html
    assert "<style" not in html  # CSS external link only
    assert 'href="executive.css"' in html
```

PDF test (when WeasyPrint installed):

```python
@pytest.mark.optional_pdf
def test_pdf_generation(sample_audit_run, tmp_path):
    pdf = render_pdf(sample_audit_run, variant="minimal")
    assert pdf.stat().st_size > 5000
```

Skip PDF in CI if optional dep not installed — but run on macOS/Linux matrix with `[pdf]` extra.

---

## v1 parity tests

I maintain `tests/parity/PARITY.md`:

| v1 check | v2 module | Parity |
|----------|-----------|--------|
| check_headers | analyzers.policy + collectors.headers | exact |
| check_tls | collectors.tls | extended (more data) |
| check_site_miscellaneous | analyzers.html_dom | extended |
| check_plugin_versions | collectors.wp_plugins + analyzers.wp_plugins | extended (compare + cap) |

Automated: load same mocked responses into v1 export (where possible) and v2; compare finding counts for core categories.

Full bash execution in CI is optional — run v1 `zsh -n web_audit.sh` syntax check only (no v1 code changes).

---

## CI pipeline (implemented)

See **[docker_ci.md](docker_ci.md)** for full detail.

| Workflow | Gate |
|----------|------|
| `.github/workflows/ci.yml` | Unit tests (required on PR) + WP Docker integration + Docker build |
| `.github/workflows/ci.yml` → `publish-ghcr` | Push `ghcr.io/<owner>/webaudit` on merge to `main` / `v.tools_main` / `v*` tags |
| `.github/workflows/publish-ghcr.yml` | Manual **Run workflow** GHCR publish |
| `.github/workflows/security.yml` | CodeQL, pip-audit, dependency review |

Local equivalent:

```bash
./orchestrate.sh --pytest-only
./orchestrate.sh --job wp-integration
```

Non-interactive (matches CI — no report browser prompt):

```bash
./orchestrate.sh --pytest-only --no-report-prompt
```

See [docker_ci.md — Pytest HTML reports](docker_ci.md#pytest-html-reports-qa) for report paths and env vars.

Separate job (future): `zsh -n web_audit.sh` — v1 syntax gate.

---

## Pre-commit (local)

```text
ruff check
ruff format --check
pytest tests/unit -q
# or full orchestrator parity:
./orchestrate.sh --pytest-only --no-report-prompt
```

Fast loop before push.

---

## What I will not test

- Live third-party sites on every PR (flaky, rude)
- Playwright in default CI (heavy); Tier 2 optional job with browser install
- Visual pixel-diff of PDFs — size + text extract sanity only

---

## Definition of done (testing) per stage

| Stage | Gate |
|-------|------|
| 1 | config + model tests green |
| 2 | all Tier 1 collectors mocked |
| 3 | scoring golden files 100% |
| 4 | three templates render |
| 5 | baseline diff + Tier 2b extensions + **WP theme fingerprint** + DNS enrichment + **Tier 2c SEO unscored** + Tier 2 depth (JS/API/links) + owner report UX tests (~200 unit tests) + **QA HTML test reports** |
| 6 | pip install + smoke scan in CI |

---

*Related: [scoring.md](scoring.md) · [architecture.md](architecture.md) · [docker_ci.md](docker_ci.md)*
