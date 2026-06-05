#!/usr/bin/env bash
# Install / uninstall / reinstall smoke test for the DMG (no GUI scan).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_NAME="Web Audit"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
DMG="$ROOT/dist/WebAudit-${VERSION}-macOS.dmg"
INSTALL_DIR="$(mktemp -d /tmp/webaudit-smoke.XXXXXX)"
MOUNT="/Volumes/Web Audit ${VERSION}"

cleanup() {
  if mount | grep -q "Web Audit ${VERSION}"; then
    hdiutil detach "$MOUNT" -quiet 2>/dev/null || true
  fi
  rm -rf "$INSTALL_DIR"
}
trap cleanup EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
ok() { echo "OK: $*"; }

echo "==> Building DMG…"
"$ROOT/scripts/build-dmg.sh"

[[ -f "$DMG" ]] || fail "DMG missing: $DMG"

install_from_dmg() {
  local label="$1"
  echo "==> $label"
  hdiutil attach "$DMG" -nobrowse -quiet
  [[ -d "$MOUNT/${APP_NAME}.app" ]] || fail "App not in DMG"
  [[ -f "$MOUNT/INSTALL.txt" ]] || fail "INSTALL.txt not in DMG"
  rm -rf "$INSTALL_DIR/${APP_NAME}.app"
  cp -R "$MOUNT/${APP_NAME}.app" "$INSTALL_DIR/"
  hdiutil detach "$MOUNT" -quiet

  local app="$INSTALL_DIR/${APP_NAME}.app"
  local bin="$app/Contents/MacOS/WebAuditMac"
  [[ -x "$bin" ]] || fail "Binary not executable"

  local min_os
  min_os="$(/usr/libexec/PlistBuddy -c 'Print :LSMinimumSystemVersion' "$app/Contents/Info.plist")"
  [[ "$min_os" == "13.0" ]] || fail "Expected LSMinimumSystemVersion 13.0, got $min_os"

  local short_ver
  short_ver="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$app/Contents/Info.plist")"
  [[ "$short_ver" == "$VERSION" ]] || fail "Version mismatch: $short_ver vs $VERSION"

  ok "$label — bundle structure valid"
}

install_from_dmg "Install #1"
rm -rf "$INSTALL_DIR/${APP_NAME}.app"
ok "Uninstall — removed app"
install_from_dmg "Reinstall #2"

echo ""
echo "All smoke checks passed."
