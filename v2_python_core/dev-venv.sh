#!/usr/bin/env bash
# Web Audit v2 — local .venv setup / teardown helper (macOS + Linux).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="${WEBAUDIT_VENV:-$PROJECT_ROOT/.venv}"
REPO_ROOT="$(cd "$PROJECT_ROOT/.." && pwd)"

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
  RED=$'\033[0;31m'
  GREEN=$'\033[0;32m'
  YELLOW=$'\033[0;33m'
  BLUE=$'\033[0;34m'
  MAGENTA=$'\033[0;35m'
  CYAN=$'\033[0;36m'
  BOLD=$'\033[1m'
  DIM=$'\033[2m'
  NC=$'\033[0m'
fi

info()    { printf '%b\n' "${CYAN}▸${NC} $*"; }
ok()      { printf '%b\n' "${GREEN}✔${NC} $*"; }
warn()    { printf '%b\n' "${YELLOW}⚠${NC} $*"; }
err()     { printf '%b\n' "${RED}✖${NC} $*" >&2; }
title()   { printf '\n%b\n' "${BOLD}${BLUE}$*${NC}"; }
hr()      { printf '%b\n' "${DIM}────────────────────────────────────────────────────────${NC}"; }

confirm() {
  local prompt="${1:-Continue?}"
  local answer lower
  printf '%b' "${YELLOW}?${NC} ${prompt} [y/N] "
  read -r answer
  lower="$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')"
  [[ "$lower" == "y" || "$lower" == "yes" ]]
}

# ── age helpers ───────────────────────────────────────────────────────────────
_mtime_epoch() {
  local path="$1"
  if [[ "$(uname -s)" == "Darwin" ]]; then
    stat -f %m "$path" 2>/dev/null || echo 0
  else
    stat -c %Y "$path" 2>/dev/null || echo 0
  fi
}

_human_age() {
  local epoch="$1"
  local now diff
  now="$(date +%s)"
  diff=$((now - epoch))
  if (( diff < 0 )); then
    echo "just now"
  elif (( diff < 60 )); then
    echo "${diff}s ago"
  elif (( diff < 3600 )); then
    echo "$(( diff / 60 ))m ago"
  elif (( diff < 86400 )); then
    echo "$(( diff / 3600 ))h ago"
  elif (( diff < 604800 )); then
    echo "$(( diff / 86400 ))d ago"
  else
    echo "$(( diff / 604800 ))w ago"
  fi
}

_fmt_when() {
  local epoch="$1"
  if [[ "$(uname -s)" == "Darwin" ]]; then
    date -r "$epoch" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "unknown"
  else
    date -d "@$epoch" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "unknown"
  fi
}

_venv_python_version() {
  local py="$1/bin/python"
  if [[ -x "$py" ]]; then
    "$py" --version 2>&1 | tr -d '\n'
  else
    echo "no python binary"
  fi
}

_is_venv_dir() {
  local dir="$1"
  [[ -d "$dir" && ( -x "$dir/bin/python" || -x "$dir/Scripts/python.exe" ) ]]
}

