# Versioning & tags history

**Purpose:** One place to track **git tags**, **Docker/GHCR tags**, and **Mac app releases** while naming conventions for dev vs stable are still being decided.

**How to run (all paths):** [DELIVERY_PATHS.md](DELIVERY_PATHS.md) — public Mac DMG, Docker-only, dev app, venv, v1 shell.

**Automated bumps:** [release_manager/README.md](release_manager/README.md) — `./release_manager/bump-versions.sh` (manifest-driven Mac/engine rewrites, archive, append-only `releases/release-history.jsonl`).

**Revisit later:** formal policy for `beta` / `ST` (stable) / `macos-v*` vs engine semver. <br>
This file is the working ledger — updates happen when I tag the release = publish

---

## Channels (draft taxonomy)

| Channel | Who | Primary artifact | Typical install | Git tags (today) | Stable naming (TBD) |
|---------|-----|------------------|-----------------|------------------|---------------------|
| **v2 engine — dev/beta** | Repo devs, CI | Python package `webaudit` | `pip install`, repo `.venv`, bundled in Mac `.app` | `v2.1.0bN` (preferred) or `2.1.0bN` | — |
| **v2 engine — stable** | Site owners, production | Same package, frozen API | pip pin, Mac public DMG engine | *not used yet* | e.g. `v2.1.0` or `2.1.0ST` |
| **Docker / GHCR** | Devs, servers, `webaudit-docker` users | OCI image | `docker pull ghcr.io/vlad-1618m/webaudit:TAG` | *no separate tag* — image tags track engine version on push to `main` / `v.tools_main` / `v*` | `:latest` + pinned semver |
| **Mac app — public** | Site owners (no Docker) | `WebAudit-*-macOS.dmg` | Drag to Applications | `macos-v*` | e.g. `macos-v0.1.0` after notarization |
| **Mac app — dev** | Repo testers | `WebAudit-*-macOS-dev.dmg` | External engine (Docker/venv) | optional `macos-dev-v*` | — |
| **v1 shell** | Minimal / read-the-script users | `web_audit.sh` | curl / clone, no tags | none (script in repo) | — |

**Rule of thumb (for now):**

- **Devs** → Docker/GHCR, dev DMG, `.venv`, `orchestrate.sh`
- **Prod / site owners (target)** → stable engine semver + **public Mac DMG** (bundled engine, no Terminal)

---

## Source of truth (current)

| What | File | Current value |
|------|------|---------------|
| Python engine semver | `v2_python_core/webaudit/__version__.py` | `2.1.0b4` |
| Python package metadata | `v2_python_core/pyproject.toml` | `2.1.0b4` |
| Mac app marketing version | `macos/WebAuditMac/VERSION` | `0.1.0-beta` |
| Mac bundled engine | built from `v2_python_core/` at DMG build time | matches `__version__.py` at build |
| Changelog (engine) | `v2_python_core/CHANGELOG.md` | see `[Unreleased]` + tagged sections |

---

## Git tag history

Sorted newest first. Run `git fetch --tags` then `git tag -l --sort=-creatordate` to refresh locally.

### Mac app (`macos-v*`)

| Tag | Date (approx) | Type | Notes |
|-----|---------------|------|-------|
| `macos-v0.1.0-beta` | *tag next* | **Mac beta** | `WebAudit-0.1.0-beta-macOS.dmg` — `--js` + `--api` default, Playwright bundled, signing/notarization pipeline, PRO icon, UI polish |
| `macos-v0.1.0-alpha.1` | 2026-06 | **Mac alpha** | Launch fix (SPM resource bundle); supersedes broken `macos-v0.1.0-alpha` |
| `macos-v0.1.0-alpha` | 2026-06 | **Mac alpha** | First public DMG — **do not use** (launch crash) |

### Engine (`v2.1.0b*`)

| Tag | Date (author commit) | Type | Notes |
|-----|----------------------|------|-------|
| `v2.1.0b4` | 2026-06-04 | **Engine beta** | Tier 3 CVE cache + SARIF + WP plugin polish |
| `v2.1.0b3` | 2026-06-04 | **Engine beta** | Stage 6 CI/Docker pipelines, GHCR publish, orchestrate |
| `2.1.0b2` | 2026-06-02 | **Engine beta** | Stage 5 beta — Tier 2 depth, report UX (tag without `v` prefix — prefer `v` for new tags) |

### Not tagged yet (planned)

| Planned tag | Artifact | Status |
|-------------|----------|--------|
| `v2.1.0` or `v2.1.0ST` | First **stable** engine + GHCR pin | Naming TBD — drop `b` suffix, document in CHANGELOG |
| `macos-v0.1.0` (or similar) | Signed/notarized public DMG | After Apple Developer ID |

