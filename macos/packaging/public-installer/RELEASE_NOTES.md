# Web Audit for Mac — release notes (public installer)

## 0.1.0-beta (unsigned)

**Status:** Beta · **Signing:** Not notarized — use `Clear-Quarantine.command` in the DMG, then Right-click → Open if needed.

**DMG:** `WebAudit-0.1.0-beta-macOS.dmg` — self-contained; scan engine + headless browser bundled inside the app.

**Git tag:** `macos-v0.1.0-beta` · **Bundled engine:** `webaudit 2.1.0b4` (from `v2_python_core` at build time)

### What’s new since alpha

- **JavaScript scans on by default** — Playwright + Chromium bundled; no extra setup for site owners
- **`Clear-Quarantine.command`** in the DMG — one double-click after install clears download quarantine
- **Web Audit Pro app icon** — from `webaudit_pro_icon.svg`, macOS squircle mask
- **Report ready UI** — host on one line with title; full-width hoverable scanned URL
- **Saved reports** — active **Viewing** row stays bright; other rows slightly dimmed

### What’s included

- Native Mac app: paste URL → scan → in-app scores + full HTML report
- Live scan log, **saved reports** (reloads from disk on relaunch), zip export (HTML + CSS), share sheet (Mail / Gmail / Messages / AirDrop)
- **Bundled Python scan engine** — no Docker, no Terminal setup, no python.org install

### System requirements

| Requirement | Detail |
|-------------|--------|
| **macOS** | **13 (Ventura), 14 (Sonoma), or 15 (Sequoia)** |
| **Architecture** | Apple Silicon (CI build); Intel Macs — test locally before relying on release |
| **Network** | Internet access for scans |
| **Disk** | ~400 MB app + engine + browser; reports under `~/Documents/WebAudit/` |

### Install

1. Download `WebAudit-0.1.0-beta-macOS.dmg` from [GitHub Releases](https://github.com/Vlad-1618M/web_audit/releases) or [muzar.io](https://muzar.io/).
2. Open DMG → drag **Web Audit** to **Applications**.
3. Double-click **`Clear-Quarantine.command`** on the DMG (Terminal clears download quarantine), then open **Web Audit** from Applications.
4. If macOS still warns once: **Right-click → Open** (unsigned build).
5. Paste a URL and scan — see `INSTALL.txt` in the DMG if anything fails.

### Uninstall

Drag **Web Audit.app** to Trash. Reports in `~/Documents/WebAudit/` are optional to delete.

### Known limitations

- Unsigned: Gatekeeper / “damaged” on first open — use `Clear-Quarantine.command` in the DMG, then Right-click → Open if needed
- WhatsApp / some social apps do not register with macOS Share — use Gmail in browser or save zip
- Chrome as default “Mail” handler cannot attach files — use **Gmail in browser** or **Apple Mail** in the app

### Downloads

| Channel | Asset |
|---------|-------|
| GitHub Releases | `WebAudit-0.1.0-beta-macOS.dmg` on tag `macos-v0.1.0-beta` |
| muzar.io | Same hosted download |

---

## 0.1.0-alpha (superseded)

Early alpha builds (`macos-v0.1.0-alpha`, `macos-v0.1.0-alpha.1`) — launch fix in `.1`; beta supersedes for new installs.

---

*Developer build with external Docker/venv engine: `WebAudit-*-macOS-dev.dmg` — see `packaging/dev-external-engine/`.*
