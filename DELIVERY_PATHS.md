# How to run Web Audit — delivery paths

**One scan engine** (`webaudit` v2 Python core). **Several ways to install and launch it.** Pick the row that matches who you are — not every path needs Docker.

| # | Who | How | Engine location | Docker? | Terminal for scans? |
|---|-----|-----|-----------------|---------|---------------------|
| **A** | **Site owner (Mac)** | Public `.dmg` → drag **Web Audit** to Applications | **Bundled** inside `Web Audit.app/Contents/Resources/Engine/` | **No** | **No** — paste URL in app |
| **B** | Site owner (any OS) | `webaudit-docker` + GHCR image | Docker container | **Yes** (one-time setup) | Once for setup; then one command per scan |
| **C** | Repo developer (Mac UI) | `./run-dev.sh` or **dev DMG** | Host: Docker **or** `.venv` **or** PATH `webaudit` | Optional | Dev setup only |
| **D** | Developer / CI | `webaudit` in Python **venv** or **pip** | Local Python | **No** | Yes |
| **E** | Developer / CI | `docker run` / compose | GHCR image | **Yes** | Yes |
| **F** | Minimal / SSH | **v1** `web_audit.sh` | Bash only | **No** | Yes |

**Reports (v2):** usually `~/Documents/WebAudit/<run>/` with `report.html`, `audit_run.json`, `report.css`.

---

## A — Mac app, public installer (recommended for site owners)

- **Artifact:** `WebAudit-*-macOS.dmg` from [GitHub Releases](https://github.com/Vlad-1618M/web_audit/releases) (current: tag `macos-v0.1.0-beta` → `WebAudit-0.1.0-beta-macOS.dmg`) or build: `macos/orchestrate-macos.sh public-dmg`
- **Engine:** bundled Python + `webaudit` — no Docker, no `python.org` install, no Terminal during scans
- **Docs:** `macos/packaging/public-installer/INSTALL.txt` (in DMG and inside app **Learn more**)
- **Not the same as:** dev DMG (`WebAudit-*-macOS-dev.dmg`) — that row is **C**

---

## B — Docker only (no Mac app)

- **Image:** `ghcr.io/vlad-1618m/webaudit:latest` ([package page](https://github.com/Vlad-1618M/web_audit/pkgs/container/webaudit))
- **Helper:** `webaudit-docker` on PATH (extract from image — see [root README](README.md#docker--github-packages--v2-audit-pro))
- **Plain English:** [v2_python_core/docs/getting_started_plain.md](v2_python_core/docs/getting_started_plain.md)

---

## C — Mac app + external engine (developers)

- **Run:** `macos/WebAuditMac/run-dev.sh` (sets `WEBAUDIT_ENGINE_POLICY=external`)
- **Or DMG:** `macos/orchestrate-macos.sh dev-dmg` → `WebAudit-*-macOS-dev.dmg`
- **Engine (pick one):** `webaudit-docker` · `v2_python_core/.venv` · `pip install webaudit`
- **Docs:** `macos/packaging/dev-external-engine/INSTALL.txt`

---

## D — Python venv / pip (no Docker)

```bash
cd v2_python_core && ./dev-venv.sh   # or: pip install / pipx install webaudit
webaudit scan https://example.com -v --open html
```

See [v2_python_core/README.md](v2_python_core/README.md).

---

## E — Docker run (automation / servers)

```bash
docker run --rm -v "$(pwd)/audit_logs:/work/audit_logs" \
  ghcr.io/vlad-1618m/webaudit:latest scan -v --open none https://example.com
```

See [v2_python_core/docs/docker_ci.md](v2_python_core/docs/docker_ci.md).

---

## F — v1 shell (bash, no Docker, no Python package)

```bash
./web_audit.sh https://example.com
```

See [README — v1 section](README.md#v1-audit-lite--bash-quick-start). In the Mac app: **Learn more → Web Audit shell V1**.

---

## Mac app engine policy (implementation)

| Policy | Set by | Engine search order |
|--------|--------|---------------------|
| `bundled` | Public `.app` / DMG `Info.plist` | `Resources/Engine/bin/webaudit` first |
| `external` | `run-dev.sh`, dev DMG, env `WEBAUDIT_ENGINE_POLICY=external` | Docker → CLI → bundled fallback |

Code: `macos/WebAuditMac/Sources/WebAuditMac/ScanRunner.swift`

---

## What was dropped | deferred

| Item | Status |
|------|--------|
| Platypus `.app` wrapper | Deferred — [designs/platypus/](designs/platypus/) mockups only |
| Mac app **requires** Docker for everyone | **Dropped** for public DMG (row **A**) |
| Session-only history (max 10) | **Dropped** — disk-backed saved reports (up to 100 folders) |
| App Store / menu bar extra | Out of scope |

---

## Related

- [VERSIONING_AND_TAGS.md](VERSIONING_AND_TAGS.md) — git tags, GHCR, Mac versions
- [macos/README.md](macos/README.md) — build orchestrator
- [macos/WebAuditMac/SWIFT_APP_GUIDE.md](macos/WebAuditMac/SWIFT_APP_GUIDE.md) — Swift architecture

*Last updated: 2026-06-06 — Mac public DMG `0.1.0-beta`.*<br>
*- Vlad.M* 
