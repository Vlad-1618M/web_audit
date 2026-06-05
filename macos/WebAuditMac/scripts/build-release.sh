#!/usr/bin/env bash
# Release build of WebAuditMac executable.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Building WebAuditMac (release)…"
swift build -c release

BIN="$ROOT/.build/release/WebAuditMac"
if [[ ! -x "$BIN" ]]; then
  echo "error: expected $BIN" >&2
  exit 1
fi

echo "OK: $BIN"
