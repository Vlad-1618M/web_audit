# Web Audit for Mac — release notes (public installer)

## 0.1.0 (stable)

**Status:** Stable · **Signing:** Developer ID signed + Apple notarized (ship with `orchestrate-macos.sh public-notarize`).

**DMG:** `WebAudit-0.1.0-macOS.dmg` — self-contained; scan engine + headless browser bundled inside the app.

**Git tag:** `macos-v0.1.0` · **Bundled engine:** `webaudit 2.1.0b4` (from `v2_python_core` at build time)

### What’s new since beta

- **Developer ID signing + notarization** — Gatekeeper-friendly public DMG (no quarantine helper script)
- **DMG installer UX** — fixed background scaling (144 DPI), clearer layout; `INSTALL.txt` bottom-left
- **Default scan depth** — `--js` and `--api` on every scan (Playwright + GraphQL/OpenAPI probes)
- **HTML report** — PASS verdict and summary banner styled green (matches in-app)
- **Web Audit Pro app icon** — macOS squircle mask
- **Report ready UI** — host on one line; full-width hoverable scanned URL; saved reports picker

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

1. Download `WebAudit-0.1.0-macOS.dmg` from [GitHub Releases](https://github.com/Vlad-1618M/web_audit/releases) or [muzar.io](https://muzar.io/).
2. Open DMG → drag **Web Audit** to **Applications**.
3. Open **Web Audit** from Applications (double-click works on notarized builds).
4. Paste a URL and scan — see `INSTALL.txt` in the DMG if anything fails.

### Uninstall

Drag **Web Audit.app** to Trash. Reports in `~/Documents/WebAudit/` are optional to delete.

### Known limitations

- **CI-built DMGs** (GitHub Actions on tag push) are still **unsigned** — use the **notarized** DMG uploaded to the release after local `public-notarize`, or build locally
- WhatsApp / some social apps do not register with macOS Share — use Gmail in browser or save zip
- Chrome as default “Mail” handler cannot attach files — use **Gmail in browser** or **Apple Mail** in the app

### Downloads

| Channel | Asset |
|---------|-------|
| GitHub Releases | `WebAudit-0.1.0-macOS.dmg` on tag `macos-v0.1.0` |
| muzar.io | Same hosted download |

### Maintainer build (signed release)

```bash
cd macos
./orchestrate-macos.sh public-smoke
./orchestrate-macos.sh public-notarize   # Developer ID + notarytool + staple
```

See [SIGNING.md](macos/packaging/public-installer/SIGNING.md).

---

## 0.1.0-beta (superseded)

`macos-v0.1.0-beta` — unsigned beta; `Clear-Quarantine.command` removed in 0.1.0 stable. Use **0.1.0** for new installs.

---

## 0.1.0-alpha (superseded)

Early alpha builds (`macos-v0.1.0-alpha`, `macos-v0.1.0-alpha.1`) — launch fix in `.1`; stable **0.1.0** supersedes for new installs.

---

*Developer build with external Docker/venv engine: `WebAudit-*-macOS-dev.dmg` — see `packaging/dev-external-engine/`.*
