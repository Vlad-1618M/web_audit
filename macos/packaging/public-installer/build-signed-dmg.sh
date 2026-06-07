#!/usr/bin/env bash
# Build, Developer ID sign, and package public DMG (unsigned DMG; notarize separately).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../_shared/paths.sh
source "$ROOT/../_shared/paths.sh"

export WEBAUDIT_DISTRIBUTION_CHANNEL=release
"$ROOT/build-app.sh"
APP="$ROOT/build/${APP_NAME}.app"
"$ROOT/../_shared/sign-app-bundle.sh" "$APP"
"$ROOT/make-dmg.sh"

echo ""
echo "Done. Signed app + DMG: $INSTALLERS_ROOT/WebAudit-${VERSION}-macOS.dmg"
echo "Next: ./notarize-release.sh  (or orchestrate-macos.sh public-notarize)"
