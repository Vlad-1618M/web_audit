#!/usr/bin/env bash
# Notarize + staple signed .app, rebuild DMG, notarize + staple DMG.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../_shared/paths.sh
source "$ROOT/../_shared/paths.sh"

APP="$ROOT/build/${APP_NAME}.app"
DMG="$INSTALLERS_ROOT/WebAudit-${VERSION}-macOS.dmg"

[[ -d "$APP" ]] || {
  echo "error: missing $APP — run build-signed-dmg.sh or build-app.sh + sign-app-bundle.sh first" >&2
  exit 1
}

"$ROOT/../_shared/notarize-app.sh" "$APP"
"$ROOT/make-dmg.sh"
"$ROOT/../_shared/notarize-dmg.sh" "$DMG"

echo ""
echo "All notarization steps passed."
echo "  App: $APP"
echo "  DMG: $DMG"
