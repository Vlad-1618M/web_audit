#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../_shared/paths.sh
source "$ROOT/../_shared/paths.sh"

DMG="$INSTALLERS_ROOT/WebAudit-${VERSION}-macOS-dev.dmg"
INSTALL_DIR="$(mktemp -d /tmp/webaudit-smoke-dev.XXXXXX)"
MOUNT=""

cleanup() {
  if [[ -n "$MOUNT" ]] && mount | grep -qF "$MOUNT"; then
    hdiutil detach "$MOUNT" -quiet 2>/dev/null || true
  fi
  rm -rf "$INSTALL_DIR"
}
trap cleanup EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
ok() { echo "OK: $*"; }

echo "==> Building dev external-engine DMG…"
"$ROOT/build-dmg.sh"
[[ -f "$DMG" ]] || fail "DMG missing: $DMG"

attach_dmg() {
  MOUNT="$(mktemp -d /tmp/webaudit-mnt-dev.XXXXXX)"
  hdiutil attach "$DMG" -nobrowse -mountpoint "$MOUNT" -quiet
  [[ -d "$MOUNT/${APP_NAME}.app" ]] || fail "Could not mount DMG"
}

install_from_dmg() {
  local label="$1"
  echo "==> $label"
  attach_dmg
  [[ -d "$MOUNT/${APP_NAME}.app" ]] || fail "App not in DMG ($MOUNT)"
  [[ -f "$MOUNT/INSTALL.txt" ]] || fail "INSTALL.txt not in DMG"
  if ! grep -qiE 'developer|external' "$MOUNT/INSTALL.txt"; then
    fail "Dev INSTALL.txt missing developer/external wording"
  fi
  rm -rf "$INSTALL_DIR/${APP_NAME}.app"
  cp -R "$MOUNT/${APP_NAME}.app" "$INSTALL_DIR/"
  hdiutil detach "$MOUNT" -quiet
  rmdir "$MOUNT" 2>/dev/null || true
  MOUNT=""

  local app="$INSTALL_DIR/${APP_NAME}.app"
  [[ -x "$app/Contents/MacOS/WebAuditMac" ]] || fail "Binary not executable"

  local policy
  policy="$(/usr/libexec/PlistBuddy -c 'Print :WEBAUDITEnginePolicy' "$app/Contents/Info.plist")"
  [[ "$policy" == "external" ]] || fail "Expected WEBAUDITEnginePolicy external, got $policy"

  ok "$label — dev bundle valid"
}

install_from_dmg "Install #1"
rm -rf "$INSTALL_DIR/${APP_NAME}.app"
ok "Uninstall — removed app"
install_from_dmg "Reinstall #2"

echo ""
echo "All dev smoke checks passed."
