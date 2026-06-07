#!/usr/bin/env bash
# Sign DMG (optional), submit to notary service, staple.
set -euo pipefail

NOTARY_PROFILE="${NOTARY_PROFILE:-webaudit-notarize}"

usage() {
  cat <<EOF
Usage: $(basename "$0") <path/to/WebAudit-*.dmg>

Environment:
  SIGN_ID          Developer ID Application (auto-detected if unset; used to codesign DMG)
  NOTARY_PROFILE   Keychain profile (default: webaudit-notarize)
  SKIP_DMG_SIGN=1  Skip codesign on DMG before submit
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
  [[ -n "$line" ]] || fail "no Developer ID Application identity"
  echo "$line" | sed -E 's/^[[:space:]]*[0-9]+\)[[:space:]]+[0-9A-Fa-f]+[[:space:]]+"([^"]+)"/\1/'
}

[[ $# -ge 1 ]] || { usage >&2; exit 1; }
DMG="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
[[ -f "$DMG" ]] || fail "DMG not found: $DMG"

if [[ "${SKIP_DMG_SIGN:-}" != "1" ]]; then
  SIGN_ID="$(resolve_sign_id)"
  echo "==> Codesigning DMG…"
  codesign --force --sign "$SIGN_ID" "$DMG"
fi

echo "==> Submitting DMG (profile: $NOTARY_PROFILE)…"
SUBMIT_OUT="$(mktemp)"
xcrun notarytool submit "$DMG" --keychain-profile "$NOTARY_PROFILE" --wait 2>&1 | tee "$SUBMIT_OUT"

SUBMISSION_ID="$(grep -E '^[[:space:]]*id:' "$SUBMIT_OUT" | tail -1 | awk '{print $2}')"
STATUS="$(grep -E '^[[:space:]]*status:' "$SUBMIT_OUT" | tail -1 | awk '{print $2}')"

if [[ "$STATUS" != "Accepted" ]]; then
  echo "FAIL: DMG notarization: ${STATUS:-unknown}" >&2
  [[ -n "$SUBMISSION_ID" ]] && xcrun notarytool log "$SUBMISSION_ID" --keychain-profile "$NOTARY_PROFILE" >&2 || true
  rm -f "$SUBMIT_OUT"
  exit 1
fi

rm -f "$SUBMIT_OUT"
echo "==> Stapling DMG…"
xcrun stapler staple "$DMG"
xcrun stapler validate "$DMG"
echo "OK: notarized + stapled $DMG"
