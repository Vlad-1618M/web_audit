# Web Audit v2 — Implementation Tracker

*Single source of truth for what is built, what is reserved, and how to extend without breaking the plan.*

Update this file **whenever** a module lands or a contract changes. Cross-check [stages.md](stages.md) and [architecture.md](architecture.md).

---

## Version

| Tag | Date | Notes |
|-----|------|-------|
| **2.0.0a1** | 2026-05 | Stage 1 alpha — CLI, config, headers + DNS, scoring, `audit_run.json` |

See [CHANGELOG.md](../CHANGELOG.md) for release notes.

---

## Module status (Tier 1)

| Module | Collector | Analyzer | Orchestrator | Tests | Stage |
|--------|-----------|----------|--------------|-------|-------|
| **headers** | `collectors/headers.py` ✓ | `analyzers/headers.py` ✓ | wired ✓ | ✓ | 1 |
| **dns** | `collectors/dns.py` ✓ | `analyzers/dns.py` ✓ | wired ✓ | ✓ | 1 |
| **paths** | — | — | — | — | **2 next** |
| **tls** | — | — | — | — | 2 |
| **policy** (CSP/HSTS parse) | — (uses headers artifact) | — | — | — | 2 |
| **cookies** | — | — | — | — | 2 |
| **artifacts** (robots, security.txt, sitemap) | — | — | — | — | 2 |
| **rate_limit** | — | — | — | — | 2 |
| **cors** | — | — | — | — | 2 |
| **framework** detect | — | — | — | — | 2–3 |
| **html** (DOM inventory) | — | — | — | — | 2–3 |
| **scoring** | n/a | n/a | `scoring/engine.py` ✓ | ✓ | 1 (partial 3) |
| **render** | — | — | — | — | 4 |
| **profiles** (WP/Django YAML) | — | — | — | — | 5 / 2b |

**Do not rename** shipped modules (`headers`, `dns`) — tests and `audit_run.json` artifacts depend on keys.

---

## Stage 2 backlog (ordered — avoid reordering without updating this doc)

1. **paths** — Exposure score; v1 `is_sensitive_path()` parity  
   - Files: `collectors/paths.py`, `analyzers/paths.py`  
   - Config: `PathsSettings` in `settings.py` (stub exists)  
   - Artifact key: `artifacts.inventory.paths` or dedicated `artifacts.paths` (pick one in paths PR; document here)  
   - Finding category: `PATHS`

2. **tls** — cert dates, versions, chain  
   - Files: `collectors/tls.py`, `analyzers/tls.py`  
   - Artifact key: `artifacts.tls` (reserved in `AuditArtifacts`)  
   - Deps: add `cryptography` to `pyproject.toml` in tls PR

3. **policy** — CSP/HSTS deep parse (v1 `check_policy_parse`)  
   - Files: `analyzers/policy.py` (reads `artifacts.headers`, no new collector)  
   - Finding categories: `POLICY`, `HEADERS` (match v1 report sections)

4. **cookies**, **artifacts**, **rate_limit**, **cors** — per [stages.md](stages.md) Tier 1 table

5. **framework** + **html** — before Stage 4 reports; feeds Stage 5 profiles

---

## Extension contract (orchestrator)

All scan modules follow the same pattern. **Do not** put HTTP I/O in analyzers or scoring in collectors.

```text
1. collector → dataclass with .to_artifact() → dict
2. analyzer  → list[Finding]
3. orchestrator.run_audit() appends findings + merges artifacts
4. score_findings(all_findings) once at end
5. write_audit_run()
```

Register new work in `webaudit/pipeline.py` (preferred) or append in `orchestrator.py` following existing headers/DNS blocks.

**Finding rules:**

- Use `Finding.from_check()` for v1 parity auto-downgrade  
- Categories must match [scoring.md](scoring.md) (`HEADERS`, `DNS`, `PATHS`, `TLS`, `POLICY`, …)  
- Tier 2c `SEO_SURFACE` — never ACTION/scored by default  
- Tier 2b `PLUGIN*` — see [plugin_vulnerability_research.md](plugin_vulnerability_research.md)

**Artifact keys** (reserved in `AuditArtifacts` — do not repurpose):

| Key | Owner stage | Status |
|-----|-------------|--------|
| `headers` | 1 | live |
| `dns` | 1 | live |
| `tls` | 2 | reserved |
| `inventory` | 2–3 | reserved (paths, URLs, images) |
| `plugins` | 5 / 2b | reserved |
| `seo_surface` | 5 / 2c | reserved |

---

## Config contract

Merge order (do not change without updating [config.md](config.md)):

```text
defaults.yaml → ~/.config/webaudit/config.yaml → ./webaudit.yaml → --config → --site-config
```

| YAML section | Pydantic model | Wired to orchestrator |
|--------------|----------------|------------------------|
| `runtime.*` | `RuntimeSettings` | ✓ |
| `collectors.dns.*` | `DnsCollectorSettings` | ✓ |
| `paths.*` | `PathsSettings` | stub only — Stage 2 |
| `collectors.tls.*` | not yet | Stage 2 |
| `scoring.*` | `ScoringSettings` | ✓ |
| `report.*` | `ReportSettings` | Stage 4 |
| `output.*` | `OutputSettings` | ✓ (json only) |

Adding a collector: extend `CollectorsSettings`, add defaults in `defaults.yaml`, snapshot appears in `config_snapshot` automatically via `model_dump()`.

---

## JSON schema stability

- `schema_version`: `"2.0"` — bump only on breaking `audit_run.json` shape changes  
- New artifact keys: **additive only** until 3.0  
- New finding categories: additive; scoring must ignore unknown categories safely  

---

## v1 parity reference

When implementing Stage 2 modules, mirror behavior from repo root `web_audit.sh` (read-only reference — **never import or source v1**):

| v2 module | v1 function (approx.) |
|-----------|------------------------|
| headers | `check_headers()` |
| policy | `check_policy_parse()` |
| paths | `is_sensitive_path()`, path probe loop |
| tls | `check_tls()`, `openssl_cert_info()` |
| cookies | cookie flag checks in v1 |
| dns | new in v2 (no v1 equivalent) |

Document intentional deltas in this file under **Parity deltas** when behavior differs.

### Parity deltas (known)

| Area | v2 today | v1 | Notes |
|------|----------|-----|-------|
| HSTS at CDN edge | ACTION if missing | VERIFY if CDN detected | CDN detect not ported yet — Stage 2/3 |
| Permissions-Policy missing | INFO, unscored | same | ✓ |
| DNS | scored SPF/DMARC | n/a | new signal |

---

## Checklist before merging Stage 2 PRs

- [ ] Row added/updated in **Module status** table above  
- [ ] `pipeline.py` or orchestrator wired; no scoring logic in collector  
- [ ] Unit tests with mocks (no live internet in CI)  
- [ ] `defaults.yaml` + `PathsSettings` / collector settings if new flags  
- [ ] [CHANGELOG.md](../CHANGELOG.md) Unreleased section  
- [ ] Parity delta noted if v1 behavior intentionally differs  

---

*Last updated: Stage 1 alpha (2026-05).*
