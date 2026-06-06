#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../_shared/paths.sh
source "$ROOT/../_shared/paths.sh"

DMG="$INSTALLERS_ROOT/WebAudit-${VERSION}-macOS.dmg"
INSTALL_DIR="$(mktemp -d /tmp/webaudit-smoke-public.XXXXXX)"
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

echo "==> Building public bundled-engine DMG…"
"$ROOT/build-dmg.sh"
[[ -f "$DMG" ]] || fail "DMG missing: $DMG"

attach_dmg() {
  MOUNT="$(mktemp -d /tmp/webaudit-mnt-public.XXXXXX)"
  hdiutil attach "$DMG" -nobrowse -mountpoint "$MOUNT" -quiet
  [[ -d "$MOUNT/${APP_NAME}.app" ]] || fail "Could not mount DMG"
}

install_from_dmg() {
  local label="$1"
  echo "==> $label"
  attach_dmg
  [[ -d "$MOUNT/${APP_NAME}.app" ]] || fail "App not in DMG ($MOUNT)"
  [[ -f "$MOUNT/INSTALL.txt" ]] || fail "INSTALL.txt not in DMG"
  if grep -qiE 'docker desktop|webaudit-docker|docker pull' "$MOUNT/INSTALL.txt"; then
    fail "Public INSTALL.txt must not require Docker setup"
  fi
  if ! grep -qi 'self-contained' "$MOUNT/INSTALL.txt"; then
    fail "Public INSTALL.txt missing self-contained wording"
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
  [[ "$policy" == "bundled" ]] || fail "Expected WEBAUDITEnginePolicy bundled, got $policy"

  local engine="$app/Contents/Resources/Engine/bin/webaudit"
  [[ -x "$engine" ]] || fail "Bundled engine missing: $engine"

  if ! "$engine" --help >/dev/null 2>&1; then
    fail "Bundled webaudit --help failed"
  fi
  if ! "$engine" --version >/dev/null 2>&1; then
    fail "Bundled webaudit --version failed"
  fi
  ok "$label — bundled engine responds (--help and --version)"

  # shellcheck source=../_shared/smoke-app-launch.sh
  source "$ROOT/../_shared/smoke-app-launch.sh"
  smoke_app_launch "$app" || fail "App launch smoke failed"
}

install_from_dmg "Install #1"
rm -rf "$INSTALL_DIR/${APP_NAME}.app"
ok "Uninstall — removed app"
install_from_dmg "Reinstall #2"

echo ""
echo "All public smoke checks passed."
