# Public installer DMG (bundled Python engine)

**Audience:** site owners — no repo clone, no Docker, no Terminal.

**Engine:** `webaudit` Python package bundled inside `Web Audit.app/Contents/Resources/Engine/`.

## Build

```bash
./build-dmg.sh
```

Downloads a relocatable Python (first run only), installs `webaudit` from `v2_python_core/`, assembles the `.app`, and creates:

`../installers/WebAudit-<version>-macOS.dmg`

The DMG also includes **`Clear-Quarantine.command`** — early adopters double-click it after dragging the app to Applications; Terminal clears download quarantine (`xattr -cr`). Steps are in `INSTALL.txt`.

## Smoke test

```bash
./smoke-install.sh
```

Validates DMG install, `Clear-Quarantine.command`, correct `INSTALL.txt` (no Docker setup steps), Playwright bundle, and bundled `Engine/bin/webaudit --help`.
