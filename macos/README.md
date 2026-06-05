# macOS apps

**Which install path?** [DELIVERY_PATHS.md](../DELIVERY_PATHS.md) — public DMG (bundled, no Docker) vs dev app + external engine.

## Deliverables matrix

| # | Who | Engine | How to run |
|---|-----|--------|------------|
| 1 | Dev | `.venv` / `webaudit` CLI | `v2_python_core/dev-venv.sh` + Terminal |
| 2 | Dev | Docker + `webaudit-docker` | `v2_python_core/scripts/webaudit-docker.sh` |
| 3 | Dev | Swift UI + external engine | `WebAuditMac/run-dev.sh` or `orchestrate-macos.sh dev-run` |
| 4 | Dev | External-engine DMG | `orchestrate-macos.sh dev-dmg` |
| 5 | **Site owner** | **Bundled Python in app** | **`orchestrate-macos.sh public-dmg`** → drag to Applications |

## Paths

| Path | Purpose |
|------|---------|
| [WebAuditMac/](WebAuditMac/) | **Shared SwiftUI source** — one app, two engine policies |
| [packaging/](packaging/) | Build scripts (dev + public tracks) — **keep in git** |
| [installers/](installers/) | **Built `.dmg` files** — gitignored, safe to delete |
| [orchestrate-macos.sh](orchestrate-macos.sh) | Build menu for both tracks |
| [WebAuditMac/SWIFT_APP_GUIDE.md](WebAuditMac/SWIFT_APP_GUIDE.md) | Architecture guide for non-Swift devs |

Design reference: [designs/swift/](../designs/swift/)

**Versions & tags:** [VERSIONING_AND_TAGS.md](../VERSIONING_AND_TAGS.md) — git tags, GHCR, Mac DMG, dev vs stable (draft).

## Engine policy

Set in `Info.plist` (`WEBAUDITEnginePolicy`) or `WEBAUDIT_ENGINE_POLICY` env:

- **`bundled`** — public `.dmg`; uses `Contents/Resources/Engine/bin/webaudit`
- **`external`** — dev; prefers Docker / venv / PATH

`run-dev.sh` sets `external` automatically.

## Installer output

All DMGs land in **`installers/`**:

| File | Command |
|------|---------|
| `WebAudit-*-macOS.dmg` | `./orchestrate-macos.sh public-dmg` |
| `WebAudit-*-macOS-dev.dmg` | `./orchestrate-macos.sh dev-dmg` |

```bash
./orchestrate-macos.sh clean-installers   # remove DMGs only
rm -rf installers/*.dmg                 # or delete manually
```
