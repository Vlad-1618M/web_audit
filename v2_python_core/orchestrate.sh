#!/usr/bin/env bash
# Web Audit v2 — local CI orchestrator (pytest, Docker WP fixture, webaudit Pro image).
#
# Usage:
#   ./orchestrate.sh --all
#   ./orchestrate.sh --job pytest
#   ./orchestrate.sh --job wp-up --wp-profile good
#   ./orchestrate.sh --job wp-integration --wp-profile mid
#   ./orchestrate.sh --job docker-build
#   ./orchestrate.sh --list
#
# Python resolution order: .venv → python3.12 → python3 → Docker webaudit:local (pytest via container)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
PYTEST_REPORTS="$SCRIPT_DIR/scripts/pytest_reports.sh"
DOCKER_DIR="$PROJECT_ROOT/docker"
COMPOSE_FILE="$DOCKER_DIR/docker-compose.yml"
VENV_DIR="${WEBAUDIT_VENV:-$PROJECT_ROOT/.venv}"
WP_PORT="${WP_PORT:-8080}"
WP_PROFILE="${WEBAUDIT_WP_PROFILE:-${WP_PROFILE:-mid}}"
WEBAUDIT_IMAGE="${WEBAUDIT_IMAGE:-webaudit:local}"
WEBAUDIT_WP_TEST_URL="${WEBAUDIT_WP_TEST_URL:-http://127.0.0.1:${WP_PORT}}"

# ── colors ────────────────────────────────────────────────────────────────────
if [[ -t 1 ]] && command -v tput >/dev/null 2>&1; then
  _n="$(tput sgr0 2>/dev/null || true)"
  RED="$(tput setaf 1 2>/dev/null || true)"
  GREEN="$(tput setaf 2 2>/dev/null || true)"
  YELLOW="$(tput setaf 3 2>/dev/null || true)"
  BLUE="$(tput setaf 4 2>/dev/null || true)"
  MAGENTA="$(tput setaf 5 2>/dev/null || true)"
  CYAN="$(tput setaf 6 2>/dev/null || true)"
  BOLD="$(tput bold 2>/dev/null || true)"
  DIM="$(tput dim 2>/dev/null || true)"
  NC="$_n"
else
  RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'
  BLUE=$'\033[0;34m'; MAGENTA=$'\033[0;35m'; CYAN=$'\033[0;36m'
  BOLD=$'\033[1m'; DIM=$'\033[2m'; NC=$'\033[0m'
fi

title() { printf '\n%b\n' "${BOLD}${BLUE}$*${NC}"; }
hr()    { printf '%b\n' "${DIM}────────────────────────────────────────────────────────${NC}"; }

# Help example: dim comment line + colored command on the next line.
help_ex() {
  local desc="$1"
  shift
  printf '  %b# %s%b\n' "$DIM" "$desc" "$NC"
  printf '  %b\n' "$*"
}

OB="${BOLD}./orchestrate.sh${NC}"

job_banner() {
  printf '\n%b\n' "${BOLD}${BLUE}JOB →${NC} ${CYAN}$1${NC}"
  printf '%b\n' "${DIM}$2${NC}"
  printf '%b\n' "${DIM}────────────────────────────────────────────────────────${NC}"
}

ok()   { printf '%b\n' "${GREEN}✔${NC} $*"; }
warn() { printf '%b\n' "${YELLOW}⚠${NC} $*"; }
err()  { printf '%b\n' "${RED}✖${NC} $*" >&2; }

confirm() {
  local prompt="${1:-Continue?}"
  if (( ASSUME_YES )); then
    return 0
  fi
  local answer lower
  printf '%b' "${YELLOW}?${NC} ${prompt} ${DIM}[y/N]${NC} "
  read -r answer
  lower="$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')"
  [[ "$lower" == "y" || "$lower" == "yes" ]]
}

