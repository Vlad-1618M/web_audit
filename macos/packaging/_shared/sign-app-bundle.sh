#!/usr/bin/env bash
# Sign Web Audit.app for Developer ID + notarization (Engine, Playwright, main binary).
set -euo pipefail

SHARED="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "$SHARED/paths.sh"

ENTITLEMENTS="${ENTITLEMENTS:-$SHARED/../public-installer/entitlements.plist}"
NOTARY_PROFILE="${NOTARY_PROFILE:-webaudit-notarize}"

usage() {
  cat <<EOF
Usage: $(basename "$0") <path/to/Web Audit.app>

Environment:
  SIGN_ID              Developer ID Application name or SHA-1 hash (auto-detected if unset)
  ENTITLEMENTS         Path to entitlements.plist (default: public-installer/entitlements.plist)
  NOTARY_PROFILE       Keychain profile for notarytool (default: webaudit-notarize)

Example:
  $(basename "$0") packaging/public-installer/build/Web\\ Audit.app
EOF
}

fail() { echo "error: $*" >&2; exit 1; }

resolve_sign_id() {
  if [[ -n "${SIGN_ID:-}" ]]; then
    echo "$SIGN_ID"
    return
  fi
  local line
  line="$(security find-identity -v -p codesigning 2>/dev/null \
    | grep 'Developer ID Application' | head -1 || true)"
  [[ -n "$line" ]] || fail "no Developer ID Application identity (run: security find-identity -v -p codesigning)"
  echo "$line" | sed -E 's/^[[:space:]]*[0-9]+\)[[:space:]]+[0-9A-Fa-f]+[[:space:]]+"([^"]+)"/\1/'
}

is_macho() {
  file "$1" 2>/dev/null | grep -q 'Mach-O'
}

sign_macho() {
  local target="$1"
  local sign_id="$2"
  codesign --force --options runtime --timestamp --sign "$sign_id" "$target"
}

[[ $# -ge 1 ]] || { usage >&2; exit 1; }
APP="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
[[ -d "$APP/Contents/MacOS/WebAuditMac" ]] || fail "not a Web Audit app bundle: $APP"
[[ -f "$ENTITLEMENTS" ]] || fail "missing entitlements: $ENTITLEMENTS"

SIGN_ID="$(resolve_sign_id)"
echo "==> Signing: $APP"
echo "    identity: $SIGN_ID"

echo "==> Mach-O libraries (.dylib, .so)…"
while IFS= read -r -d '' f; do
  is_macho "$f" || continue
  sign_macho "$f" "$SIGN_ID"
done < <(find "$APP" -type f \( -name '*.dylib' -o -name '*.so' \) -print0)

echo "==> Mach-O executables…"
while IFS= read -r -d '' f; do
  is_macho "$f" || continue
  sign_macho "$f" "$SIGN_ID"
done < <(find "$APP" -type f -perm -111 -print0)

echo "==> Nested .app bundles (Playwright helpers, innermost first)…"
while IFS= read -r nested; do
  [[ -n "$nested" ]] || continue
  sign_macho "$nested" "$SIGN_ID"
done < <(find "$APP/Contents" -name '*.app' -type d -print 2>/dev/null \
  | awk '{ print length, $0 }' | sort -rn | cut -d' ' -f2-)

MAIN="$APP/Contents/MacOS/WebAuditMac"
echo "==> Main executable + app wrapper…"
codesign --force --options runtime --timestamp \
  --entitlements "$ENTITLEMENTS" --sign "$SIGN_ID" "$MAIN"
codesign --force --options runtime --timestamp \
  --entitlements "$ENTITLEMENTS" --sign "$SIGN_ID" "$APP"

echo "==> Verifying signature…"
codesign --verify --deep --strict --verbose=2 "$APP"
echo "OK: signed $APP"
