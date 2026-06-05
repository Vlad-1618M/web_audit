#!/usr/bin/env bash
# Launch WebAuditMac without tying keyboard focus to Terminal.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -x .build/debug/WebAuditMac ]]; then
  echo "Building WebAuditMac…"
  swift build
fi

export WEBAUDIT_REPO="${WEBAUDIT_REPO:-$(cd "$ROOT/../.." && pwd)}"
export WEBAUDIT_DOCKER_SCRIPT="${WEBAUDIT_DOCKER_SCRIPT:-$WEBAUDIT_REPO/v2_python_core/scripts/webaudit-docker.sh}"
export WEBAUDIT_ENGINE_POLICY="${WEBAUDIT_ENGINE_POLICY:-external}"
export WEBAUDIT_VENV="${WEBAUDIT_VENV:-$WEBAUDIT_REPO/v2_python_core/.venv}"

# Background + disown: shell keeps your exports, Terminal prompt returns, GUI gets keyboard when clicked.
.build/debug/WebAuditMac &
disown

echo "Web Audit launched."
echo "  Click the app window, then type or ⌘V to paste."
echo "  Quit with ⌘Q (not Ctrl+C)."
