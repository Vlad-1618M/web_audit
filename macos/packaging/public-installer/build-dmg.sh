#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
find "$ROOT" "$ROOT/../_shared" -name '*.sh' -type f -print0 2>/dev/null | xargs -0 chmod +x 2>/dev/null || true

"$ROOT/../_shared/build-release.sh"
"$ROOT/bundle-engine.sh"
"$ROOT/make-app-bundle.sh"
"$ROOT/make-dmg.sh"

# shellcheck source=../_shared/paths.sh
source "$ROOT/../_shared/paths.sh"
echo ""
echo "Done. Public DMG: $INSTALLERS_ROOT/WebAudit-${VERSION}-macOS.dmg"
