#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "$ROOT/paths.sh"

SRC="$APP_ROOT/Sources/WebAuditMac/Resources/webaudit.png"
OUT="${1:-$APP_ROOT/build/AppIcon.icns}"
ICONSET="$(mktemp -d)/AppIcon.iconset"

[[ -f "$SRC" ]] || { echo "error: missing $SRC" >&2; exit 1; }

mkdir -p "$(dirname "$OUT")"
mkdir -p "$ICONSET"

make_icon() {
  local size="$1"
  local name="$2"
  sips -z "$size" "$size" "$SRC" --out "$ICONSET/$name" >/dev/null
}

make_icon 16  icon_16x16.png
make_icon 32  icon_16x16@2x.png
make_icon 32  icon_32x32.png
make_icon 64  icon_32x32@2x.png
make_icon 128 icon_128x128.png
make_icon 256 icon_128x128@2x.png
make_icon 256 icon_256x256.png
make_icon 512 icon_256x256@2x.png
make_icon 512 icon_512x512.png
make_icon 1024 icon_512x512@2x.png

iconutil -c icns "$ICONSET" -o "$OUT"
echo "OK: $OUT"
