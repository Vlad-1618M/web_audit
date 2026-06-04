#!/usr/bin/env bash
# Web Audit v2 — pytest HTML report archive, list, and browser open helper.
#
# Standalone:
#   ./scripts/pytest_reports.sh help
#   ./scripts/pytest_reports.sh new-path
#   ./scripts/pytest_reports.sh list
#   ./scripts/pytest_reports.sh open 0
#   ./scripts/pytest_reports.sh prompt [/path/to/latest.html]
#
# Orchestrator calls `new-path` before pytest and `prompt` after pytest finishes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${WEBAUDIT_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
REPORTS_DIR="${WEBAUDIT_PYTEST_REPORTS_DIR:-$PROJECT_ROOT/pytest_reports}"
REPORT_PREFIX="webaudit_pytest_"
COVERAGE_INDEX="$PROJECT_ROOT/htmlcov/index.html"

# ── colors ────────────────────────────────────────────────────────────────────
if [[ -t 1 ]] && command -v tput >/dev/null 2>&1; then
  _n="$(tput sgr0 2>/dev/null || true)"
  GREEN="$(tput setaf 2 2>/dev/null || true)"
  YELLOW="$(tput setaf 3 2>/dev/null || true)"
  ORANGE="$(tput setaf 208 2>/dev/null || tput setaf 3 2>/dev/null || true)"
  BLUE="$(tput setaf 4 2>/dev/null || true)"
  CYAN="$(tput setaf 6 2>/dev/null || true)"
  RED="$(tput setaf 1 2>/dev/null || true)"
  BOLD="$(tput bold 2>/dev/null || true)"
  DIM="$(tput dim 2>/dev/null || true)"
  NC="$_n"
