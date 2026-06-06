# macOS packaging

**Delivery paths (app vs Docker vs venv):** [DELIVERY_PATHS.md](../../DELIVERY_PATHS.md)

Two DMG tracks share one Swift UI (`../WebAuditMac/`).

| Path | Audience | Engine | DMG output |
|------|----------|--------|------------|
| [dev-external-engine/](dev-external-engine/) | Repo developers | Host: Docker, `.venv`, or PATH | `../installers/WebAudit-*-macOS-dev.dmg` |
| [public-installer/](public-installer/) | Site owners | Bundled in `Resources/Engine/` | `../installers/WebAudit-*-macOS.dmg` |

Built DMGs live in **[../installers/](../installers/)** (gitignored). Scripts and `build/` staging stay here.

Each track ships its own **`INSTALL.txt`** inside the DMG (public = no Docker; dev = external engine setup).

**DMG window:** branded background + drag-to-Applications layout via vendored [create-dmg](_shared/vendor/README.md). Icon positions: `_shared/dmg-layout.env` (shared with `generate-dmg-background.py`). Regenerate art after layout edits: `python3 _shared/generate-dmg-background.py`.

**App icon:** `_shared/make-icns.sh` rasterizes `Resources/webaudit_pro_icon.svg` (or falls back to `webaudit.png`), applies macOS squircle corners (~22.37% radius) via `render-macos-iconset.py`, writes `AppIcon.icns` plus synced `webaudit.png` for in-app branding. SVG rasterization uses macOS `qlmanage` (CI runs on `macos-14`).
Do not use legacy `WebAuditMac/packaging/INSTALL.txt`.

## Commands

From `macos/`:

```bash
./orchestrate-macos.sh dev-run
./orchestrate-macos.sh public-dmg
./orchestrate-macos.sh public-smoke
```
