#!/usr/bin/env bash
# Bundle relocatable Python + webaudit into build/engine/ for Contents/Resources/Engine/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../_shared/paths.sh
source "$ROOT/../_shared/paths.sh"

ENGINE_OUT="$ROOT/build/engine"
CACHE_DIR="$ROOT/build/cache"
PBS_TAG="${PBS_TAG:-20241016}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12.7}"

arch="$(uname -m)"
case "$arch" in
  arm64) PBS_ARCH="aarch64-apple-darwin" ;;
  x86_64) PBS_ARCH="x86_64-apple-darwin" ;;
  *)
    echo "error: unsupported Mac arch: $arch" >&2
    exit 1
    ;;
esac

TAR_NAME="cpython-${PYTHON_VERSION}+${PBS_TAG}-${PBS_ARCH}-install_only.tar.gz"
TAR_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/${TAR_NAME}"
TAR_CACHE="$CACHE_DIR/$TAR_NAME"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "error: missing command: $1" >&2; exit 1; }
}

need_cmd curl
need_cmd tar

[[ -f "$PYTHON_CORE/pyproject.toml" ]] || {
  echo "error: missing $PYTHON_CORE/pyproject.toml" >&2
  exit 1
}

echo "==> Bundling webaudit engine (${PBS_ARCH}, Python ${PYTHON_VERSION})"
rm -rf "$ENGINE_OUT"
mkdir -p "$ENGINE_OUT/bin" "$CACHE_DIR"

if [[ ! -f "$TAR_CACHE" ]]; then
  echo "==> Downloading python-build-standalone (${TAR_NAME})…"
  curl -fsSL "$TAR_URL" -o "$TAR_CACHE"
fi

WORK="$(mktemp -d /tmp/webaudit-engine.XXXXXX)"
trap 'rm -rf "$WORK"' EXIT

tar -xzf "$TAR_CACHE" -C "$WORK"
[[ -x "$WORK/python/bin/python3" ]] || {
  echo "error: expected $WORK/python/bin/python3 after extract" >&2
  exit 1
}

PY="$WORK/python/bin/python3"
echo "==> Installing webaudit[js] from $PYTHON_CORE"
"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install "$PYTHON_CORE[js]" --no-cache-dir

cp -R "$WORK/python" "$ENGINE_OUT/python"

BROWSERS_DIR="$ENGINE_OUT/playwright-browsers"
mkdir -p "$BROWSERS_DIR"
echo "==> Installing Playwright Chromium into $BROWSERS_DIR"
export PLAYWRIGHT_BROWSERS_PATH="$BROWSERS_DIR"
"$ENGINE_OUT/python/bin/python3" -m playwright install chromium chromium-headless-shell

if ! "$ENGINE_OUT/python/bin/python3" -c "import playwright" >/dev/null 2>&1; then
  echo "error: playwright package not importable in bundled engine" >&2
  exit 1
fi
if [[ -z "$(find "$BROWSERS_DIR" -type f 2>/dev/null | head -1)" ]]; then
  echo "error: no Playwright browser binaries under $BROWSERS_DIR" >&2
  exit 1
fi

echo "==> Smoke: Playwright driver + Chromium launch"
export PLAYWRIGHT_BROWSERS_PATH="$BROWSERS_DIR"
if ! "$ENGINE_OUT/python/bin/python3" - <<'PY' >/dev/null 2>&1; then
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    browser.close()
PY
  echo "error: Playwright driver smoke test failed (sync_playwright / chromium.launch)" >&2
  exit 1
fi
echo "    Playwright driver OK"

cat > "$ENGINE_OUT/bin/webaudit" <<'WRAP'
#!/usr/bin/env bash
set -euo pipefail
ENGINE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ENGINE_ROOT/python/bin/python3"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$ENGINE_ROOT/playwright-browsers}"
case "${1:-}" in
  --version|-V)
    if VER="$("$PY" -c "import importlib.metadata as m; print(m.version('webaudit'))" 2>/dev/null)"; then
      echo "webaudit ${VER} (bundled engine)"
    else
      echo "webaudit (bundled engine, version unknown)"
    fi
    exit 0
    ;;
esac
exec "$PY" -m webaudit.cli.main "$@"
WRAP
chmod +x "$ENGINE_OUT/bin/webaudit"

if ! "$ENGINE_OUT/bin/webaudit" --help >/dev/null 2>&1; then
  echo "error: bundled webaudit --help failed" >&2
  exit 1
fi
if ! "$ENGINE_OUT/bin/webaudit" --version >/dev/null 2>&1; then
  echo "error: bundled webaudit --version failed" >&2
  exit 1
fi
echo "OK: $ENGINE_OUT"
ENGINE_VER="$(grep -E '^version = ' "$PYTHON_CORE/pyproject.toml" | head -1 | sed 's/.*"\(.*\)".*/\1/')"
echo "    engine: webaudit ${ENGINE_VER}"
du -sh "$ENGINE_OUT"
