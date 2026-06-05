#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../_shared/paths.sh
source "$ROOT/../_shared/paths.sh"

BUNDLE_ID="io.vtools.weaudit.mac"
BUILD_NUMBER="${BUILD_NUMBER:-1}"
MIN_MACOS="${MIN_MACOS:-13.0}"
ENGINE_POLICY="bundled"
ENGINE_SRC="$ROOT/build/engine"

BIN="$APP_ROOT/.build/release/WebAuditMac"
APP="$ROOT/build/${APP_NAME}.app"

[[ -x "$BIN" ]] || { echo "error: run build-release.sh first (missing $BIN)" >&2; exit 1; }
[[ -x "$ENGINE_SRC/bin/webaudit" ]] || {
  echo "error: run bundle-engine.sh first (missing $ENGINE_SRC/bin/webaudit)" >&2
  exit 1
}

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

cp "$BIN" "$APP/Contents/MacOS/WebAuditMac"
chmod +x "$APP/Contents/MacOS/WebAuditMac"

cp "$APP_ROOT/Sources/WebAuditMac/Resources/"*.png "$APP/Contents/Resources/" 2>/dev/null || true
cp "$ROOT/INSTALL.txt" "$APP/Contents/Resources/INSTALL.txt"
"$ROOT/../_shared/make-icns.sh" "$APP/Contents/Resources/AppIcon.icns"

rm -rf "$APP/Contents/Resources/Engine"
cp -R "$ENGINE_SRC" "$APP/Contents/Resources/Engine"

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
  <key>WEBAUDITEnginePolicy</key>
  <string>${ENGINE_POLICY}</string>
</dict>
</plist>
PLIST

echo "OK: $APP"
echo "    version=${VERSION} policy=${ENGINE_POLICY} min_macos=${MIN_MACOS}"
du -sh "$APP/Contents/Resources/Engine"