ghcr_resolve_target() {
  GHCR_PUSH_OWNER="${GHCR_OWNER:-}"
  if [[ -z "$GHCR_PUSH_OWNER" ]]; then
    GHCR_PUSH_OWNER="$(git -C "$PROJECT_ROOT" remote get-url origin 2>/dev/null | sed -n 's/.*github\.com[:/]\([^/]*\).*/\1/p' | tr -d '\r')"
  fi
  GHCR_PUSH_OWNER="$(printf '%s' "$GHCR_PUSH_OWNER" | tr '[:upper:]' '[:lower:]')"
  GHCR_PUSH_VERSION="$(grep '__version__' "$PROJECT_ROOT/webaudit/__version__.py" | sed 's/.*"\(.*\)".*/\1/')"
  if [[ -n "$GHCR_PUSH_OWNER" ]]; then
    GHCR_PUSH_REMOTE="ghcr.io/${GHCR_PUSH_OWNER}/webaudit"
  else
    GHCR_PUSH_REMOTE=""
  fi
}

confirm_ghcr_push() {
  ghcr_resolve_target
  if [[ -z "$GHCR_PUSH_REMOTE" ]]; then
    err "Set GHCR_OWNER (GitHub username/org) or run from a git repo with github.com origin"
    return 1
  fi

  if (( ASSUME_YES )); then
    warn "Skipping GHCR push prompts (--yes) — pushing to ${GHCR_PUSH_REMOTE}"
    return 0
  fi

  printf '\n'
  warn "docker-push-ghcr uploads ${WEBAUDIT_IMAGE} to GitHub Container Registry (GHCR)."
  printf '%b\n' "${DIM}  Tags: ${GHCR_PUSH_REMOTE}:${GHCR_PUSH_VERSION} and :latest${NC}"
  if ! confirm "Push this image to GHCR now?"; then
    ok "Push cancelled — GitHub was not updated."
    return 1
  fi

  printf '\n'
  printf '%b\n' "${BOLD}${YELLOW}Public image — please confirm again${NC}"
  printf '%b\n' "  ${GHCR_PUSH_REMOTE} is (or will become) a ${BOLD}public${NC} package on GitHub."
  printf '%b\n' "  Anyone on the internet can pull it, e.g.:"
  printf '%b\n' "${DIM}    docker pull ${GHCR_PUSH_REMOTE}:latest${NC}"
  printf '%b\n' "  Existing :latest and :${GHCR_PUSH_VERSION} tags on GHCR will be ${BOLD}overwritten${NC}."
  printf '%b\n' "  Use this only when you intend to publish a release — not for every local test build."
  printf '\n'
  if ! confirm "Are you sure you want to publish to GHCR?"; then
    ok "Push cancelled at safety prompt — no images uploaded."
    return 1
  fi
  return 0
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    err "Required command not found: $1"
    return 1
  fi
}

have_docker() {
  command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1
}

compose() {
  need_cmd docker
  export WEBAUDIT_WP_PROFILE="$WP_PROFILE"
  export WP_PROFILE="$WP_PROFILE"
  export WP_PORT="$WP_PORT"
  export WEBAUDIT_IMAGE="$WEBAUDIT_IMAGE"
  docker compose -f "$COMPOSE_FILE" "$@"
}

resolve_python() {
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    echo "$VENV_DIR/bin/python"
    return 0
  fi
  if command -v python3.12 >/dev/null 2>&1; then
    command -v python3.12
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  return 1
}

ensure_python_env() {
  local py
  if py="$(resolve_python)"; then
    ok "Using Python: $py ($("$py" --version 2>&1))"
    if ! "$py" -c "import pytest" 2>/dev/null; then
      warn "pytest not installed — run ./dev-venv.sh setup or: pip install -e '.[dev]'"
      return 1
    fi
    return 0
  fi
  if have_docker && docker image inspect "$WEBAUDIT_IMAGE" >/dev/null 2>&1; then
    warn "No local Python env — will run pytest inside Docker image $WEBAUDIT_IMAGE"
    return 0
  fi
  err "No Python (.venv / python3) and no Docker image $WEBAUDIT_IMAGE"
  err "Fix: ./dev-venv.sh setup   OR   ./orchestrate.sh --job docker-build"
  return 1
}

