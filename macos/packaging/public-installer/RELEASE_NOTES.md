# Web Audit for Mac — release notes (public installer)

## 0.1.0-alpha (unsigned)

**Status:** Early alpha · **Signing:** Not notarized — use Right-click → Open on first launch.

**DMG:** `WebAudit-0.1.0-alpha-macOS.dmg` — self-contained; scan engine bundled inside the app.

### What’s included

- Native Mac app: paste URL → scan → in-app scores + full HTML report
- Live scan log, **saved reports** (reloads from disk on relaunch), zip export (HTML + CSS), share sheet (Mail / Gmail / Messages / AirDrop)
- **Bundled Python scan engine** — no Docker, no Terminal setup, no python.org install

### System requirements

| Requirement | Detail |
|-------------|--------|
| **macOS** | **13 (Ventura), 14 (Sonoma), or 15 (Sequoia)** |
| **Architecture** | Intel and Apple Silicon |
| **Network** | Internet access for scans |
| **Disk** | ~200 MB app + engine; reports under `~/Documents/WebAudit/` |

### Install

1. Download `WebAudit-0.1.0-alpha-macOS.dmg` from [GitHub Releases](https://github.com/Vlad-1618M/web_audit/releases) or [muzar.io](https://muzar.io/).
2. Open DMG → drag **Web Audit** to **Applications**.
3. **Right-click → Open** the first time (unsigned build).
4. Paste a URL and scan — see `INSTALL.txt` in the DMG if anything fails.

### Uninstall

Drag **Web Audit.app** to Trash. Reports in `~/Documents/WebAudit/` are optional to delete.

### Known limitations

- Unsigned: Gatekeeper warning on first open
- WhatsApp / some social apps do not register with macOS Share — use Gmail in browser or save zip
- Chrome as default “Mail” handler cannot attach files — use **Gmail in browser** or **Apple Mail** in the app

### Downloads

| Channel | Asset |
|---------|-------|
| GitHub Releases | `WebAudit-0.1.0-alpha-macOS.dmg` on tag `macos-v0.1.0-alpha` |
| muzar.io | Same hosted download |

---

*Developer build with external Docker/venv engine: `WebAudit-*-macOS-dev.dmg` — see `packaging/dev-external-engine/`.*
