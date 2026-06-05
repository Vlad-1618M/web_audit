#!/usr/bin/env bash
# Delegates to dev external-engine DMG (backward compatible).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec "$ROOT/packaging/dev-external-engine/build-dmg.sh"
