#!/usr/bin/env bash
# Wrapper: run bump_versions.py from repo root.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 "$ROOT/release_manager/bump_versions.py" "$@"
