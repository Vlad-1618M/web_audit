# SwiftPM resource bundle for executable targets (Bundle.module).
# Source after paths.sh. Places bundle under Contents/Resources/ (notarization-safe).

stage_spm_resource_bundle() {
  local app="$1"
  local app_root="${2:-$APP_ROOT}"
  local bundle_name="WebAuditMac_WebAuditMac.bundle"
  local dest_dir="$app/Contents/Resources"

  [[ -d "$app/Contents" ]] || {
    echo "error: not a .app bundle: $app" >&2
    return 1
  }

  local resource_bundle=""
  while IFS= read -r candidate; do
    resource_bundle="$candidate"
    break
  done < <(find "$app_root/.build" -path "*/release/${bundle_name}" -type d 2>/dev/null)

  if [[ -z "$resource_bundle" || ! -d "$resource_bundle" ]]; then
    echo "error: missing ${bundle_name} under ${app_root}/.build (run swift build -c release first)" >&2
    return 1
  fi

  mkdir -p "$dest_dir"
  rm -rf "$app/${bundle_name}" "$dest_dir/${bundle_name}"
  cp -R "$resource_bundle" "$dest_dir/"
  echo "OK: staged ${bundle_name} → Contents/Resources/ (from ${resource_bundle})"
}
