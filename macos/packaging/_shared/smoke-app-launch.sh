# Smoke: SPM resource bundle present and GUI binary stays alive briefly.
# Source after paths.sh.

SPM_RESOURCE_BUNDLE_NAME="WebAuditMac_WebAuditMac.bundle"

assert_spm_resource_bundle() {
  local app="$1"
  local bundle="$app/${SPM_RESOURCE_BUNDLE_NAME}"
  [[ -d "$bundle" ]] || {
    echo "FAIL: missing SPM resource bundle: $bundle" >&2
    return 1
  }
  echo "OK: ${SPM_RESOURCE_BUNDLE_NAME} present"
}

smoke_app_launch() {
  local app="$1"
  local bin="$app/Contents/MacOS/WebAuditMac"
  local wait_secs="${2:-3}"

  [[ -x "$bin" ]] || {
    echo "FAIL: binary not executable: $bin" >&2
    return 1
  }

  assert_spm_resource_bundle "$app" || return 1

  # Headless CI: app should not fatal on Bundle.module during startup.
  "$bin" &
  local pid=$!
  sleep "$wait_secs"
  if ! kill -0 "$pid" 2>/dev/null; then
    wait "$pid" 2>/dev/null || true
    echo "FAIL: app exited within ${wait_secs}s (launch crash? run: $bin)" >&2
    return 1
  fi
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  echo "OK: app binary still running after ${wait_secs}s"
}
