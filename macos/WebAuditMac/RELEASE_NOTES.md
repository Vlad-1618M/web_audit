# Web Audit for Mac — release notes

**Current public version:** `0.1.0-beta` · tag `macos-v0.1.0-beta` · DMG `WebAudit-0.1.0-beta-macOS.dmg`

Two installer tracks — use the right DMG for your audience:

| Audience | DMG | Notes |
|----------|-----|-------|
| **Site owners** | `WebAudit-*-macOS.dmg` | Bundled scan engine — **no Docker** |
| **Developers** | `WebAudit-*-macOS-dev.dmg` | External engine (Docker / venv) |

**Public release notes (GitHub / muzar.io):** [packaging/public-installer/RELEASE_NOTES.md](../packaging/public-installer/RELEASE_NOTES.md)

**Build:**

```bash
cd macos
./orchestrate-macos.sh public-dmg    # site owners
./orchestrate-macos.sh dev-dmg       # developers
```
