#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../_shared/paths.sh
source "$ROOT/../_shared/paths.sh"

APP="$ROOT/build/${APP_NAME}.app"
STAGE="$ROOT/build/dmg-stage"
DMG_NAME="WebAudit-${VERSION}-macOS.dmg"
DMG="$INSTALLERS_ROOT/${DMG_NAME}"

[[ -d "$APP" ]] || { echo "error: run make-app-bundle.sh first (missing $APP)" >&2; exit 1; }

rm -rf "$STAGE"
mkdir -p "$STAGE" "$INSTALLERS_ROOT"

cp -R "$APP" "$STAGE/"
cp "$ROOT/INSTALL.txt" "$STAGE/"
# Applications drop link is added by create-dmg (--app-drop-link)

ICON_FILE="$APP/Contents/Resources/AppIcon.icns"
export ICON_FILE
chmod +x "$ROOT/../_shared/make-styled-dmg.sh"
"$ROOT/../_shared/make-styled-dmg.sh" "$DMG" "$STAGE" "Web Audit ${VERSION}"

echo ""
echo "Done. Public DMG: $DMG"
