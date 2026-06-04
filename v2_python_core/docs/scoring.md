# Web Audit v2 — Scoring & Verdict Math

*How I turn findings into numbers and a plain-language verdict. v1 parity first, then extensions.*

---

## Design goals

1. **Understandable** — a site owner sees red/yellow/green, not CVE jargon.
2. **Deterministic** — same `audit_run.json` → same scores; fully unit-tested.
3. **Compatible** — Hygiene and Exposure mean what v1 users expect.
4. **Extensible** — Tier 2 adds weighted risk and diff; core math stays stable.

---

## Finding model (input to scoring)

Every analyzer emits a `Finding`:

```python
# implemented — webaudit/models/finding.py
Finding(
    category="HEADERS",           # TLS, DNS, PATHS, ...
    item="Content-Security-Policy",
    status="MISSING",             # machine status
    severity="HIGH",              # CRITICAL | HIGH | MEDIUM | LOW | INFO
    class_="ACTION",              # ACTION | VERIFY | EXPECTED | INFO
    scored=True,                  # affects Hygiene when ACTION
    detail="No CSP header on homepage",
    evidence={ ... },             # optional structured proof
)
```

**Auto-downgrade (v1 parity):** statuses like `OK`, `PRESENT`, `REJECTED`, `PROTECTED`, `SECURE`, `NONE_FOUND`, `EXPECTED` → class **INFO**, `scored=False`.

---

## Hygiene score (0–100)

**Question:** *How well is the site configured?*

**Start:** `hygiene = 100`

**Apply only:** `class == ACTION` and `scored == True`

| Severity | Points deducted |
|----------|-----------------|
| CRITICAL | 25 |
| HIGH     | 10 |
| MEDIUM   | 4 |
| LOW      | 1 |

```text
hygiene = max(0, 100 - sum(deductions))
```

**Example:**

- 1× HIGH (−10) + 2× MEDIUM (−8) → **Hygiene = 82**

**Does NOT affect Hygiene:**

- VERIFY, EXPECTED, INFO
- Open non-sensitive paths marked REVIEW
- DNS informational records (unless configured as scored ACTION)

### Tier 2 extension: category caps (optional)

I may add config knobs to prevent one category from dominating:

```yaml
scoring:
  hygiene_caps:
    HEADERS: 30   # max 30 points off from header issues per run
```

Default: **no caps** (v1 behavior). **Tier 2b default for extensions:**

```yaml
scoring:
  hygiene_caps:
    PLUGIN: 30
    PLUGIN_CVE: 30
    THEME: 25
    THEME_CVE: 25
    PACKAGE: 30      # Django / Laravel
    GEM: 30          # Rails
  plugin_worst_wins: true   # optional — use highest-severity extension finding only
```

---

## Plugin & extension findings (Tier 2b)

Categories: `PLUGIN*` (WordPress plugins), `THEME*` (WordPress themes), `PACKAGE*` (Django/Laravel), `GEM*` (Rails), plus shared `*_VERIFY` / `*_INFO` variants.

**WordPress themes (Tier 2b+):** Stale free themes on wordpress.org → ACTION (`THEME` / `STALE`); premium parent themes → VERIFY; child theme → INFO; update-trap on watchlist parents without child theme → VERIFY. See [wordpress_theme_threat_model.md](wordpress_theme_threat_model.md).

| Finding | Class | Scored | Hygiene | Exposure |
|---------|-------|--------|---------|----------|
| Free plugin behind wp.org latest | ACTION | yes | MEDIUM–HIGH (gap size) | no |
| Premium plugin detected | VERIFY | no | — | — |
| Unauth CVE match | ACTION | yes | per CVSS | yes if critical unauth |
| Auth-required CVE (Contributor+) | VERIFY | no | — | — |
| No version string | VERIFY | no | — | — |
| Unknown / custom slug | VERIFY | no | — | — |

**Never label “nulled”** in automated output — use `verify_updates` / `verify_maintenance` (see [plugin_vulnerability_research.md](plugin_vulnerability_research.md)).