# ── discovery ─────────────────────────────────────────────────────────────────
collect_venv_paths() {
  local -a paths=()
  local name candidate

  for name in .venv venv .virtualenv env; do
    candidate="$PROJECT_ROOT/$name"
    if _is_venv_dir "$candidate"; then
      paths+=("$candidate")
    fi
  done

  # Same repo, other common locations (e.g. root web_audit/.venv)
  for name in .venv venv; do
    candidate="$REPO_ROOT/$name"
    if _is_venv_dir "$candidate" && [[ "$candidate" != "$VENV_DIR" ]]; then
      local seen=0 p
      for p in "${paths[@]+"${paths[@]}"}"; do
        [[ "$p" == "$candidate" ]] && seen=1 && break
      done
      (( seen == 0 )) && paths+=("$candidate")
    fi
  done

  if ((${#paths[@]} > 0)); then
    printf '%s\n' "${paths[@]}"
  fi
}

show_existing_venvs() {
  title "Virtual environments found"
  local path epoch when age pyver marker found=0

  while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    found=1
    epoch="$(_mtime_epoch "$path")"
    when="$(_fmt_when "$epoch")"
    age="$(_human_age "$epoch")"
    pyver="$(_venv_python_version "$path")"
    marker=""
    [[ "$path" == "$VENV_DIR" ]] && marker="${GREEN} (this project default)${NC}"
    printf '  %b%s%b\n' "${BOLD}" "$path" "${NC}${marker}"
    printf '    %smodified:%s %s  %s(%s)%s  %s%s%s\n' \
      "$DIM" "$NC" "$when" "$DIM" "$age" "$NC" "$CYAN" "$pyver" "$NC"
  done < <(collect_venv_paths)

  if (( found == 0 )); then
    info "No local venv directories detected under:"
    printf '  %s\n' "$PROJECT_ROOT"
    printf '  %s\n' "$REPO_ROOT"
  fi
}

show_pyenv_state() {
  if ! command -v pyenv >/dev/null 2>&1; then
    info "pyenv: not installed (skipped)"
    return 0
  fi

  title "pyenv (system Python versions)"
  local line ver_dir epoch when age
  while IFS= read -r line; do
    printf '  %s\n' "$line"
  done < <(pyenv versions 2>/dev/null || true)

  if pyenv commands 2>/dev/null | grep -qx virtualenv; then
    title "pyenv virtualenvs"
    local name root
    while IFS= read -r name; do
      [[ -z "$name" ]] && continue
      root="$(pyenv prefix "$name" 2>/dev/null || true)"
      if [[ -n "$root" && -d "$root" ]]; then
        epoch="$(_mtime_epoch "$root")"
        when="$(_fmt_when "$epoch")"
        age="$(_human_age "$epoch")"
        printf '  %b%s%b  %smodified %s (%s)%s\n' \
          "${MAGENTA}" "$name" "${NC}" "$DIM" "$when" "$age" "$NC"
        printf '    %s%s%s\n' "$DIM" "$root" "$NC"
      else
        printf '  %b%s%b\n' "${MAGENTA}" "$name" "${NC}"
      fi
    done < <(pyenv virtualenvs --bare 2>/dev/null || true)
  fi
}

show_system_python() {
  title "System Python candidates"
  local cmd ver
  for cmd in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
      ver="$("$cmd" --version 2>&1)"
      printf '  %b%-12s%b %s\n' "$CYAN" "$cmd" "$NC" "$ver"
    fi
  done
}

prompt_cleanup_venvs() {
  local path count=0
  while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    count=$((count + 1))
  done < <(collect_venv_paths)

  (( count == 0 )) && return 0

  hr
  warn "Found ${count} virtual environment(s) on disk."
  if confirm "Remove ALL listed venvs before continuing?"; then
    while IFS= read -r path; do
      [[ -z "$path" ]] && continue
      rm -rf "$path"
      ok "Removed $path"
    done < <(collect_venv_paths)
  else
    info "Keeping existing venvs."
  fi
}

pick_python() {
  local cmd
  for cmd in python3.13 python3.12 python3.11 python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
      local minor
      minor="$("$cmd" -c 'import sys; print("%d.%d" % (sys.version_info.major, sys.version_info.minor))')"
      if awk -v v="$minor" 'BEGIN { split(v,a,"."); exit (a[1]+0 >= 3 && a[2]+0 >= 11) ? 0 : 1 }'; then
        echo "$cmd"
        return 0
      fi
    fi
  done
  return 1
}

do_refresh() {
  if ! _is_venv_dir "$VENV_DIR"; then
    warn "No venv at $VENV_DIR — run setup first."
    do_setup
    return
  fi
  title "Refresh — reuse existing .venv"
  info "Venv: $VENV_DIR ($(_venv_python_version "$VENV_DIR"))"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  python -m pip install -U pip wheel >/dev/null
  pip install -e "$PROJECT_ROOT[dev]"
  ok "Dependencies refreshed"
  print_usage_hint
}

do_activate_print() {
  if ! _is_venv_dir "$VENV_DIR"; then
    err "No venv at $VENV_DIR — run: ./dev-venv.sh setup"
    exit 1
  fi
  printf "source '%s/bin/activate' && cd '%s'\n" "$VENV_DIR" "$PROJECT_ROOT"
}

_detect_user_shell_name() {
  local s="${SHELL##*/}"
  printf '%s' "${s:-bash}"
}

print_activate_commands() {
  local shname
  shname="$(_detect_user_shell_name)"
  title "Activate in your current terminal"
  ok "Venv: $VENV_DIR ($(_venv_python_version "$VENV_DIR"))"
  hr
  if [[ "$shname" == "zsh" ]]; then
    info "Recommended for zsh (Powerlevel10k / custom .zshrc — no subshell noise):"
    printf '\n  %beval "$(%s/dev-venv.sh activate --print)"%s\n\n' "$CYAN" "$PROJECT_ROOT" "$NC"
    info "Or run the steps manually:"
  else
    info "Recommended (bash — activates in this window, keeps your prompt):"
    if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
      printf '\n  %bsource %s/dev-venv.sh activate --print | source /dev/stdin%s\n\n' \
        "$CYAN" "$PROJECT_ROOT" "$NC"
    fi
  fi
  printf '  %bsource %s/bin/activate%s\n' "$CYAN" "$VENV_DIR" "$NC"
  printf '  %bcd %s%s\n\n' "$CYAN" "$PROJECT_ROOT" "$NC"
  warn "Avoid: full zsh subshell if your ~/.zshrc prints calendar/IP on startup (p10k warning)."
  info "For a quiet isolated shell instead: ${BOLD}./dev-venv.sh shell${NC}"
}

do_activate() {
  if ! _is_venv_dir "$VENV_DIR"; then
    warn "No venv at $VENV_DIR — running setup first."
    do_setup
    return
  fi
  print_activate_commands
}

do_shell_minimal() {
  if ! _is_venv_dir "$VENV_DIR"; then
    warn "No venv at $VENV_DIR — running setup first."
    do_setup
  fi
  local zdot="$PROJECT_ROOT/.dev-shell"
  mkdir -p "$zdot"
  cat >"$zdot/.zshrc" <<EOF
# webaudit minimal dev shell — skips your ~/.zshrc (p10k, calendar, etc.)
export PROMPT='(webaudit) %~ %# '
source '$VENV_DIR/bin/activate'
cd '$PROJECT_ROOT'
echo ''
echo 'webaudit dev shell — minimal zsh (~/.zshrc skipped). Type exit to leave.'
echo ''
EOF

  title "Minimal dev shell"
  info "Uses ${BOLD}ZDOTDIR=$zdot${NC} — your ~/.zshrc is NOT loaded (no p10k/calendar noise)."
  ok "Type ${BOLD}exit${NC} when done."
  hr
  ZDOTDIR="$zdot" exec zsh -i
}

do_shell_bash() {
  if ! _is_venv_dir "$VENV_DIR"; then
    warn "No venv at $VENV_DIR — running setup first."
    do_setup
  fi
  title "Minimal bash dev shell"
  info "No ~/.bashrc / profile — quiet fallback if zsh minimal shell is unavailable."
  ok "Type ${BOLD}exit${NC} when done."
  hr
  # shellcheck disable=SC1091
  exec bash --noprofile --norc -c "source '$VENV_DIR/bin/activate' && cd '$PROJECT_ROOT' && PS1='(webaudit) \W\$ ' && exec bash --noprofile --norc -i"
}

do_shell() {
  if command -v zsh >/dev/null 2>&1; then
    do_shell_minimal
  else
    do_shell_bash
  fi
}

do_source_activate() {
  if ! _is_venv_dir "$VENV_DIR"; then
    err "No venv at $VENV_DIR — run: ./dev-venv.sh setup"
    return 1
  fi
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  cd "$PROJECT_ROOT" || return 1
  ok "Activated $VENV_DIR (cwd: $PROJECT_ROOT)"
}

do_setup() {
  title "Setup — Web Audit v2 .venv"
  show_existing_venvs
  show_pyenv_state
  show_system_python
  hr

  if _is_venv_dir "$VENV_DIR"; then
    warn "Default venv already exists: $VENV_DIR"
    printf '%b\n' "${BOLD}Choose:${NC}"
    printf '  1) Use existing (show activate command)\n'
    printf '  2) Refresh deps only (pip install -e)\n'
    printf '  3) Recreate from scratch (delete + new venv)\n'
    printf '  4) Cancel\n'
    local choice
    printf '%b' "${CYAN}Choice [1-4] (default 2):${NC} "
    read -r choice
    case "${choice:-2}" in
      1) print_activate_commands; return ;;
      2) do_refresh; return ;;
      3)
        if confirm "Delete $VENV_DIR and recreate?"; then
          rm -rf "$VENV_DIR"
          ok "Removed old venv"
        else
          info "Cancelled."
          return
        fi
        ;;
      4|q|Q) info "Cancelled."; return ;;
      *) do_refresh; return ;;
    esac
  fi

  local py
  if ! py="$(pick_python)"; then
    err "Need Python >= 3.11 (python3.11+ not found on PATH)."
    exit 1
  fi
  info "Using $py ($($py --version 2>&1))"

  "$py" -m venv "$VENV_DIR"
  ok "Created $VENV_DIR"

  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  python -m pip install -U pip wheel >/dev/null
  pip install -e "$PROJECT_ROOT[dev]"
  ok "Installed webaudit editable + dev deps"

  print_usage_hint
}

