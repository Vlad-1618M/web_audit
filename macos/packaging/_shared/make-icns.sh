#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "$ROOT/paths.sh"

RES="$APP_ROOT/Sources/WebAuditMac/Resources"
OUT="${1:-$APP_ROOT/build/AppIcon.icns}"
RENDER="$ROOT/render-macos-iconset.py"
ICONSET="$(mktemp -d)/AppIcon.iconset"
RAW_PNG="$APP_ROOT/build/icon-raw.png"
MASTER_PNG="$APP_ROOT/build/webaudit.png"

[[ -f "$RENDER" ]] || { echo "error: missing $RENDER" >&2; exit 1; }

resolve_icon_source() {
  local candidates=(
    "$RES/webaudit_pro_icon.svg"
    "$RES/webaudit.png"
    "$RES/alpha_version_webaudit_app_logo_removed.png"
    "$REPO_ROOT/png/webaudit.png"
  )
  local path
  for path in "${candidates[@]}"; do
    if [[ -f "$path" ]]; then
      printf '%s' "$path"
      return 0
    fi
  done
  echo "error: no app icon source (expected webaudit_pro_icon.svg or webaudit.png under $RES)" >&2
  return 1
}

rasterize_to_png() {
  local src="$1" dest="$2" size="${3:-1024}"
  mkdir -p "$(dirname "$dest")"

  case "${src##*.}" in
    svg|SVG)
      if [[ "$(uname -s)" != "Darwin" ]]; then
        echo "error: SVG icon source requires macOS qlmanage to rasterize: $src" >&2
        return 1
      fi
      local work thumb
      work="$(mktemp -d)"
      qlmanage -t -s "$size" -o "$work" "$src" >/dev/null 2>&1
      thumb="$work/$(basename "$src").png"
      [[ -f "$thumb" ]] || {
        echo "error: qlmanage failed to rasterize $src" >&2
        rm -rf "$work"
        return 1
      }
      cp "$thumb" "$dest"
      rm -rf "$work"
      ;;
    png|PNG|jpg|JPEG|webp|WEBP)
      cp "$src" "$dest"
      ;;
    *)
      echo "error: unsupported icon source type: $src" >&2
      return 1
      ;;
  esac
}

SRC="$(resolve_icon_source)"
echo "==> App icon source: $SRC"

mkdir -p "$(dirname "$OUT")"
mkdir -p "$ICONSET"

rasterize_to_png "$SRC" "$RAW_PNG" 1024

ICON_PY=python3
if ! python3 -c "import PIL" 2>/dev/null; then
  echo "==> Pillow not found; using temp venv for squircle icon rendering…"
  ICON_VENV="$(mktemp -d)/icon-venv"
  python3 -m venv "$ICON_VENV"
  "$ICON_VENV/bin/pip" install --quiet Pillow
  ICON_PY="$ICON_VENV/bin/python"
fi

if ! "$ICON_PY" "$RENDER" "$RAW_PNG" "$ICONSET" "$MASTER_PNG"; then
  echo "error: render-macos-iconset.py failed" >&2
  exit 1
fi

iconutil -c icns "$ICONSET" -o "$OUT"

# In-app footer logo (AppBrand) and repo marketing copy — squircle-masked, no white corners.
cp "$MASTER_PNG" "$RES/webaudit.png"
cp "$MASTER_PNG" "$REPO_ROOT/png/webaudit.png"

echo "OK: $OUT"
echo "OK: $MASTER_PNG (squircle master synced to Resources/ and png/)"
