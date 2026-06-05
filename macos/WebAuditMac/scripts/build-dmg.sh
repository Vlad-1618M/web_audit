#!/usr/bin/env bash
# Full pipeline: release binary → .app → .dmg
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

"$ROOT/scripts/build-release.sh"
"$ROOT/scripts/make-app-bundle.sh"
"$ROOT/scripts/make-dmg.sh"

echo ""
echo "Done. Ship: dist/WebAudit-$(tr -d '[:space:]' < VERSION)-macOS.dmg"