**Mac beta note:** App `0.1.0-beta` can ship while engine stays `2.1.0b4` until a stable engine cut (`v2.1.0`) — rebuild DMG after engine bump to bundle the new semver.

---

## Docker / GHCR image tags

Published from CI on push to `main`, `v.tools_main`, or git tags starting with `v`.  
Package: [ghcr.io/vlad-1618m/webaudit](https://github.com/Vlad-1618M/web_audit/pkgs/container/webaudit)

| Image tag | When set | Maps to |
|-----------|----------|---------|
| `2.1.0b4` | CI publish | `__version__.py` at publish commit |
| `latest` | CI publish | same image as version tag |
| `sha-abcdefg` | CI publish | short git SHA |
| `v2.1.0b4` | CI publish | if git tag `v2.1.0b4` exists on that push |

**Dev pull (most common):**

```bash
docker pull ghcr.io/vlad-1618m/webaudit:latest
# or pin: docker pull ghcr.io/vlad-1618m/webaudit:2.1.0b4
```

Manual extra tag: workflow **Publish GHCR** (`.github/workflows/publish-ghcr.yml`).

---

## Mac app releases (DMG)

| Version file | DMG filename | Engine policy | INSTALL.txt |
|--------------|--------------|---------------|-------------|
| `0.1.0-beta` | `WebAudit-0.1.0-beta-macOS.dmg` | bundled (public) | `packaging/public-installer/INSTALL.txt` |
| `0.1.0-beta` | `WebAudit-0.1.0-beta-macOS-dev.dmg` | external Docker/venv | `packaging/dev-external-engine/INSTALL.txt` |
| `0.1.0-alpha` | `WebAudit-0.1.0-alpha-macOS.dmg` | bundled (public) | superseded — use beta |

Build: `macos/orchestrate-macos.sh public-dmg` / `dev-dmg` → output `macos/installers/`.

Release notes (public): `macos/packaging/public-installer/RELEASE_NOTES.md`

**Git tag for Mac releases:** `macos-v<VERSION>` (e.g. `macos-v0.1.0-beta`) — separate from engine `v2.x` tags so Docker users are not confused.

**Tag command (after `public-smoke` on release commit):**

```bash
git tag -s macos-v0.1.0-beta -m "Web Audit for Mac 0.1.0-beta"
git push origin macos-v0.1.0-beta
```

---

## Naming convention — revisit (TODO)

Open questions to decide before first **stable** release:

1. **Engine stable suffix** — `2.1.0` vs `2.1.0ST` vs `v2.1.0` (git) only?
2. **Beta** — keep `bN` (`2.1.0b5`) until stable cut?
3. **Mac app** — stay on `0.x` marketing version while engine is `2.x`? (yes: app `0.1.0-beta`, engine `2.1.0b4` today)
4. **GHCR** — publish `:stable` alias when engine hits stable, or only semver + `latest`?
5. **Bundled Mac DMG** — record engine semver in release notes / `INSTALL.txt` each build? (yes — see RELEASE_NOTES + INSTALL)

**Proposed stable cut checklist (draft):**

- [ ] Bump `__version__.py` to stable (no `b`)
- [ ] Tag `v2.1.0` (or agreed name)
- [ ] CHANGELOG section, not `[Unreleased]`
- [ ] GHCR publish + pin docs
- [ ] Rebuild public Mac DMG with new engine
- [ ] Tag `macos-v…` if shipping installer

---

## Related docs

| Doc | Topic |
|-----|--------|
| [v2_python_core/CHANGELOG.md](v2_python_core/CHANGELOG.md) | Engine release notes |
| [v2_python_core/docs/docker_ci.md](v2_python_core/docs/docker_ci.md) | Docker tags, CI publish |
| [macos/packaging/public-installer/RELEASE_NOTES.md](macos/packaging/public-installer/RELEASE_NOTES.md) | Mac public DMG notes |
| [.github/workflows/release-macos.yml](.github/workflows/release-macos.yml) | Mac GitHub Release on `macos-v*` |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) | GHCR publish on main / `v*` |

---

## Quick commands

```bash
# List git tags (newest first)
git fetch --tags
git tag -l --sort=-creatordate

# Show what's on a tag
git show macos-v0.1.0-beta --no-patch

# Local engine version
grep __version__ v2_python_core/webaudit/__version__.py

# Local Mac app version
cat macos/WebAuditMac/VERSION
```

*Last updated: 2026-06-06 — Mac `0.1.0-beta` docs; tag `macos-v0.1.0-beta` pending push.*<br>
*-Vlad.M*