run_pytest_local() {
  local report_path="$1"
  local py
  py="$(resolve_python)"
  local -a html_args=()
  if "$py" -c "import pytest_html" 2>/dev/null; then
    html_args=(--html="$report_path" --self-contained-html)
  else
    warn "pytest-html not installed — no consolidated report (pip install -e '.[dev]')"
  fi
  "$py" -m pytest tests/unit \
    -v -s -x \
    --tb=short \
    -ra \
    --cov=webaudit \
    --cov-report=term-missing \
    --cov-report=html:"$PROJECT_ROOT/htmlcov" \
    --cov-report=xml:"$PROJECT_ROOT/coverage.xml" \
    "${html_args[@]}"
}

run_pytest_docker() {
  local report_path="$1"
  need_cmd docker
  docker run --rm \
    -v "$PROJECT_ROOT:/src" \
    -w /src \
    python:3.12-slim-bookworm \
    bash -ec "pip install -q -U pip && pip install -q -e '.[dev]' && python -m pytest tests/unit -v -s -x --tb=short -ra --cov=webaudit --cov-report=term-missing --cov-report=html:htmlcov --html='${report_path}' --self-contained-html"
}

job_pytest() {
  job_banner "pytest (unit)" "Expanded output: -v -s -x -ra + coverage (htmlcov/) + dated HTML report (pytest_reports/)"
  cd "$PROJECT_ROOT"
  local report_path rc=0
  report_path="$("$PYTEST_REPORTS" new-path)"
  if resolve_python >/dev/null 2>&1; then
    run_pytest_local "$report_path" || rc=$?
  else
    run_pytest_docker "$report_path" || rc=$?
  fi
  if [[ -f "$report_path" ]]; then
    ok "Saved pytest report: $(basename "$report_path")"
  fi
  if (( SKIP_REPORT_PROMPT )); then
    WEBAUDIT_SKIP_PYTEST_OPEN=1 "$PYTEST_REPORTS" prompt "$report_path" || true
  else
    "$PYTEST_REPORTS" prompt "$report_path" || true
  fi
  if (( rc == 0 )); then
    ok "Unit tests passed"
  else
    err "Unit tests failed (exit $rc)"
    return "$rc"
  fi
}

job_integration() {
  job_banner "pytest (integration / WordPress fixture)" "Requires WP stack — URL: $WEBAUDIT_WP_TEST_URL profile: $WP_PROFILE"
  cd "$PROJECT_ROOT"
  export WEBAUDIT_WP_TEST_URL
  export WEBAUDIT_WP_PROFILE="$WP_PROFILE"
  local py
  py="$(resolve_python)" || { err "integration tests need local Python with dev deps"; return 1; }
  "$py" -m pytest tests/integration -v -s -ra --tb=short -m integration
  ok "Integration tests passed"
}

job_wp_up() {
  job_banner "wp-up" "Start MariaDB + WordPress on http://localhost:${WP_PORT} (profile: ${WP_PROFILE})"
  need_cmd docker
  compose up -d wp-db wordpress
  ok "Waiting for WordPress health…"
  compose run --rm wp-init
  ok "WordPress fixture ready — scan: webaudit scan ${WEBAUDIT_WP_TEST_URL} -v"
  ok "Or: WEBAUDIT_WP_TEST_URL=${WEBAUDIT_WP_TEST_URL} ./orchestrate.sh --job integration"
}

job_wp_down() {
  job_banner "wp-down" "Stop WordPress test stack and remove containers"
  compose down --remove-orphans
  ok "WordPress stack stopped"
}

