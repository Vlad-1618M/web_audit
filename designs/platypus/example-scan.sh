#!/usr/bin/env bash
# Example script for Platypus.app — Web Audit owner Mac app (prototype).
# Wrap this in Platypus: Script Type = Shell, Interface = Progress Bar + Text.
# Requires: webaudit-docker on PATH (from install script or ~/.local/bin).
#
# Platypus passes dropped text/URLs as $1; or prompt user if empty.

set -euo pipefail

URL="${1:-}"
OUTPUT="${HOME}/Documents/WebAudit"

if [[ -z "$URL" ]]; then
  URL="$(osascript -e 'text returned of (display dialog "Enter your website address:" default answer "https://" with title "Web Audit")')"
fi

URL="$(printf '%s' "$URL" | tr -d '\r\n' | xargs)"
if [[ ! "$URL" =~ ^https?:// ]]; then
  osascript -e 'display alert "Invalid address" message "Paste the full URL starting with https://" as warning'
  exit 1
fi

echo "Web Audit — scanning $URL"
echo "Reports → $OUTPUT"
echo ""

if ! command -v webaudit-docker >/dev/null 2>&1; then
  echo "ERROR: webaudit-docker not found."
  echo "Install once: see v2_python_core/docs/docker_ci.md (pull-only section)"
  exit 1
fi

webaudit-docker --output-dir "$OUTPUT" scan "$URL" -v --open none

RUN="$(ls -td "$OUTPUT"/*/ 2>/dev/null | head -1)"
REPORT="${RUN}report.html"

if [[ ! -f "$REPORT" ]]; then
  osascript -e 'display alert "Scan failed" message "No report was created. See log above." as critical'
  exit 1
fi

CHOICE="$(osascript -e "button returned of (display dialog \"Report ready at:\n$REPORT\" with title \"Web Audit\" buttons {\"Show in Finder\", \"Open in browser\", \"Done\"} default button \"Open in browser\")")"

case "$CHOICE" in
  "Open in browser") open "$REPORT" ;;
  "Show in Finder") open -R "$REPORT" ;;
esac

echo ""
echo "Powered by muzar.io · https://github.com/Vlad-1618M"
echo "© $(date +%Y) Vtools. All rights reserved."
