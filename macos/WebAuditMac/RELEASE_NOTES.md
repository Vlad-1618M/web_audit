# Web Audit for Mac — release notes

**Current public version:** `0.1.0` (stable) · tag `macos-v0.1.0` · DMG `WebAudit-0.1.0-macOS.dmg`

Two installer tracks — use the right DMG for your audience:

| Audience | DMG | Notes |
|----------|-----|-------|
| **Site owners** | `WebAudit-*-macOS.dmg` | Bundled scan engine — **no Docker** · **signed + notarized** for release |
| **Developers** | `WebAudit-*-macOS-dev.dmg` | External engine (Docker / venv) |

**Public release notes (GitHub / muzar.io):** [packaging/public-installer/RELEASE_NOTES.md](../packaging/public-installer/RELEASE_NOTES.md)

**Signing:** [packaging/public-installer/SIGNING.md](../packaging/public-installer/SIGNING.md)

**Build:**

```bash
cd macos
./orchestrate-macos.sh public-dmg          # unsigned (CI / quick test)
./orchestrate-macos.sh public-signed-dmg   # Developer ID sign + DMG
./orchestrate-macos.sh public-notarize     # sign + notarize + staple (ship to users)
./orchestrate-macos.sh dev-dmg             # developers
```
