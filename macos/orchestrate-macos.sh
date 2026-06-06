#!/usr/bin/env bash
# macOS deliverables — dev external-engine vs public bundled installer.
set -euo pipefail

MACOS_ROOT="$(cd "$(dirname "$0")" && pwd)"
DEV="$MACOS_ROOT/packaging/dev-external-engine"
PUBLIC="$MACOS_ROOT/packaging/public-installer"
SHARED="$MACOS_ROOT/packaging/_shared"
APP="$MACOS_ROOT/WebAuditMac"
INSTALLERS="$MACOS_ROOT/installers"

ensure_packaging_scripts() {
  local dir="$1"
  local label="$2"
  if [[ ! -d "$dir" ]]; then
    echo "error: missing $label directory: $dir" >&2
    echo "  Pull latest macos/packaging/ from the repo." >&2
    exit 1
  fi
  local count
  count="$(find "$dir" -maxdepth 1 -name '*.sh' -type f 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "$count" == "0" ]]; then
    echo "error: no .sh scripts in $dir" >&2
    exit 1
  fi
  find "$dir" "$SHARED" -name '*.sh' -type f -print0 2>/dev/null \
    | xargs -0 chmod +x 2>/dev/null || true
  [[ -x "$SHARED/vendor/create-dmg" ]] || chmod +x "$SHARED/vendor/create-dmg" 2>/dev/null || true
}

usage() {
  cat <<EOF
Web Audit — macOS orchestrator

Usage:
  $(basename "$0") dev-dmg           Build dev DMG (Docker/venv engine on host)
  $(basename "$0") dev-smoke         Build + install smoke (dev DMG)
  $(basename "$0") dev-run           Launch Swift app for repo dev (run-dev.sh)
  $(basename "$0") public-dmg        Build public DMG (bundled Python engine)
  $(basename "$0") public-smoke      Build + install smoke (public DMG)
  $(basename "$0") public-engine     Bundle Python engine only (no DMG)
  $(basename "$0") swift-test        Run WebAuditMac unit tests (needs full Xcode)
  $(basename "$0") clean-installers    Remove built .dmg files (keeps README)
  $(basename "$0") -h | --help

Paths:
  Swift source     $APP
  Built DMGs       $INSTALLERS  (gitignored — safe to delete)
  Dev packaging    $DEV
  Public packaging $PUBLIC
EOF
}

run_swift_test() {
  cd "$APP"
  if ! xcrun --find xctest >/dev/null 2>&1; then
    echo "SKIP: XCTest not available (Command Line Tools only)." >&2
    echo "  Unit tests run on GitHub Actions (macos-14 + Xcode)." >&2
    echo "  Local tests: install Xcode, then:" >&2
    echo "    sudo xcode-select -s /Applications/Xcode.app/Contents/Developer" >&2
    exit 0
  fi
  swift test
}

cmd="${1:-}"
case "$cmd" in
  dev-dmg)
    ensure_packaging_scripts "$DEV" "dev-external-engine"
    "$DEV/build-dmg.sh"
    ;;
  dev-smoke)
    ensure_packaging_scripts "$DEV" "dev-external-engine"
    "$DEV/smoke-install.sh"
    ;;
  dev-run)
    "$APP/run-dev.sh"
    ;;
  public-dmg)
    ensure_packaging_scripts "$PUBLIC" "public-installer"
    "$PUBLIC/build-dmg.sh"
    ;;
  public-smoke)
    ensure_packaging_scripts "$PUBLIC" "public-installer"
    "$PUBLIC/smoke-install.sh"
    ;;
  public-engine)
    ensure_packaging_scripts "$PUBLIC" "public-installer"
    "$PUBLIC/bundle-engine.sh"
    ;;
  swift-test)
    run_swift_test
    ;;
  clean-installers)
    mkdir -p "$INSTALLERS"
    find "$INSTALLERS" -maxdepth 1 -name '*.dmg' -type f -delete 2>/dev/null || true
    echo "OK: removed .dmg files from $INSTALLERS"
    ;;
  -h|--help|"")
    usage
    [[ -n "$cmd" ]] || exit 0
    ;;
  *)
    echo "error: unknown command: $cmd" >&2
    usage >&2
    exit 1
    ;;
esac
