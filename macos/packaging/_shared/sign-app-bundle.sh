#!/usr/bin/env bash
# Sign Web Audit.app for Developer ID + notarization (Engine, Playwright, main binary).
set -euo pipefail

SHARED="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "$SHARED/paths.sh"

ENTITLEMENTS="${ENTITLEMENTS:-$SHARED/../public-installer/entitlements.plist}"
ENGINE_JIT_ENTITLEMENTS="${ENGINE_JIT_ENTITLEMENTS:-$SHARED/../public-installer/engine-jit-entitlements.plist}"

usage() {
  cat <<EOF
Usage: $(basename "$0") <path/to/Web Audit.app>

Environment:
  SIGN_ID              Developer ID Application name or SHA-1 hash (auto-detected if unset)
  ENTITLEMENTS         Path to entitlements.plist (default: public-installer/entitlements.plist)
  ENGINE_JIT_ENTITLEMENTS  JIT entitlements for Playwright node + Chromium (engine-jit-entitlements.plist)

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
  local entitlements="${3:-}"
  if [[ -n "$entitlements" ]]; then
    codesign --force --options runtime --timestamp \
      --entitlements "$entitlements" --sign "$sign_id" "$target"
  else
    codesign --force --options runtime --timestamp --sign "$sign_id" "$target"
  fi
}

sign_macho_files_deepest() {
  local root="$1"
  local label="${2:-$root}"
  local entitlements="${3:-}"
  local -a files=()
  while IFS= read -r -d '' f; do
    is_macho "$f" || continue
    files+=("$f")
  done < <(find "$root" -type f -print0)

  [[ ${#files[@]} -gt 0 ]] || return 0
  echo "==> Mach-O in $label (${#files[@]} files, deepest first)…"
  printf '%s\n' "${files[@]}" | sort_paths_deepest | while read -r f; do
    sign_macho "$f" "$SIGN_ID" "$entitlements"
  done
}

sign_code_bundles_deepest() {
  local root="$1"
  local label="${2:-$root}"
  local entitlements="${3:-}"
  local -a bundles=()
  while IFS= read -r bundle; do
    [[ -n "$bundle" ]] || continue
    bundles+=("$bundle")
  done < <(find "$root" \( -name '*.app' -o -name '*.framework' -o -name '*.xpc' \) -type d -print)

  [[ ${#bundles[@]} -gt 0 ]] || return 0
  echo "==> Code bundles in $label (${#bundles[@]} bundles, deepest first)…"
  printf '%s\n' "${bundles[@]}" | sort_paths_deepest | while read -r bundle; do
    sign_macho "$bundle" "$SIGN_ID" "$entitlements"
  done
}

sign_tree() {
  local root="$1"
  local label="$2"
  local entitlements="${3:-}"
  [[ -d "$root" ]] || return 0
  sign_macho_files_deepest "$root" "$label" "$entitlements"
  sign_code_bundles_deepest "$root" "$label" "$entitlements"
}

sign_macho_files_deepest_entitled() {
  sign_macho_files_deepest "$1" "$2" "$ENGINE_JIT_ENTITLEMENTS"
}

sign_code_bundles_deepest_entitled() {
  sign_code_bundles_deepest "$1" "$2" "$ENGINE_JIT_ENTITLEMENTS"
}

# Playwright's bundled node driver and Chromium need JIT under hardened runtime.
sign_playwright_jit_helpers() {
  local py_root="$1"
  local pw_root="$2"
  [[ -f "$ENGINE_JIT_ENTITLEMENTS" ]] || fail "missing engine JIT entitlements: $ENGINE_JIT_ENTITLEMENTS"

  echo "==> Playwright JIT helpers (node driver + python + Chromium)…"
  local -a jit_files=()
  while IFS= read -r -d '' f; do
    is_macho "$f" || continue
    jit_files+=("$f")
  done < <(find "$py_root" \( -path '*/playwright/driver/node' -o -path '*/bin/python3*' \) -type f -print0 2>/dev/null)

  if [[ ${#jit_files[@]} -gt 0 ]]; then
    printf '%s\n' "${jit_files[@]}" | sort_paths_deepest | while read -r f; do
      sign_macho "$f" "$SIGN_ID" "$ENGINE_JIT_ENTITLEMENTS"
    done
  fi

  [[ -d "$pw_root" ]] || return 0
  sign_macho_files_deepest_entitled "$pw_root" "playwright-browsers (JIT)"
  sign_code_bundles_deepest_entitled "$pw_root" "playwright-browsers (JIT)"
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
sign_playwright_jit_helpers "$PY" "$PW"

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
