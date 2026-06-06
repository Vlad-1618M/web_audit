# Release manager

Version bumps and release audit trail for **Web Audit** — Mac app (`macos/WebAuditMac/VERSION`) and Python engine (`v2_python_core/webaudit/__version__.py`).

**Python core** + **`bump-versions.sh`** wrapper. Stdlib only.

## Quick start

```bash
# From repo root
./release_manager/bump-versions.sh --help

# Preview Mac bump (no writes)
./release_manager/bump-versions.sh --dry-run --mac 0.1.0-beta

# Preview engine bump
./release_manager/bump-versions.sh --dry-run --engine 2.1.0

# Apply both (double confirm; archives first)
./release_manager/bump-versions.sh --both 0.1.0-beta 2.1.0

# Tag / smoke playbook only
./release_manager/bump-versions.sh --release-guide

# Last 5 release log entries
./release_manager/bump-versions.sh --log-tail 5

# Restore files from an archive run
./release_manager/bump-versions.sh --restore 20260606T120000Z-a1b2
```

## Layout

| Path | Purpose |
|------|---------|
| `bump_versions.py` | CLI entry |
| `bump-versions.sh` | Shell wrapper → Python |
| `version-bump-manifest.json` | Files and rules per channel |
| `release_bump/` | Python package |
| `releases/release-history.jsonl` | **Append-only** audit log (git-tracked) |
| `releases/RELEASE.log` | Human-readable append mirror |
| `.version-bump-archive/` | Per-run file snapshots (gitignored) |

## Safety

- **Archive** every touched file before rewrite
- **Double confirm** (unless `--yes`)
- **`--dry-run`** — preview only; still appends a `dry_run` line to JSONL
- **`--restore <run_id>`** — copy archive back; logs restore

## Manifest

Edit `version-bump-manifest.json` when new docs pick up version strings.  
Mac DMG naming reads `VERSION` at build time (`macos/packaging/_shared/paths.sh`) — no separate bump there.

## Related

- [VERSIONING_AND_TAGS.md](../VERSIONING_AND_TAGS.md)
- [DELIVERY_PATHS.md](../DELIVERY_PATHS.md)