else
  GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'; ORANGE=$'\033[0;33m'
  RED=$'\033[0;31m'
  BLUE=$'\033[0;34m'; CYAN=$'\033[0;36m'
  BOLD=$'\033[1m'; DIM=$'\033[2m'; NC=$'\033[0m'
fi

title() { printf '\n%b\n' "${BOLD}${BLUE}$*${NC}"; }
ok()    { printf '%b\n' "${GREEN}✔${NC} $*"; }
warn()  { printf '%b\n' "${YELLOW}⚠${NC} $*"; }
err()   { printf '%b\n' "${RED}✖${NC} $*" >&2; }

confirm() {
  local prompt="${1:-Continue?}"
  if (( PYTEST_REPORTS_ASSUME_YES )); then
    return 0
  fi
  local answer lower
  printf '%b' "${YELLOW}?${NC} ${prompt} ${DIM}[y/N]${NC} "
  read -r answer
  lower="$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')"
  [[ "$lower" == "y" || "$lower" == "yes" ]]
}

pytest_reports_ensure_dir() {
  mkdir -p "$REPORTS_DIR"
}

pytest_reports_new_path() {
  pytest_reports_ensure_dir
  date +"${REPORTS_DIR}/${REPORT_PREFIX}%Y-%m-%d_%H%M%S.html"
}

# Populate REPORT_LIST (newest first). Returns count via stdout.
pytest_reports_collect() {
  REPORT_LIST=()
  local f
  pytest_reports_ensure_dir
  shopt -s nullglob
  local -a candidates=("$REPORTS_DIR"/${REPORT_PREFIX}*.html)
  shopt -u nullglob
  if ((${#candidates[@]} == 0)); then
    return 0
  fi
  while IFS= read -r f; do
    [[ -n "$f" ]] && REPORT_LIST+=("$f")
  done < <(printf '%s\n' "${candidates[@]}" | sort -r)
}

open_in_browser() {
  local target="$1"
  if [[ ! -f "$target" ]]; then
    err "File not found: $target"
    return 1
  fi
  if [[ "$(uname -s)" == "Darwin" ]]; then
    open "$target"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$target"
  elif command -v sensible-browser >/dev/null 2>&1; then
    sensible-browser "$target"
  else
    err "No browser opener found (macOS: open, Linux: xdg-open)"
    printf '%b\n' "${DIM}  $target${NC}"
    return 1
  fi
  ok "Opened $(basename "$target")"
}

pytest_reports_list() {
  local highlight="${1:-}"
  pytest_reports_collect
  local count="${#REPORT_LIST[@]}"
  if (( count == 0 )); then
    warn "No pytest HTML reports in ${REPORTS_DIR}/"
    printf '%b\n' "${DIM}  Run ./orchestrate.sh --pytest-only to generate one.${NC}"
    return 0
  fi

  title "Pytest reports (${count} saved)"
  printf '%b\n' "${DIM}Directory: ${REPORTS_DIR}/${NC}"
  hr() { printf '%b\n' "${DIM}────────────────────────────────────────────────────────${NC}"; }
  hr

  local i path base is_new color tag
  for i in "${!REPORT_LIST[@]}"; do
    path="${REPORT_LIST[$i]}"
    base="$(basename "$path")"
    is_new=0
    if [[ -n "$highlight" && "$path" == "$highlight" ]]; then
      is_new=1
    elif [[ -z "$highlight" && "$i" -eq 0 ]]; then
      is_new=1
    fi
    if (( is_new )); then
      color="$GREEN"
      tag=" ${BOLD}· latest${NC}"
    else
      color="$ORANGE"
      tag=""
    fi
    printf '  %b[%s]%b %b%s%b%b\n' "$CYAN" "$i" "$NC" "$color" "$base" "$NC" "$tag"
  done
  hr
  if [[ -f "$COVERAGE_INDEX" ]]; then
    printf '%b\n' "${DIM}Coverage (separate): ${COVERAGE_INDEX}${NC}"
  fi
  printf '\n'
}

pytest_reports_open_index() {
  local idx="${1:-0}"
  pytest_reports_collect
  local count="${#REPORT_LIST[@]}"
  if (( count == 0 )); then
    err "No reports to open"
    return 1
  fi
  if ! [[ "$idx" =~ ^[0-9]+$ ]] || (( idx < 0 || idx >= count )); then
    err "Invalid index: $idx (valid: 0–$((count - 1)))"
    return 1
  fi
  open_in_browser "${REPORT_LIST[$idx]}"
}

pytest_reports_show_paths() {
  local latest="${1:-}"
  if [[ -z "$latest" ]]; then
    pytest_reports_collect
    latest="${REPORT_LIST[0]:-}"
  fi
  if [[ -n "$latest" && -f "$latest" ]]; then
    ok "Pytest report: $latest"
  fi
  if [[ -f "$COVERAGE_INDEX" ]]; then
    ok "Coverage:      $COVERAGE_INDEX"
  fi
}

pytest_reports_prompt() {
  local newest="${1:-}"
  if [[ -n "$newest" && ! -f "$newest" ]]; then
    warn "Expected report not found: $newest"
    newest=""
  fi

  if (( PYTEST_REPORTS_SKIP_PROMPT )); then
    pytest_reports_show_paths "$newest"
    return 0
  fi

  if [[ ! -t 0 ]]; then
    pytest_reports_show_paths "$newest"
    return 0
  fi

  pytest_reports_list "$newest"

  pytest_reports_collect
  local count="${#REPORT_LIST[@]}"
  if (( count == 0 )); then
    return 0
  fi

  if ! confirm "Open pytest report in browser?"; then
    pytest_reports_show_paths "$newest"
    return 0
  fi

  local pick=0
  if (( count > 1 )); then
    local answer
    printf '%b' "${YELLOW}?${NC} Which report? ${DIM}[0–$((count - 1)), Enter = 0]${NC} "
    read -r answer
    if [[ -z "$answer" ]]; then
      pick=0
    elif [[ "$answer" =~ ^[0-9]+$ ]] && (( answer >= 0 && answer < count )); then
      pick="$answer"
    else
      warn "Invalid choice — using latest [0]"
      pick=0
    fi
  fi

  open_in_browser "${REPORT_LIST[$pick]}"
}

pytest_reports_help() {
  title "pytest_reports.sh — pytest HTML report manager"
  printf '%b\n' "${DIM}────────────────────────────────────────────────────────${NC}"
  printf '%b\n' "${BOLD}Usage${NC}"
  printf '  %s %bhelp%b\n' "$(basename "$0")" "$CYAN" "$NC"
  printf '  %s %bnew-path%b              Print dated path for the next pytest --html report\n' \
    "$(basename "$0")" "$CYAN" "$NC"
  printf '  %s %blist%b [%b--all%b]         List archived reports (newest = green, older = orange)\n' \
    "$(basename "$0")" "$CYAN" "$NC" "$CYAN" "$NC"
  printf '  %s %bopen%b %bINDEX%b             Open report by index (0 = newest)\n' \
    "$(basename "$0")" "$CYAN" "$NC" "$CYAN" "$NC"
  printf '  %s %bprompt%b [%bPATH%b]         Ask y/n to open; pick index if several exist\n' \
    "$(basename "$0")" "$CYAN" "$NC" "$CYAN" "$NC"
  printf '%b\n' "${DIM}────────────────────────────────────────────────────────${NC}"
  printf '%b\n' "${BOLD}Environment${NC}"
  printf '  %bWEBAUDIT_PROJECT_ROOT%b       Project root (default: parent of scripts/)\n' "$YELLOW" "$NC"
  printf '  %bWEBAUDIT_PYTEST_REPORTS_DIR%b  Output dir (default: pytest_reports/)\n' "$YELLOW" "$NC"
  printf '  %bWEBAUDIT_SKIP_PYTEST_OPEN%b    Skip interactive prompt (CI / scripts)\n' "$YELLOW" "$NC"
  printf '%b\n' "${DIM}────────────────────────────────────────────────────────${NC}"
  printf '%b\n' "${BOLD}Reports${NC}  ${REPORT_PREFIX}YYYY-MM-DD_HHMMSS.html  ${DIM}(self-contained pytest-html)${NC}"
  printf '%b\n' "${BOLD}Coverage${NC}  htmlcov/index.html  ${DIM}(separate — pytest-cov)${NC}"
  printf '\n'
}

# ── main ──────────────────────────────────────────────────────────────────────
PYTEST_REPORTS_SKIP_PROMPT=0
PYTEST_REPORTS_ASSUME_YES=0
REPORT_LIST=()

if [[ -n "${WEBAUDIT_SKIP_PYTEST_OPEN:-}" ]]; then
  PYTEST_REPORTS_SKIP_PROMPT=1
fi

cmd="${1:-help}"
shift || true

case "$cmd" in
  help|-h|--help)
    pytest_reports_help
    ;;
  new-path)
    pytest_reports_new_path
    ;;
  list)
    pytest_reports_list
    ;;
  open)
    pytest_reports_open_index "${1:-0}"
    ;;
  prompt)
    pytest_reports_prompt "${1:-}"
    ;;
  *)
    err "Unknown command: $cmd"
    pytest_reports_help
    exit 1
    ;;
esac