job_wp_reset() {
  job_banner "wp-reset" "Remove WordPress volumes (fresh DB + uploads)"
  compose down -v --remove-orphans
  ok "Volumes removed — run --job wp-up to recreate"
}

job_docker_build() {
  job_banner "docker-build" "Build webaudit Pro image → ${WEBAUDIT_IMAGE}"
  need_cmd docker
  docker build -f "$DOCKER_DIR/webaudit/Dockerfile" -t "$WEBAUDIT_IMAGE" "$PROJECT_ROOT"
  ok "Built $WEBAUDIT_IMAGE"
  docker run --rm "$WEBAUDIT_IMAGE" --help >/dev/null
  ok "Smoke: webaudit --help OK"
}

job_docker_push_ghcr() {
  job_banner "docker-push-ghcr" "Tag and push ${WEBAUDIT_IMAGE} to GitHub Container Registry"
  need_cmd docker

  if ! confirm_ghcr_push; then
    return 0
  fi

  docker image inspect "$WEBAUDIT_IMAGE" >/dev/null 2>&1 || job_docker_build

  local remote="$GHCR_PUSH_REMOTE"
  local version="$GHCR_PUSH_VERSION"
  local owner="$GHCR_PUSH_OWNER"

  if ! grep -q "ghcr.io" "$HOME/.docker/config.json" 2>/dev/null; then
    warn "Not logged in to ghcr.io — run one of:"
    printf '  %sgh auth login%s\n' "$DIM" "$NC"
    printf '  %sgh auth token | docker login ghcr.io -u %s --password-stdin%s\n' "$DIM" "$owner" "$NC"
    return 1
  fi

  docker tag "$WEBAUDIT_IMAGE" "${remote}:${version}"
  docker tag "$WEBAUDIT_IMAGE" "${remote}:latest"
  docker push "${remote}:${version}"
  docker push "${remote}:latest"
  ok "Pushed ${remote}:${version} and :latest"
  ok "Pull: docker pull ${remote}:${version}"
}

job_docker_scan_wp() {
  job_banner "docker-scan-wp" "Run webaudit from container against WordPress on Docker network"
  need_cmd docker
  docker image inspect "$WEBAUDIT_IMAGE" >/dev/null 2>&1 || job_docker_build
  compose --profile pro run --rm --no-deps webaudit scan "http://wordpress" -v --open none
  ok "Scan from webaudit container completed"
}

job_docker_scan_host() {
  job_banner "docker-scan-host" "Run webaudit from container (host network target URL required)"
  local url="${1:-$WEBAUDIT_WP_TEST_URL}"
  need_cmd docker
  docker run --rm --network webaudit-test-net \
    -v "$PROJECT_ROOT/audit_logs:/work/audit_logs" \
    "$WEBAUDIT_IMAGE" scan "$url" -v --open none
}

