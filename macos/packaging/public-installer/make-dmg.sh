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
ln -s /Applications "$STAGE/Applications"

rm -f "$DMG"
hdiutil create \
  -volname "Web Audit ${VERSION}" \
  -srcfolder "$STAGE" \
  -ov \
  -format UDZO \
  "$DMG" >/dev/null

echo "OK: $DMG"
du -h "$DMG"
