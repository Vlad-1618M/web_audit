# Web Audit for Mac — release notes

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
