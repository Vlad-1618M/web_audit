# Copy launch-critical brand PNGs into Contents/Resources/ (never silent-fail).
# Usage: copy_brand_png_resources <path/to/App.app> <path/to/Sources/WebAuditMac/Resources>

copy_brand_png_resources() {
  local app="$1"
  local resources_src="$2"
  local dest="$app/Contents/Resources"

  [[ -d "$app/Contents" ]] || {
    echo "error: not a .app bundle: $app" >&2
    return 1
  }

  mkdir -p "$dest"
  for name in vtool-trademark webaudit; do
    local src="$resources_src/${name}.png"
    [[ -f "$src" ]] || {
      echo "error: missing brand PNG: $src" >&2
      return 1
    }
    cp "$src" "$dest/"
  done
  echo "OK: brand PNGs → Contents/Resources/"
}