**Exposure:** only when `exposure_on_unauth_cve_only: true` (framework profile default) and CVE requires no authentication.

**v1 parity note:** v1 `PLUGIN_VERSION` / EXPOSED / MEDIUM with WPScan URL → v2 splits into PLUGIN + optional PLUGIN_CVE with structured evidence.

---

## SEO surface findings (Tier 2c — never scored by default)

Category: **`SEO_SURFACE`**. All findings **INFO** or **VERIFY** unless I explicitly override in custom rules (shipped default: never).

| Finding | Class | Hygiene | Exposure |
|---------|-------|---------|----------|
| Homepage `noindex` | VERIFY | no | no |
| Missing meta description | INFO | no | no |
| Canonical missing/duplicate | INFO | no | no |
| robots.txt blocks `/` | VERIFY | no | no |
| Broken internal link (sample) | INFO | no | no |

```yaml
scoring:
  seo_surface_affects_scores: false   # hard default
```

**Verdict:** SEO_SURFACE findings **do not** change PASS / NEEDS_ATTENTION / AT_RISK.

Full check list: [seo_surface.md](seo_surface.md).

---

## Exposure score (0–100)

**Question:** *Are secrets or sensitive files reachable?*

**UI label (2.1.0a1 reports):** **Leak protection** with **/100** suffix — e.g. `100/100` means no obvious public leaks (good), not “100% exposed.”

**Start:** `exposure = 100`

**Apply only:** sensitive path probes where HTTP status ∈ `{200, 500, 502, 503, 504}` (5xx treated as “might be leaking error/debug” — v1 parity).

| Event | Deduction |
|-------|-----------|
| Each sensitive path with qualifying status | **−25** |

```text
exposure = max(0, 100 - 25 * leak_count)
```

**Sensitive path list:** inherited from v1 `is_sensitive_path()` logic — `.env`, `.git/HEAD`, `wp-config.php`, `settings.py`, dumps, etc. Defined in config `paths.sensitive_builtin` + overrides.

**Does NOT reduce Exposure:**

- `expected_open` routes in site config
- Built-in login surfaces (`/wp-login.php`, `/admin/login/`, …)
- robots.txt, sitemap (public SEO)
- 403/404 on sensitive paths (good — no deduction)

**Example:**

- `.env` → 200, `.git/HEAD` → 200 → **Exposure = 50**

---

## Verdict (new in v2 — plain language)

Hygiene and Exposure are two axes. I add a single **Verdict** for executive reports.

### Step 1 — band each score

| Score range | Band |
|-------------|------|
| 90–100 | GOOD |
| 70–89 | FAIR |
| 50–69 | POOR |
| 0–49 | CRITICAL |

### Step 2 — combine matrix

| Exposure band | Hygiene band | Verdict | Owner-facing label |
|---------------|--------------|---------|-------------------|
| GOOD | GOOD | **PASS** | Looks reasonably hardened |
| GOOD | FAIR/POOR | **NEEDS_ATTENTION** | No obvious leaks, but config gaps |
| POOR/CRITICAL | any | **AT_RISK** | Sensitive exposure detected |
| any | CRITICAL | **AT_RISK** | Severe misconfiguration |
| POOR | POOR | **AT_RISK** | Fix both exposure and hygiene |

**Override rules (hard stops):**

- Any **CRITICAL** ACTION finding with category `PATHS` and status `OPEN` on `.env` or `.git` → **AT_RISK** regardless of math
- Certificate **EXPIRED** → **AT_RISK**
- Config `scoring.verdict_override` for site-specific rules (enterprise tier later)

```python
# pseudocode
def compute_verdict(hygiene: int, exposure: int, findings: list) -> str:
    if has_hard_stop(findings):
        return "AT_RISK"
    h_band = band(hygiene)
    e_band = band(exposure)
    if e_band in ("POOR", "CRITICAL") or h_band == "CRITICAL":
        return "AT_RISK"
    if h_band in ("FAIR", "POOR") and e_band == "GOOD":
        return "NEEDS_ATTENTION"
    if h_band == "GOOD" and e_band == "GOOD":
        return "PASS"
    return "NEEDS_ATTENTION"
```