do_teardown() {
  title "Teardown — remove .venv"
  show_existing_venvs
  hr

  if ! _is_venv_dir "$VENV_DIR"; then
    warn "Nothing to remove at $VENV_DIR"
    if confirm "Remove ANY other detected venvs instead?"; then
      local path
      while IFS= read -r path; do
        [[ -z "$path" ]] && continue
        rm -rf "$path"
        ok "Removed $path"
      done < <(collect_venv_paths)
    fi
    return 0
  fi

  warn "About to delete: $VENV_DIR"
  if confirm "Proceed with teardown?"; then
    rm -rf "$VENV_DIR"
    ok "Teardown complete — $VENV_DIR removed"
  else
    info "Teardown cancelled."
  fi
}

do_status() {
  title "Web Audit v2 — dev environment status"
  info "Project:  $PROJECT_ROOT"
  info "Default venv: $VENV_DIR"
  hr
  show_existing_venvs
  show_pyenv_state
  show_system_python

  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    hr
    ok "Currently active: ${VIRTUAL_ENV}"
  fi
}

print_usage_hint() {
  hr
  ok "Ready. Examples:"
  printf '  %beval "$(./dev-venv.sh activate --print)"   # zsh: activate here (no subshell)%s\n' "$DIM" "$NC"
  printf '  %s./dev-venv.sh shell      # minimal quiet subshell (skips ~/.zshrc)%s\n' "$DIM" "$NC"
  printf '  %s./dev-venv.sh activate   # print activate commands%s\n' "$DIM" "$NC"
  printf '  %swebaudit scan https://example.com%s\n' "$DIM" "$NC"
  printf '  %spytest%s\n' "$DIM" "$NC"
  printf '  %s./dev-venv.sh teardown%s\n' "$DIM" "$NC"
  hr
  info "Plain English:"
  printf '  %sSetup (above) = install the webaudit command on this machine.%s\n' "$DIM" "$NC"
  printf '  %swebaudit scan URL = run a check; results go to audit_logs/%s\n' "$DIM" "$NC"
  printf '  %swebaudit completion install   # optional Tab autocomplete (see plain-English panel)%s\n' "$DIM" "$NC"
  printf '  %swebaudit completion uninstall # remove Tab files from ~ (NOT removed by teardown)%s\n' "$DIM" "$NC"
  printf '  %sSee docs/getting_started_plain.md for a full non-technical guide.%s\n' "$DIM" "$NC"
}

