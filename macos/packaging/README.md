# macOS packaging

**Delivery paths (app vs Docker vs venv):** [DELIVERY_PATHS.md](../../DELIVERY_PATHS.md)

Two DMG tracks share one Swift UI (`../WebAuditMac/`).

| Path | Audience | Engine | DMG output |
|------|----------|--------|------------|
| [dev-external-engine/](dev-external-engine/) | Repo developers | Host: Docker, `.venv`, or PATH | `../installers/WebAudit-*-macOS-dev.dmg` |
| [public-installer/](public-installer/) | Site owners | Bundled in `Resources/Engine/` | `../installers/WebAudit-*-macOS.dmg` |

Built DMGs live in **[../installers/](../installers/)** (gitignored). Scripts and `build/` staging stay here.

Each track ships its own **`INSTALL.txt`** inside the DMG (public = no Docker; dev = external engine setup).
Do not use legacy `WebAuditMac/packaging/INSTALL.txt`.

## Commands

From `macos/`:

```bash
./orchestrate-macos.sh dev-run
./orchestrate-macos.sh public-dmg
./orchestrate-macos.sh public-smoke
```
