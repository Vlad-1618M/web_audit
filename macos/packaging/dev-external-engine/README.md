# Dev external-engine DMG

**Audience:** repo developers and testers.

**Engine:** host-installed — Docker (`webaudit-docker`), venv `webaudit`, or PATH. Nothing bundled inside the app.

## Build

```bash
./build-dmg.sh
```

Output: `../installers/WebAudit-<version>-macOS-dev.dmg`

## Run without DMG

```bash
../../WebAuditMac/run-dev.sh
```

Sets `WEBAUDIT_ENGINE_POLICY=external` and points at repo `webaudit-docker.sh` when available.
