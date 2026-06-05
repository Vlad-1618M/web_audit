# Web Audit for Mac — release notes

## 0.1.0-alpha (unsigned)

**Status:** Early alpha · **Signing:** Not notarized — use Right-click → Open on first launch.

### What’s included

- Native Mac app: paste URL → scan → in-app scores + full HTML report
- Live scan log, session history, zip export (HTML + CSS), share sheet (Mail / Gmail / Messages / AirDrop)
- Requires **Docker Desktop** + **webaudit-docker** on PATH (one-time Terminal setup)

### System requirements

| Requirement | Detail |
|-------------|--------|
| **macOS** | **13 (Ventura), 14 (Sonoma), or 15 (Sequoia)** — current release plus two prior major versions |
| **Architecture** | Intel and Apple Silicon (universal binary when built on CI; arm64 or x86_64 from local `swift build` on your machine) |
| **Docker** | Docker Desktop + `webaudit-docker` helper ([pull-only setup](https://github.com/Vlad-1618M/web_audit/blob/v.tools_main/v2_python_core/docs/getting_started_plain.md)) |
| **Disk** | ~50 MB app; reports under `~/Documents/WebAudit/` |

### Install

1. Download `WebAudit-0.1.0-alpha-macOS.dmg` from [GitHub Releases](https://github.com/Vlad-1618M/web_audit/releases) or [muzar.io](https://muzar.io/).
2. Open DMG → drag **Web Audit** to **Applications**.
3. **Right-click → Open** the first time (unsigned build).
4. Complete one-time `webaudit-docker` setup (see `INSTALL.txt` in the DMG).

### Uninstall

Drag **Web Audit.app** to Trash. Reports in `~/Documents/WebAudit/` are optional to delete.

### Known limitations

- Scan engine not bundled — Docker required
- Unsigned: Gatekeeper warning on first open
- WhatsApp / some social apps do not register with macOS Share — use Gmail in browser or save zip
- Chrome as default “Mail” handler cannot attach files — use **Gmail in browser** or **Apple Mail** in the app

### Downloads

| Channel | Link |
|---------|------|
| GitHub Releases | `WebAudit-0.1.0-alpha-macOS.dmg` on tag `macos-v0.1.0-alpha` |
| muzar.io | Same asset URL (hosted download button) |

---

*Template for next release: bump VERSION, duplicate section above, list fixes/features.*