usage() {
  cat <<EOF
${BOLD}Web Audit v2 — dev-venv.sh${NC}

Usage:
  $(basename "$0")              Interactive menu (detects existing .venv)
  $(basename "$0") activate     Print how to activate in your current shell
  $(basename "$0") shell        Minimal dev subshell (skips ~/.zshrc / p10k noise)
  $(basename "$0") setup        Create .venv + pip install -e ".[dev]"
  $(basename "$0") refresh      Reinstall deps into existing .venv (no recreate)
  $(basename "$0") teardown     Remove .venv (with confirmation)
  $(basename "$0") status       List venvs, ages, pyenv, system Python
  $(basename "$0") cleanup      Prompt to remove all detected venvs

Activate in current shell (recommended for zsh + Powerlevel10k):
  eval "\$(./dev-venv.sh activate --print)"

Activate from bash only (source this script):
  source ./dev-venv.sh

Environment:
  WEBAUDIT_VENV   Override venv path (default: $PROJECT_ROOT/.venv)

EOF
}

interactive_menu() {
  title "Web Audit v2 — dev environment"
  show_existing_venvs
  show_pyenv_state
  hr

  if _is_venv_dir "$VENV_DIR"; then
    ok "Existing .venv ready — $VENV_DIR"
    printf '%b\n' "${BOLD}What do you want to do?${NC}"
    printf '  %s1)%s Show activate command (current shell)  %s(recommended for zsh/p10k)%s\n' \
      "$GREEN" "$NC" "$DIM" "$NC"
    printf '  2) Minimal dev shell (skips ~/.zshrc — quiet)\n'
    printf '  3) Refresh deps only (pip install -e)\n'
    printf '  4) Full setup / recreate .venv\n'
    printf '  5) Status only\n'
    printf '  6) Teardown .venv\n'
    printf '  7) Cleanup — remove all detected venvs\n'
    printf '  8) Exit\n'
    hr
    local choice
    printf '%b' "${CYAN}Choice [1-8] (default 1):${NC} "
    read -r choice
    case "${choice:-1}" in
      1) print_activate_commands ;;
      2) do_shell ;;
      3) do_refresh ;;
      4) do_setup ;;
      5) do_status ;;
      6) do_teardown ;;
      7) prompt_cleanup_venvs ;;
      8|q|Q) info "Bye." ;;
      *) err "Invalid choice"; exit 1 ;;
    esac
    return
  fi

  warn "No .venv yet — setup required before webaudit will run."
  printf '%b\n' "${BOLD}What do you want to do?${NC}"
  printf '  1) Setup .venv (install deps)\n'
  printf '  2) Status only\n'
  printf '  3) Exit\n'
  hr
  local choice
  printf '%b' "${CYAN}Choice [1-3] (default 1):${NC} "
  read -r choice
  case "${choice:-1}" in
    1) do_setup ;;
    2) do_status ;;
    3|q|Q) info "Bye." ;;
    *) err "Invalid choice"; exit 1 ;;
  esac
}

main() {
  local cmd="${1:-}"

  case "$cmd" in
    -h|--help|help)
      usage
      ;;
    setup|up|install)
      do_setup
      ;;
    activate|use|on)
      if [[ "${2:-}" == "--print" ]]; then
        do_activate_print
      else
        do_activate
      fi
      ;;
    refresh|sync)
      do_refresh
      ;;
    teardown|down|remove|rm)
      do_teardown
      ;;
    status|list|ls)
      do_status
      ;;
    cleanup|clean)
      show_existing_venvs
      prompt_cleanup_venvs
      ;;
    shell|sh)
      do_shell
      ;;
    "")
      interactive_menu
      ;;
    *)
      err "Unknown command: $cmd"
      usage
      exit 1
      ;;
  esac
}

# Sourced from bash only: source ./dev-venv.sh
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  case "${1:-}" in
    ""|activate|use|on)
      do_source_activate
      ;;
    *)
      err "When sourcing: source ./dev-venv.sh   (bash only)"
      err "From zsh use: eval \"\$(./dev-venv.sh activate --print)\""
      return 1 2>/dev/null || exit 1
      ;;
  esac
  return 0 2>/dev/null || exit 0
fi

main "$@"
