# Web Audit for Mac (SwiftUI)

Native macOS app for site owners — same flow as [designs/swift](../../designs/swift/) mockups.

**Status:** early alpha · **DMG / notarization:** in progress (local build + Right-click → Open for now)

**Architecture & module guide (non-Swift devs):** [SWIFT_APP_GUIDE.md](SWIFT_APP_GUIDE.md) — file-by-file map, libraries, dev build vs `.dmg`, screenshot placeholders, Mermaid diagrams.

---

## Requirements

- macOS 13+
- Xcode 15+ or Swift 5.9+ toolchain
- **Scan engine** (one of):
  - **`webaudit-docker`** on PATH (recommended) — Docker Desktop + [install from image](../../v2_python_core/docs/docker_ci.md)
  - **`webaudit`** CLI — dev venv or pipx

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

## Xcode (optional)

```bash
cd macos/WebAuditMac
open Package.swift   # opens as Swift package in Xcode
# Run scheme WebAuditMac (My Mac)
```

To ship a `.app` bundle / `.dmg`, add an Xcode **App** target or use `xcodebuild` archive — documented when notarization pipeline lands.

---

## What it does

1. Enter URL → **Scan my website**
2. Live log streams `webaudit -v` output (auto-scroll)
3. On success: in-app **verdict + hygiene/exposure scores** (from `audit_run.json`), metric chips, fix-first list
4. **Open report in browser**, **Save report to share** (zip with HTML + CSS + instructions), Finder, Share
5. **Session history** — reopen up to 10 scans from the same app session
6. Reports under **`~/Documents/WebAudit/`**
7. Footer: Powered by [muzar.io](https://muzar.io/) · [GitHub](https://github.com/Vlad-1618M) · © Vtools
8. **v1 shell edition** link — read/download `web_audit.sh` for users who do not trust the Mac app yet

---

## Distribution (later)

| Step | Status |
|------|--------|
| GitHub Releases `.dmg` | TODO |
| Apple notarization | **In progress** |
| muzar.io download page | TODO |

Until then: build from source or email a zip of `.build/debug/WebAuditMac` for trusted testers only.

---

## Related

- **Swift code guide:** [SWIFT_APP_GUIDE.md](SWIFT_APP_GUIDE.md)
- UI mockups & user-flow diagrams: [designs/swift/](../../designs/swift/) · [user-flow.md](../../designs/swift/user-flow.md)
- Docker wrapper: [v2_python_core/scripts/webaudit-docker.sh](../../v2_python_core/scripts/webaudit-docker.sh)
- Plain-English guide: [getting_started_plain.md](../../v2_python_core/docs/getting_started_plain.md)
