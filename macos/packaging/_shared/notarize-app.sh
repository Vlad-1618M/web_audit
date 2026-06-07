#!/usr/bin/env bash
# Zip .app, submit to Apple notary service, staple on success.
set -euo pipefail

SHARED="$(cd "$(dirname "$0")" && pwd)"
NOTARY_PROFILE="${NOTARY_PROFILE:-webaudit-notarize}"
ZIP_OUT="${ZIP_OUT:-/tmp/WebAudit-notarize.zip}"

usage() {
  cat <<EOF
Usage: $(basename "$0") <path/to/Web Audit.app>

Environment:
  NOTARY_PROFILE   Keychain credentials profile (default: webaudit-notarize)
  ZIP_OUT          Temp zip path (default: /tmp/WebAudit-notarize.zip)

On Invalid status, prints: xcrun notarytool log <id> --keychain-profile "$NOTARY_PROFILE"
EOF
}

fail() { echo "error: $*" >&2; exit 1; }

[[ $# -ge 1 ]] || { usage >&2; exit 1; }
APP="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
[[ -d "$APP/Contents" ]] || fail "not an app bundle: $APP"

echo "==> Zipping for notarization…"
rm -f "$ZIP_OUT"
ditto -c -k --keepParent "$APP" "$ZIP_OUT"
echo "    $ZIP_OUT ($(du -h "$ZIP_OUT" | awk '{print $1}'))"

echo "==> Submitting to Apple (profile: $NOTARY_PROFILE)…"
SUBMIT_OUT="$(mktemp)"
xcrun notarytool submit "$ZIP_OUT" --keychain-profile "$NOTARY_PROFILE" --wait 2>&1 | tee "$SUBMIT_OUT"

SUBMISSION_ID="$(grep -E '^[[:space:]]*id:' "$SUBMIT_OUT" | tail -1 | awk '{print $2}')"
STATUS="$(grep -E '^[[:space:]]*status:' "$SUBMIT_OUT" | tail -1 | awk '{print $2}')"

if [[ "$STATUS" != "Accepted" ]]; then
  echo "" >&2
  echo "FAIL: notarization status: ${STATUS:-unknown}" >&2
  if [[ -n "$SUBMISSION_ID" ]]; then
    echo "Log:" >&2
    xcrun notarytool log "$SUBMISSION_ID" --keychain-profile "$NOTARY_PROFILE" >&2 || true
    echo "" >&2
    echo "Retry log:" >&2
    echo "  xcrun notarytool log $SUBMISSION_ID --keychain-profile \"$NOTARY_PROFILE\"" >&2
  fi
  rm -f "$SUBMIT_OUT"
  exit 1
fi

rm -f "$SUBMIT_OUT"
echo "==> Stapling ticket to app…"
xcrun stapler staple "$APP"
xcrun stapler validate "$APP"
echo "OK: notarized + stapled $APP"