list_jobs() {
  title "Available jobs"
  printf '%b\n' "${DIM}(use ${NC}${YELLOW}--job NAME${NC}${DIM} or ${NC}${YELLOW}--all${NC}${DIM})${NC}"
  hr
  printf '  %bpytest%b            Unit tests first — always recommended (default in --all)\n' "$CYAN" "$NC"
  printf '  %bintegration%b       Integration tests vs local WP fixture\n' "$CYAN" "$NC"
  printf '  %bwp-up%b             Start WordPress + init (profile: %s)\n' "$CYAN" "$NC" "$WP_PROFILE"
  printf '  %bwp-down%b           Stop WP stack\n' "$CYAN" "$NC"
  printf '  %bwp-reset%b          Stop WP + delete volumes\n' "$CYAN" "$NC"
  printf '  %bdocker-build%b      Build webaudit Pro image (%s)\n' "$CYAN" "$NC" "$WEBAUDIT_IMAGE"
  printf '  %bdocker-push-ghcr%b  Push %s to ghcr.io %b(double y/N confirm — public image)%b\n' \
    "$CYAN" "$NC" "$WEBAUDIT_IMAGE" "$DIM" "$NC"
  printf '  %bdocker-scan-wp%b    Scan http://wordpress from webaudit container\n' "$CYAN" "$NC"
  printf '  %bwp-integration%b    wp-up + integration + wp-down (use %s--keep-wp%s to skip teardown)\n' \
    "$CYAN" "$NC" "$YELLOW" "$NC"
  hr
  printf '%b\n' "${BOLD}${MAGENTA}Profiles${NC}  ${GREEN}weak${NC} | ${GREEN}mid${NC} | ${GREEN}good${NC}  ${DIM}(aliases: minimal, ok, strong)${NC}"
  hr
  printf '%b\n' "${BOLD}${MAGENTA}Environment${NC}"
  printf '  %bWP_PORT%b                 Host port %b(default %s)%b\n' "$YELLOW" "$NC" "$DIM" "$WP_PORT" "$NC"
  printf '  %bWEBAUDIT_WP_TEST_URL%b    Integration target %b(default %s)%b\n' \
    "$YELLOW" "$NC" "$DIM" "$WEBAUDIT_WP_TEST_URL" "$NC"
  printf '  %bWEBAUDIT_WP_PROFILE%b     weak | mid | good\n' "$YELLOW" "$NC"
  printf '  %bWEBAUDIT_IMAGE%b          Docker tag %b(default %s)%b\n' \
    "$YELLOW" "$NC" "$DIM" "$WEBAUDIT_IMAGE" "$NC"
  printf '  %bGHCR_OWNER%b              GitHub user/org for docker-push-ghcr\n' "$YELLOW" "$NC"
  hr
  printf '%b\n' "${DIM}Full guide:${NC} ${CYAN}docs/docker_ci.md${NC}"
  printf '%b\n' "${DIM}Pytest reports:${NC} ${CYAN}./scripts/pytest_reports.sh help${NC}"
  printf '\n'
}

