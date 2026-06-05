#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "$ROOT/paths.sh"

cd "$APP_ROOT"
echo "Building WebAuditMac (release)…"
swift build -c release

BIN="$APP_ROOT/.build/release/WebAuditMac"
[[ -x "$BIN" ]] || { echo "error: expected $BIN" >&2; exit 1; }
echo "OK: $BIN"
