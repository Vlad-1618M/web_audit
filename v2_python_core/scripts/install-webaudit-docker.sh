#!/usr/bin/env bash
# One-time install: pull GHCR image, install webaudit-docker wrapper to ~/.local/bin, ensure PATH.
#
# Pull-only (no git clone):
#   curl -fsSL https://raw.githubusercontent.com/Vlad-1618M/web_audit/v.tools_main/v2_python_core/scripts/install-webaudit-docker.sh | bash
#
# From a git clone:
#   ./scripts/install-webaudit-docker.sh
#
# Wrapper source order: sibling webaudit-docker.sh in repo → GitHub raw → extract from image (fallback).
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${WEBAUDIT_DOCKER_IMAGE:-ghcr.io/vlad-1618m/webaudit:latest}"
GIT_RAW_BASE="${WEBAUDIT_GIT_RAW:-https://raw.githubusercontent.com/Vlad-1618M/web_audit/v.tools_main/v2_python_core/scripts}"
BIN_DIR="${HOME}/.local/bin"
WRAPPER="${BIN_DIR}/webaudit-docker"
WRAPPER_SRC="${SCRIPT_DIR}/webaudit-docker.sh"
PATH_EXPORT='export PATH="$HOME/.local/bin:$PATH"'
PATH_MARKER='# added by install-webaudit-docker.sh (Web Audit)'

SKIP_PULL=0
SKIP_PATH=0
FROM_IMAGE=0

usage() {
  cat <<EOF
install-webaudit-docker.sh — install webaudit-docker host wrapper + PATH

Usage:
  $(basename "$0") [options]

Options:
  --no-pull     Skip docker pull (image already local)
  --no-path     Do not modify shell rc; print export instructions only
  --from-image  Install wrapper from the Docker image only (may lag behind GitHub)
  -h, --help    Show this help

After install:
  webaudit-docker scan https://example.com
  webaudit-docker --output-dir documents scan https://example.com -v --open html
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-pull) SKIP_PULL=1 ;;
    --no-path) SKIP_PATH=1 ;;
    --from-image) FROM_IMAGE=1 ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

command -v docker >/dev/null 2>&1 || {
  echo "error: docker not found — install Docker Desktop first." >&2
  echo "  https://docs.docker.com/desktop/" >&2
  exit 1
}

mkdir -p "$BIN_DIR"

if [[ "$SKIP_PULL" -eq 0 ]]; then
  echo "==> Pulling ${IMAGE}"
  docker pull "$IMAGE"
else
  echo "==> Skipping docker pull (--no-pull)"
fi

install_wrapper() {
  echo "==> Installing ${WRAPPER}"

  if [[ "$FROM_IMAGE" -eq 1 ]]; then
    docker run --rm --entrypoint cat "$IMAGE" \
      /usr/share/webaudit/webaudit-docker.sh >"$WRAPPER"
    echo "OK: wrapper from image ${IMAGE}"
    chmod +x "$WRAPPER"
    return 0
  fi

  if [[ -f "$WRAPPER_SRC" ]]; then
    cp "$WRAPPER_SRC" "$WRAPPER"
    echo "OK: wrapper from repo ${WRAPPER_SRC}"
    chmod +x "$WRAPPER"
    return 0
  fi

  if curl -fsSL "${GIT_RAW_BASE}/webaudit-docker.sh" -o "$WRAPPER"; then
    echo "OK: wrapper from ${GIT_RAW_BASE}/webaudit-docker.sh"
    chmod +x "$WRAPPER"
    return 0
  fi

  echo "WARN: could not fetch wrapper from GitHub — falling back to image extract" >&2
  docker run --rm --entrypoint cat "$IMAGE" \
    /usr/share/webaudit/webaudit-docker.sh >"$WRAPPER"
  echo "OK: wrapper from image ${IMAGE} (re-run install after git push for latest wrapper)"
  chmod +x "$WRAPPER"
}

install_wrapper

shell_rc() {
  if [[ -n "${ZSH_VERSION:-}" ]] || [[ "${SHELL:-}" == *zsh* ]]; then
    echo "${HOME}/.zshrc"
  elif [[ -f "${HOME}/.bashrc" ]]; then
    echo "${HOME}/.bashrc"
  else
    echo "${HOME}/.bash_profile"
  fi
}

warn_path_manual() {
  echo ""
  echo "If webaudit-docker is not found, run:"
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
}

ensure_path() {
  if [[ ":${PATH}:" == *":${BIN_DIR}:"* ]]; then
    echo "OK: ${BIN_DIR} is already on PATH in this shell"
    return 0
  fi

  if [[ "$SKIP_PATH" -eq 1 ]]; then
    warn_path_manual
    return 0
  fi

  local rc
  rc="$(shell_rc)"
  touch "$rc"

  if grep -qF '.local/bin' "$rc" 2>/dev/null || grep -qF "$PATH_MARKER" "$rc" 2>/dev/null; then
    echo "OK: ${rc} already mentions ~/.local/bin (not modified)"
    warn_path_manual
    return 0
  fi

  {
    echo ""
    echo "$PATH_MARKER"
    echo "$PATH_EXPORT"
  } >>"$rc"
  echo "OK: appended PATH line to ${rc}"
  echo "    Run: source ${rc}   (or open a new terminal)"
}

ensure_path

echo ""
echo "==> Verify"
if command -v webaudit-docker >/dev/null 2>&1; then
  echo "OK: $(command -v webaudit-docker)"
  webaudit-docker --help | head -n 3 || true
else
  warn_path_manual
  echo "  then: webaudit-docker --help"
fi

echo ""
echo "==> Example scan"
echo "  webaudit-docker scan https://example.com"