---

## Risk index (Tier 2 — optional fourth number)

For technical reports and diffs:

```text
risk_index = (100 - hygiene) * 0.6 + (100 - exposure) * 0.4
```

Weighted toward hygiene because most sites fail config, not open `.env`. Display 0–100 where **lower is better** — or invert for UI as “safety index” = `100 - risk_index`.

Config:

```yaml
scoring:
  show_risk_index: true
  risk_weights:
    hygiene: 0.6
    exposure: 0.4
```

---

## Baseline diff math (Tier 2)

When comparing run **B** to baseline **A**:

| Change | Diff severity |
|--------|---------------|
| New sensitive path OPEN | **REGRESSION** (critical) |
| Hygiene dropped ≥ 10 points | **REGRESSION** |
| Hygiene improved ≥ 10 points | **IMPROVEMENT** |
| New ACTION finding | **NEW_ISSUE** |
| ACTION finding resolved | **RESOLVED** |
| DNS/TLS cosmetic INFO | **INFO** |
| New PLUGIN_CVE (unauth) | **REGRESSION** (critical) |
| Plugin version improved | **IMPROVEMENT** |

```text
delta_hygiene = hygiene_B - hygiene_A
delta_exposure = exposure_B - exposure_A
```

Report section: **Changes since {date}** with counts per bucket.

---

## CI gate math (v1 parity)

Flags:

```bash
webaudit scan URL --fail-under-hygiene 80 --fail-under-exposure 100
```

```text
exit 0 if hygiene >= threshold_h AND exposure >= threshold_e
exit 1 otherwise
exit 2 config/usage error
```

---

## DNS & TLS findings — scoring policy

**Tier 1 default:**

| Finding type | Class | Scored |
|--------------|-------|--------|
| DMARC missing | ACTION | yes (MEDIUM) |
| SPF missing | ACTION | yes (LOW) |
| DNSSEC not enabled | INFO | no |
| TLS 1.0/1.1 accepted | ACTION | yes (HIGH/MEDIUM — v1 parity) |
| Weak cipher | ACTION | yes (HIGH) |
| Cert expires < 30d | ACTION | yes (HIGH) |
| Cert expired | ACTION | yes (CRITICAL) |
| AAAA not published | INFO | no |

All tunable in `config/scoring_rules.yaml` without code changes.

---

## Worked example (full)

**Findings (scored ACTION only):**

1. CSP missing — HIGH (−10)
2. X-Frame-Options missing — MEDIUM (−4)
3. DMARC missing — MEDIUM (−4)
4. TLS 1.1 accepted — MEDIUM (−4)

**Hygiene:** 100 − 22 = **78** (FAIR)

**Exposure:** no sensitive leaks → **100** (GOOD)

**Verdict:** **NEEDS_ATTENTION** (good exposure, fair hygiene)

**Owner text (executive template):**

> Your site does not show obvious secret files to the public, but several standard security headers and email protections are missing. Share this report with your developer.

---

## pytest requirements for scoring

Golden files:

```text
tests/fixtures/scoring/
  case_hygiene_only.json      → expected 82
  case_exposure_double.json   → expected 50
  case_verdict_at_risk.json   → AT_RISK
  case_hard_stop_env.json     → AT_RISK override
  case_plugin_cap.json        → 5 stale plugins capped at 30 hygiene loss
  case_plugin_auth_cve.json   → VERIFY not scored
```

Every severity × class combination gets at least one unit test.

Plugin CVE cases sourced from [plugin_vulnerability_research.md](plugin_vulnerability_research.md) §4 as fixtures — not hardcoded in scorer.

---

*Related: [testing.md](testing.md) · [roadmap.md](roadmap.md) · [framework_profiles.md](framework_profiles.md) · [seo_surface.md](seo_surface.md)*
