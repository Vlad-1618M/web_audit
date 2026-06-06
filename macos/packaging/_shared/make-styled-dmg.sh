#!/usr/bin/env bash
# Build a styled read-only DMG (background, icon layout, Applications drop link).
# Requires staged folder with .app and INSTALL.txt.
set -euo pipefail

SHARED="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "$SHARED/paths.sh"

LAYOUT_ENV="$SHARED/dmg-layout.env"
CREATE_DMG="$SHARED/vendor/create-dmg"
BACKGROUND="$SHARED/dmg-background.png"
ICON_FILE="${ICON_FILE:-}"

usage() {
  cat <<EOF
Usage: $(basename "$0") <dmg_output_path> <stage_folder> <volume_name>

Example:
  make-styled-dmg.sh "\$INSTALLERS_ROOT/WebAudit-0.1.0-alpha-macOS.dmg" "\$STAGE" "Web Audit"
EOF
}

fail() { echo "error: $*" >&2; exit 1; }

[[ $# -ge 3 ]] || { usage >&2; exit 1; }

DMG_OUT="$1"
STAGE="$2"
VOLNAME="$3"

[[ -f "$LAYOUT_ENV" ]] || fail "missing layout: $LAYOUT_ENV"
# shellcheck source=dmg-layout.env
source "$LAYOUT_ENV"

[[ -x "$CREATE_DMG" ]] || fail "missing create-dmg: $CREATE_DMG"
[[ -d "$SHARED/vendor/support" ]] || fail "missing create-dmg support/: $SHARED/vendor/support"
[[ -f "$BACKGROUND" ]] || fail "missing background: $BACKGROUND (run generate-dmg-background.py)"
[[ -d "$STAGE/${APP_NAME}.app" ]] || fail "missing app in stage: $STAGE/${APP_NAME}.app"
[[ -f "$STAGE/INSTALL.txt" ]] || fail "missing INSTALL.txt in stage"

mkdir -p "$(dirname "$DMG_OUT")"
rm -f "$DMG_OUT"

DMG_ARGS=(--volname "$VOLNAME")
if [[ -n "${ICON_FILE:-}" && -f "${ICON_FILE}" ]]; then
  DMG_ARGS+=(--volicon "$ICON_FILE")
fi

"$CREATE_DMG" \
  "${DMG_ARGS[@]}" \
  --background "$BACKGROUND" \
  --window-pos 120 100 \
  --window-size "$DMG_WIN_W" "$DMG_WIN_H" \
  --icon-size "$DMG_ICON_SIZE" \
  --text-size 12 \
  --icon "${APP_NAME}.app" "$DMG_APP_X" "$DMG_APP_Y" \
  --hide-extension "${APP_NAME}.app" \
  --app-drop-link "$DMG_APPS_X" "$DMG_APPS_Y" \
  --icon "INSTALL.txt" "$DMG_INSTALL_X" "$DMG_INSTALL_Y" \
  --hide-extension "INSTALL.txt" \
  --no-internet-enable \
  "$DMG_OUT" \
  "$STAGE"

echo "OK: $DMG_OUT"
du -h "$DMG_OUT"
