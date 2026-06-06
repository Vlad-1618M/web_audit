# Web Audit for Mac (SwiftUI)

Native macOS app for site owners — same flow as [designs/swift](../../designs/swift/) mockups.

**Status:** **0.1.0-beta** (unsigned) · **DMG / notarization:** in progress (`Clear-Quarantine.command` + Right-click → Open for now)

**Architecture & module guide (non-Swift devs):** [SWIFT_APP_GUIDE.md](SWIFT_APP_GUIDE.md) — file-by-file map, libraries, dev build vs `.dmg`, screenshot placeholders, Mermaid diagrams.

---

## Requirements

- macOS 13+
- Xcode 15+ or Swift 5.9+ toolchain
- **Dev run** — scan engine on host (one of):
  - **`webaudit-docker`** — Docker Desktop + [install from image](../../v2_python_core/docs/docker_ci.md)
  - **`webaudit`** CLI — dev venv or pipx
- **Public `.dmg`** — bundled Python engine (no Docker); see packaging below

## Packaging tracks

| Track | Command | DMG |
|-------|---------|-----|
| **Public installer** | `../orchestrate-macos.sh public-dmg` | `../installers/WebAudit-*-macOS.dmg` (~400 MB with bundled JS browser) |
| **Dev external-engine** | `../orchestrate-macos.sh dev-dmg` | `../installers/WebAudit-*-macOS-dev.dmg` |

Details: [../packaging/README.md](../packaging/README.md)

---

## Build & run (Swift Package)

```bash
cd macos/WebAuditMac
swift build
./run-dev.sh
```

**Do not** run `.build/debug/WebAuditMac` in the **foreground** in Terminal — the shell keeps keyboard focus and your typing lands in the terminal (you'll see `http…` in the shell). Use `./run-dev.sh` instead (backgrounds the app, keeps `WEBAUDIT_*` exports).

Other options:

```bash
open .build/debug/WebAuditMac          # detached, but does not pass custom env vars
(.build/debug/WebAuditMac &)           # manual background; disown optional
```

First launch avoids Gatekeeper blocking an unsigned binary. For Finder double-click, use Right-click → **Open** until notarized.

**Quit:** **⌘Q** on the app window — not Ctrl+C in Terminal (that does not stop a GUI app or Docker cleanly).

---

## Stop a scan / cleanup

| Situation | What to do |
|-----------|------------|
| Scan running | Click **Cancel scan** in the app (kills the wrapper + scan subprocess) |
| Quit the app | **⌘Q** or Web Audit → **Quit** |
| Launched from Terminal | Close the window with **⌘Q**; ignore Ctrl+C in the shell |
| Docker still running | `docker ps` then `docker stop <container_id>` |
| Nuclear option | Activity Monitor → quit **WebAuditMac**; then `docker stop $(docker ps -q --filter ancestor=ghcr.io/vlad-1618m/webaudit:latest)` if needed |

Partial reports under `~/Documents/WebAudit/` are harmless; delete old run folders manually if you want disk back.

---

## Dev: point at this repo

If `webaudit-docker` is not installed globally:

```bash
export WEBAUDIT_REPO="/Users/you/path/to/web_audit"
export WEBAUDIT_DOCKER_SCRIPT="$WEBAUDIT_REPO/v2_python_core/scripts/webaudit-docker.sh"

# Or native venv:
export WEBAUDIT_VENV="$WEBAUDIT_REPO/v2_python_core/.venv"

cd macos/WebAuditMac && swift build && .build/debug/WebAuditMac
```

---

## Build installer (.app + .dmg) for release

Use the orchestrator from `macos/` (two DMG tracks):

```bash
cd macos
./orchestrate-macos.sh public-dmg   # site owners → installers/WebAudit-<VERSION>-macOS.dmg
./orchestrate-macos.sh public-smoke
./orchestrate-macos.sh dev-dmg      # developers → installers/WebAudit-<VERSION>-macOS-dev.dmg
./orchestrate-macos.sh dev-smoke
```

Each DMG includes its own `INSTALL.txt`, **Web Audit.app**, and an **Applications** shortcut.
Public `INSTALL.txt` does **not** mention Docker; dev `INSTALL.txt` documents external engine setup.

**Supported macOS:** 13, 14, 15 (see `VERSION` + [RELEASE_NOTES.md](RELEASE_NOTES.md) → public notes in `packaging/public-installer/`).

**GitHub Release:** push tag `macos-v0.1.0-beta` or run workflow **Release macOS app** (uploads DMG + release notes).

**Unit tests:** `swift test` (requires full **Xcode.app** selected in `xcode-select`, not Command Line Tools alone). CI runs tests on `macos-14`.

First launch (unsigned): **Right-click → Open** in Applications.

---

## Xcode (optional)

```bash
cd macos/WebAuditMac
open Package.swift   # opens as Swift package in Xcode
# Run scheme WebAuditMac (My Mac)
```

Notarization / Developer ID signing — Stage 2 (after DMG pipeline is verified).

---

## What it does

1. Enter URL → **Scan my website**
2. Live log streams `webaudit -v` output (auto-scroll)
3. On success: in-app **verdict + hygiene/exposure scores** (from `audit_run.json`), metric chips, fix-first list
4. **Open report in browser**, **Save report to share** (zip), Finder, Share sheet (Mail / Gmail / AirDrop)
5. **Saved reports** — loads past scans from `~/Documents/WebAudit/` on relaunch; switch reports, zip all, delete all (with confirm)
6. **Scan failure** — diagnostic log file, **Try again** / **Back to home**, copyable support email
7. **Learn more** — docs, install guide, shell V1, Docker package (devs), contact
8. Reports under **`~/Documents/WebAudit/`**; failure logs under **`~/Documents/WebAudit/Logs/`**
9. Footer: Powered by [muzar.io](https://muzar.io/) · [GitHub](https://github.com/Vlad-1618M) · © Vtools

**Engine:** public `.dmg` = bundled (no Docker). Dev `run-dev.sh` / dev `.dmg` = external (Docker, venv, or PATH). See [DELIVERY_PATHS.md](../../DELIVERY_PATHS.md).

---

## Distribution

| Step | Status |
|------|--------|
| Public + dev `.dmg` scripts | **Done** — `../orchestrate-macos.sh public-dmg` / `dev-dmg` |
| GitHub Releases `.dmg` | Workflow `.github/workflows/release-macos.yml` (tag `macos-v*`) |
| muzar.io download page | Link to GitHub Release asset (placeholder until tag) |
| Apple notarization | **Later** (unsigned: Right-click → Open) |

---

## Related

- **Swift code guide:** [SWIFT_APP_GUIDE.md](SWIFT_APP_GUIDE.md)
- UI mockups & user-flow diagrams: [designs/swift/](../../designs/swift/) · [user-flow.md](../../designs/swift/user-flow.md)
- Docker wrapper: [v2_python_core/scripts/webaudit-docker.sh](../../v2_python_core/scripts/webaudit-docker.sh)
- Plain-English guide: [getting_started_plain.md](../../v2_python_core/docs/getting_started_plain.md)
