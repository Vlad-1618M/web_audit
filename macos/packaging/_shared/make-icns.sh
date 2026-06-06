#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "$ROOT/paths.sh"

SRC="$APP_ROOT/Sources/WebAuditMac/Resources/webaudit.png"
OUT="${1:-$APP_ROOT/build/AppIcon.icns}"
RENDER="$ROOT/render-macos-iconset.py"
ICONSET="$(mktemp -d)/AppIcon.iconset"

[[ -f "$SRC" ]] || { echo "error: missing $SRC" >&2; exit 1; }
[[ -f "$RENDER" ]] || { echo "error: missing $RENDER" >&2; exit 1; }

mkdir -p "$(dirname "$OUT")"
mkdir -p "$ICONSET"

if ! python3 -c "import PIL" 2>/dev/null; then
  echo "==> Installing Pillow for macOS squircle icon rendering…"
  python3 -m pip install --quiet Pillow
fi

if ! python3 "$RENDER" "$SRC" "$ICONSET"; then
  echo "error: render-macos-iconset.py failed (install Pillow: pip install Pillow)" >&2
  exit 1
fi

iconutil -c icns "$ICONSET" -o "$OUT"
echo "OK: $OUT"