usage() {
  local pr="${YELLOW}--wp-profile${NC}"
  local kp="${YELLOW}--keep-wp${NC}"
  local nr="${YELLOW}--no-report-prompt${NC}"
  local job="${YELLOW}--job${NC}"
  local yes="${YELLOW}--yes${NC}"

  title "Web Audit v2 — orchestrate.sh"
  hr
  printf '%b\n' "${BOLD}Usage${NC}"
  printf '  %s %b--all%b [%b--wp-profile%b %bPROFILE%b] [%b--keep-wp%b] [%b--no-report-prompt%b]\n' \
    "$(basename "$0")" "$YELLOW" "$NC" "$YELLOW" "$GREEN" "$NC" "$YELLOW" "$NC" "$YELLOW" "$NC"
  printf '  %s %b--pytest-only%b [%b--no-report-prompt%b]\n' \
    "$(basename "$0")" "$YELLOW" "$NC" "$YELLOW" "$NC"
  printf '  %s %b--job%b %bNAME%b [%b--wp-profile%b %bPROFILE%b] [%b--keep-wp%b] [%b--yes%b]  %b…repeat --job for a chain%b\n' \
    "$(basename "$0")" "$YELLOW" "$NC" "$CYAN" "$NC" "$YELLOW" "$GREEN" "$NC" \
    "$YELLOW" "$NC" "$YELLOW" "$NC" "$DIM" "$NC"
  printf '  %s %b--list%b          List jobs, profiles, and environment variables\n' \
    "$(basename "$0")" "$YELLOW" "$NC"
  printf '  %s %b-h%b | %b--help%b | %b--h%b\n' \
    "$(basename "$0")" "$YELLOW" "$NC" "$YELLOW" "$NC" "$YELLOW" "$NC"
  hr
  printf '%b\n' "${BOLD}Options${NC}"
  printf '  %b--wp-profile%b %bweak%b | %bmid%b | %bgood%b   WordPress fixture hardening %b(default: %s)%b\n' \
    "$YELLOW" "$NC" "$GREEN" "$NC" "$GREEN" "$NC" "$GREEN" "$NC" "$DIM" "$WP_PROFILE" "$NC"
  printf '  %b--keep-wp%b              Leave WP stack running after %bwp-integration%b / %b--all%b\n' \
    "$YELLOW" "$NC" "$CYAN" "$NC" "$YELLOW" "$NC"
  printf '  %b--no-report-prompt%b     Skip “open pytest report?” prompt (CI / scripts)\n' "$YELLOW" "$NC"
  printf '  %b-y%b, %b--yes%b              Skip GHCR double-confirm (%bdocker-push-ghcr%b only)\n' \
    "$YELLOW" "$NC" "$YELLOW" "$NC" "$CYAN" "$NC"
  hr
  printf '%b\n' "${BOLD}${MAGENTA}Jobs${NC}  ${DIM}(names for ${NC}${YELLOW}--job${NC}${DIM})${NC}"
  printf '  %bpytest%b              Unit tests + coverage + dated HTML report\n' "$CYAN" "$NC"
  printf '  %bintegration%b         Integration tests (WP fixture must be up)\n' "$CYAN" "$NC"
  printf '  %bwp-up%b                Start MariaDB + WordPress + init\n' "$CYAN" "$NC"
  printf '  %bwp-down%b              Stop WP containers\n' "$CYAN" "$NC"
  printf '  %bwp-reset%b             Stop WP and delete volumes (fresh DB)\n' "$CYAN" "$NC"
  printf '  %bwp-integration%b      wp-up → integration → wp-down\n' "$CYAN" "$NC"
  printf '  %bdocker-build%b         Build %s image locally\n' "$CYAN" "$NC" "$WEBAUDIT_IMAGE"
  printf '  %bdocker-push-ghcr%b     Publish image to GitHub Container Registry\n' "$CYAN" "$NC"
  printf '  %bdocker-scan-wp%b       Scan http://wordpress from webaudit container\n' "$CYAN" "$NC"
  printf '  %bdocker-scan-host%b      Scan a host URL from webaudit container\n' "$CYAN" "$NC"
  hr
  printf '%b\n' "${BOLD}Examples${NC}  ${DIM}(# = what it does · command on next line)${NC}"
  printf '\n'
  printf '%b\n' "${BOLD}${BLUE}Help & discovery${NC}"
  help_ex "Show this help" \
    "${OB} ${YELLOW}-h${NC}"
  help_ex "Same as -h" \
    "${OB} ${YELLOW}--help${NC}    ${OB} ${YELLOW}--h${NC}"
  help_ex "Job catalog + env vars" \
    "${OB} ${YELLOW}--list${NC}"
  printf '\n'
  printf '%b\n' "${BOLD}${BLUE}Pytest (unit)${NC}"
  help_ex "Unit tests, coverage (htmlcov/), dated HTML report; asks to open report" \
    "${OB} ${YELLOW}--pytest-only${NC}"
  help_ex "Pytest without browser prompt — for CI or scripts" \
    "${OB} ${YELLOW}--pytest-only${NC} ${nr}"
  help_ex "Same skip-prompt via environment" \
    "${DIM}WEBAUDIT_SKIP_PYTEST_OPEN=1${NC} ${OB} ${YELLOW}--pytest-only${NC}"
  help_ex "Unit tests as an explicit job (same as --pytest-only)" \
    "${OB} ${job} ${CYAN}pytest${NC}"
  help_ex "List / open archived pytest HTML reports" \
    "${BOLD}./scripts/pytest_reports.sh${NC} ${YELLOW}list${NC}"
  help_ex "Open newest report by index" \
    "${BOLD}./scripts/pytest_reports.sh${NC} ${YELLOW}open${NC} ${GREEN}0${NC}"
  printf '\n'
  printf '%b\n' "${BOLD}${BLUE}Full local pipeline${NC}"
  help_ex "pytest → docker-build → wp-up → integration → wp-down" \
    "${OB} ${YELLOW}--all${NC}"
  help_ex "Full pipeline with strong WordPress fixture" \
    "${OB} ${YELLOW}--all${NC} ${pr} ${GREEN}good${NC}"
  help_ex "Full pipeline; keep WP running for manual scans afterward" \
    "${OB} ${YELLOW}--all${NC} ${kp}"
  help_ex "Full pipeline, good profile, keep WP, no report browser prompt" \
    "${OB} ${YELLOW}--all${NC} ${pr} ${GREEN}good${NC} ${kp} ${nr}"
  printf '\n'
  printf '%b\n' "${BOLD}${BLUE}WordPress fixture${NC}"
  help_ex "Start WP on localhost:${WP_PORT} (default profile: mid)" \
    "${OB} ${job} ${CYAN}wp-up${NC}"
  help_ex "Weak / minimal hardening fixture" \
    "${OB} ${job} ${CYAN}wp-up${NC} ${pr} ${GREEN}weak${NC}"
  help_ex "Strong hardening fixture" \
    "${OB} ${job} ${CYAN}wp-up${NC} ${pr} ${GREEN}good${NC}"
  help_ex "Profile via environment (same as --wp-profile)" \
    "${DIM}WEBAUDIT_WP_PROFILE=${NC}${GREEN}good${NC} ${OB} ${job} ${CYAN}wp-up${NC}"
  help_ex "Custom host port" \
    "${DIM}WP_PORT=${NC}${GREEN}9090${NC} ${OB} ${job} ${CYAN}wp-up${NC}"
  help_ex "Stop WP containers" \
    "${OB} ${job} ${CYAN}wp-down${NC}"
  help_ex "Stop WP and wipe volumes (fresh database)" \
    "${OB} ${job} ${CYAN}wp-reset${NC}"
  help_ex "End-to-end: start WP, run integration tests, tear down" \
    "${OB} ${job} ${CYAN}wp-integration${NC}"
  help_ex "Integration with good profile; leave stack up" \
    "${OB} ${job} ${CYAN}wp-integration${NC} ${pr} ${GREEN}good${NC} ${kp}"
  help_ex "Integration tests only (WP must already be running)" \
    "${OB} ${job} ${CYAN}integration${NC}"
  help_ex "Custom integration target URL" \
    "${DIM}WEBAUDIT_WP_TEST_URL=${NC}${GREEN}http://127.0.0.1:8080${NC} ${OB} ${job} ${CYAN}integration${NC}"
  printf '\n'
  printf '%b\n' "${BOLD}${BLUE}Docker — webaudit image${NC}"
  help_ex "Build local Pro image tag (${WEBAUDIT_IMAGE})" \
    "${OB} ${job} ${CYAN}docker-build${NC}"
  help_ex "Custom image tag" \
    "${DIM}WEBAUDIT_IMAGE=${NC}${GREEN}webaudit:dev${NC} ${OB} ${job} ${CYAN}docker-build${NC}"
  help_ex "Publish to GHCR — double y/N confirm (public image)" \
    "${OB} ${job} ${CYAN}docker-push-ghcr${NC}"
  help_ex "Publish without prompts (use with care)" \
    "${OB} ${job} ${CYAN}docker-push-ghcr${NC} ${yes}"
  help_ex "Scan WP on Docker network from webaudit container" \
    "${OB} ${job} ${CYAN}docker-scan-wp${NC}"
  help_ex "Scan host URL from container on webaudit-test-net" \
    "${OB} ${job} ${CYAN}docker-scan-host${NC}"
  help_ex "Run webaudit CLI directly from built image" \
    "${DIM}docker run --rm ${NC}${GREEN}${WEBAUDIT_IMAGE}${NC} ${DIM}scan https://example.com --open none${NC}"
  printf '\n'
  printf '%b\n' "${BOLD}${BLUE}Chained jobs${NC}  ${DIM}(multiple ${NC}${YELLOW}--job${NC}${DIM} in one invocation)${NC}"
  help_ex "Build image then start WP" \
    "${OB} ${job} ${CYAN}docker-build${NC} ${job} ${CYAN}wp-up${NC}"
  help_ex "Pytest then build (quick pre-commit check)" \
    "${OB} ${job} ${CYAN}pytest${NC} ${job} ${CYAN}docker-build${NC}"
  help_ex "Reset WP, bring up fresh, run integration" \
    "${OB} ${job} ${CYAN}wp-reset${NC} ${job} ${CYAN}wp-up${NC} ${job} ${CYAN}integration${NC}"
  hr
  printf '%b\n' "${BOLD}${YELLOW}Note${NC}  ${CYAN}docker-build${NC} is local only. ${CYAN}docker-push-ghcr${NC} asks twice before uploading."
  printf '%b\n' "${DIM}See also:${NC} ${CYAN}./orchestrate.sh --list${NC}  ·  ${CYAN}docs/docker_ci.md${NC}  ·  ${CYAN}./scripts/pytest_reports.sh help${NC}"
  printf '\n'
}

