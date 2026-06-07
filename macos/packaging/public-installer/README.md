# Public installer DMG (bundled Python engine)

**Audience:** site owners — no repo clone, no Docker, no Terminal.

**Engine:** `webaudit` Python package bundled inside `Web Audit.app/Contents/Resources/Engine/`.

## Build

```bash
./build-dmg.sh
```

Downloads a relocatable Python (first run only), installs `webaudit` from `v2_python_core/`, assembles the `.app`, and creates:

`../installers/WebAudit-<version>-macOS.dmg`

DMG contents: **Web Audit.app**, **INSTALL.txt**, and an **Applications** shortcut.

**Release:** `cd macos && ./orchestrate-macos.sh public-notarize` — signed + notarized DMG for site owners. Unsigned local/CI builds: Right-click → Open on first launch (see `INSTALL.txt`).

## Smoke test

```bash
./smoke-install.sh
```

Validates DMG install (no quarantine script), correct `INSTALL.txt` (no Docker setup steps), Playwright bundle, and bundled `Engine/bin/webaudit --help`.

## Signing & notarization

See [SIGNING.md](SIGNING.md). Release path:

```bash
cd macos && ./orchestrate-macos.sh public-notarize
```

Local memo: `~/webaudit-release-tools/MAC_SIGNING_MEMO.txt`
