#!/usr/bin/env bash
# Assemble Web Audit.app from release binary + resources.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_NAME="Web Audit"
BUNDLE_ID="io.vtools.weaudit.mac"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
BUILD_NUMBER="${BUILD_NUMBER:-1}"
MIN_MACOS="${MIN_MACOS:-13.0}"

BIN="$ROOT/.build/release/WebAuditMac"
APP="$ROOT/build/${APP_NAME}.app"

if [[ ! -x "$BIN" ]]; then
  echo "error: run scripts/build-release.sh first (missing $BIN)" >&2
  exit 1
fi

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

cp "$BIN" "$APP/Contents/MacOS/WebAuditMac"
chmod +x "$APP/Contents/MacOS/WebAuditMac"

cp "$ROOT/Sources/WebAuditMac/Resources/"*.png "$APP/Contents/Resources/" 2>/dev/null || true
"$ROOT/scripts/make-icns.sh" "$APP/Contents/Resources/AppIcon.icns"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleExecutable</key>
  <string>WebAuditMac</string>
  <key>CFBundleIconFile</key>
  <string>AppIcon</string>
  <key>CFBundleIdentifier</key>
  <string>${BUNDLE_ID}</string>
  <key>CFBundleName</key>
  <string>${APP_NAME}</string>
  <key>CFBundleDisplayName</key>
  <string>${APP_NAME}</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>${VERSION}</string>
  <key>CFBundleVersion</key>
  <string>${BUILD_NUMBER}</string>
  <key>LSMinimumSystemVersion</key>
  <string>${MIN_MACOS}</string>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>NSHumanReadableCopyright</key>
  <string>Copyright © 2026 Vtools. All rights reserved.</string>
</dict>
</plist>
PLIST

echo "OK: $APP"
echo "    version=${VERSION} min_macos=${MIN_MACOS}"
