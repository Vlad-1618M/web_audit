#!/usr/bin/env bash
# Build AppIcon.icns — delegates to packaging/_shared (squircle macOS icon).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/../packaging/_shared/make-icns.sh" "${1:-$ROOT/build/AppIcon.icns}"
