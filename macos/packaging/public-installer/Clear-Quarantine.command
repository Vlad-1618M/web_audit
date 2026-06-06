#!/bin/bash
# Double-click this file in the DMG — Terminal opens and clears macOS download quarantine
# on Web Audit.app after you drag it to Applications. Safe to run more than once.

set -euo pipefail

APP="/Applications/Web Audit.app"

echo ""
echo "Web Audit — clear download quarantine"
echo "======================================"
echo ""

if [[ ! -d "$APP" ]]; then
  echo "Web Audit is not in Applications yet."
  echo ""
  echo "Do this first:"
  echo "  1. Drag Web Audit.app from this disk image onto the Applications folder."
  echo "  2. Double-click Clear-Quarantine.command again."
  echo ""
  read -r -p "Press Return to close Terminal…" _
  exit 1
fi

xattr -cr "$APP"
echo "OK: cleared quarantine on Web Audit"
echo ""
echo "Next:"
echo "  1. Open Applications."
echo "  2. Double-click Web Audit."
echo ""
echo "If macOS still shows a security warning:"
echo "  • Right-click Web Audit → Open → click Open once."
echo "  • Or: System Settings → Privacy & Security → Open Anyway."
echo ""
read -r -p "Press Return to close Terminal…" _
