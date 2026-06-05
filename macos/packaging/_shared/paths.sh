# Shared paths for macOS packaging scripts (source with: . "$(dirname "$0")/../_shared/paths.sh")
PACKAGING_SHARED="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MACOS_ROOT="$(cd "$PACKAGING_SHARED/../.." && pwd)"
APP_ROOT="$MACOS_ROOT/WebAuditMac"
REPO_ROOT="$(cd "$MACOS_ROOT/.." && pwd)"
PYTHON_CORE="$REPO_ROOT/v2_python_core"
APP_NAME="Web Audit"
VERSION="$(tr -d '[:space:]' < "$APP_ROOT/VERSION")"
# All built .dmg files land here (gitignored). Safe to rm -rf and rebuild.
INSTALLERS_ROOT="$MACOS_ROOT/installers"