run_all() {
  local keep_wp=0
  [[ "${1:-}" == "--keep-wp" ]] && keep_wp=1
  ensure_python_env || true
  job_pytest
  if have_docker; then
    job_docker_build
    job_wp_up
    job_integration || { err "Integration failed"; exit 1; }
    if (( keep_wp == 0 )); then
      job_wp_down
    else
      warn "Keeping WP stack running (--keep-wp)"
    fi
  else
    warn "Docker not available — skipping WP fixture + integration + image build"
  fi
  ok "All jobs completed"
}

# ── main ──────────────────────────────────────────────────────────────────────
JOBS=()
RUN_ALL=0
PYTEST_ONLY=0
KEEP_WP=0
ASSUME_YES=0
SKIP_REPORT_PROMPT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all) RUN_ALL=1; shift ;;
    --pytest-only) PYTEST_ONLY=1; shift ;;
    --job) JOBS+=("${2:?--job requires name}"); shift 2 ;;
    --wp-profile) WP_PROFILE="$2"; WEBAUDIT_WP_PROFILE="$2"; shift 2 ;;
    --keep-wp) KEEP_WP=1; shift ;;
    --no-report-prompt) SKIP_REPORT_PROMPT=1; shift ;;
    -y|--yes) ASSUME_YES=1; shift ;;
    --list) list_jobs; exit 0 ;;
    -h|--help|--h) usage; exit 0 ;;
    *) err "Unknown option: $1"; usage; exit 1 ;;
  esac
done

if (( RUN_ALL )); then
  if (( KEEP_WP )); then
    run_all --keep-wp
  else
    run_all
  fi
  exit 0
fi

if (( PYTEST_ONLY )); then
  ensure_python_env
  job_pytest
  exit 0
fi

if ((${#JOBS[@]} == 0)); then
  usage
  exit 1
fi

for j in "${JOBS[@]}"; do
  case "$j" in
    pytest) ensure_python_env; job_pytest ;;
    integration) ensure_python_env; job_integration ;;
    wp-up) job_wp_up ;;
    wp-down) job_wp_down ;;
    wp-reset) job_wp_reset ;;
    docker-build) job_docker_build ;;
    docker-push-ghcr) job_docker_push_ghcr ;;
    docker-scan-wp) job_docker_scan_wp ;;
    docker-scan-host) job_docker_scan_host "${2:-}" ;;
    wp-integration)
      job_wp_up
      ensure_python_env
      job_integration
      if (( KEEP_WP == 0 )); then job_wp_down; fi
      ;;
    *) err "Unknown job: $j"; list_jobs; exit 1 ;;
  esac
done
