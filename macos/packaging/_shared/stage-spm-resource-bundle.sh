# SwiftPM resource bundle for executable targets (Bundle.module).
# Source after paths.sh. Places WebAuditMac_WebAuditMac.bundle beside Contents/ in .app.

stage_spm_resource_bundle() {
  local app="$1"
  local app_root="${2:-$APP_ROOT}"
  local bundle_name="WebAuditMac_WebAuditMac.bundle"

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

  rm -rf "$app/${bundle_name}"
  cp -R "$resource_bundle" "$app/"
  echo "OK: staged ${bundle_name} from ${resource_bundle}"
}
