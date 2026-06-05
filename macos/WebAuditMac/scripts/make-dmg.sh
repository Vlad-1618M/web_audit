#!/usr/bin/env bash
# Legacy entry point — delegates to dev external-engine DMG (not the public installer).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "note: use macos/orchestrate-macos.sh public-dmg for site-owner builds" >&2
exec "$ROOT/packaging/dev-external-engine/build-dmg.sh"
