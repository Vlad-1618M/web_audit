#!/usr/bin/env bash
# Create a drag-to-Applications DMG from build/Web Audit.app
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_NAME="Web Audit"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
APP="$ROOT/build/${APP_NAME}.app"
STAGE="$ROOT/build/dmg-stage"
DMG_NAME="WebAudit-${VERSION}-macOS.dmg"
DMG="$ROOT/dist/${DMG_NAME}"

if [[ ! -d "$APP" ]]; then
  echo "error: run scripts/make-app-bundle.sh first (missing $APP)" >&2
  exit 1
fi

rm -rf "$STAGE" "$ROOT/dist"
mkdir -p "$STAGE" "$ROOT/dist"

cp -R "$APP" "$STAGE/"
cp "$ROOT/packaging/INSTALL.txt" "$STAGE/"
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
