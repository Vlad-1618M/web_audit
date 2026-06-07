#!/usr/bin/env bash
# Sign Web Audit.app for Developer ID + notarization (Engine, Playwright, main binary).
set -euo pipefail

SHARED="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "$SHARED/paths.sh"

ENTITLEMENTS="${ENTITLEMENTS:-$SHARED/../public-installer/entitlements.plist}"

usage() {
  cat <<EOF
Usage: $(basename "$0") <path/to/Web Audit.app>

Environment:
  SIGN_ID              Developer ID Application name or SHA-1 hash (auto-detected if unset)
  ENTITLEMENTS         Path to entitlements.plist (default: public-installer/entitlements.plist)

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

# Paths with spaces: length TAB path
sort_paths_deepest() {
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    printf '%s\t%s\n' "${#path}" "$path"
  done | sort -t $'\t' -k1,1nr | cut -f2-
}

sign_macho() {
  local target="$1"
  local sign_id="$2"
  codesign --force --options runtime --timestamp --sign "$sign_id" "$target"
}

sign_macho_files_deepest() {
  local root="$1"
  local label="${2:-$root}"
  local -a files=()
  while IFS= read -r -d '' f; do
    is_macho "$f" || continue
    files+=("$f")
  done < <(find "$root" -type f -print0)

  [[ ${#files[@]} -gt 0 ]] || return 0
  echo "==> Mach-O in $label (${#files[@]} files, deepest first)…"
  printf '%s\n' "${files[@]}" | sort_paths_deepest | while read -r f; do
    sign_macho "$f" "$SIGN_ID"
  done
}

sign_code_bundles_deepest() {
  local root="$1"
  local label="${2:-$root}"
  local -a bundles=()
  while IFS= read -r bundle; do
    [[ -n "$bundle" ]] || continue
    bundles+=("$bundle")
  done < <(find "$root" \( -name '*.app' -o -name '*.framework' -o -name '*.xpc' \) -type d -print)

  [[ ${#bundles[@]} -gt 0 ]] || return 0
  echo "==> Code bundles in $label (${#bundles[@]} bundles, deepest first)…"
  printf '%s\n' "${bundles[@]}" | sort_paths_deepest | while read -r bundle; do
    sign_macho "$bundle" "$SIGN_ID"
  done
}

sign_tree() {
  local root="$1"
  local label="$2"
  [[ -d "$root" ]] || return 0
  sign_macho_files_deepest "$root" "$label"
  sign_code_bundles_deepest "$root" "$label"
}

[[ $# -ge 1 ]] || { usage >&2; exit 1; }
APP="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
[[ -f "$APP/Contents/MacOS/WebAuditMac" ]] || fail "not a Web Audit app bundle: $APP"
[[ -f "$ENTITLEMENTS" ]] || fail "missing entitlements: $ENTITLEMENTS"

SIGN_ID="$(resolve_sign_id)"
echo "==> Signing: $APP"
echo "    identity: $SIGN_ID"

ENGINE="$APP/Contents/Resources/Engine"
PY="$ENGINE/python"
PW="$ENGINE/playwright-browsers"

sign_tree "$PY" "Engine/python"
[[ -d "$ENGINE/bin" ]] && sign_macho_files_deepest "$ENGINE/bin" "Engine/bin"
sign_tree "$PW" "playwright-browsers"

MAIN="$APP/Contents/MacOS/WebAuditMac"
echo "==> Main executable + app wrapper…"
codesign --force --options runtime --timestamp \
  --entitlements "$ENTITLEMENTS" --sign "$SIGN_ID" "$MAIN"
codesign --force --options runtime --timestamp \
  --entitlements "$ENTITLEMENTS" --sign "$SIGN_ID" "$APP"

echo "==> Verifying Playwright Chrome (strict)…"
CHROME_APP="$(find "$PW" -name 'Google Chrome for Testing.app' -type d 2>/dev/null | head -1 || true)"
if [[ -n "$CHROME_APP" ]]; then
  codesign --verify --deep --strict --verbose=2 "$CHROME_APP"
fi

echo "==> Verifying full app signature…"
codesign --verify --deep --strict --verbose=2 "$APP"
echo "OK: signed $APP"
