#!/usr/bin/env bash
# Web Audit v2 — run GHCR/local webaudit image with host-mounted reports and host-side --open.
#
# Browsers cannot open from inside the container. This wrapper:
#   1. Mounts a host directory for audit_logs
#   2. Runs webaudit with --open none in Docker
#   3. Opens reports on the host (or prompts y/N)
#
# Pull-only install (no git clone — run once):
#   curl -fsSL https://raw.githubusercontent.com/Vlad-1618M/web_audit/v.tools_main/v2_python_core/scripts/install-webaudit-docker.sh | bash
#   webaudit-docker scan https://example.com --open html
#
# Repo devs:
#   ./scripts/webaudit-docker.sh scan https://example.com
#   ./scripts/webaudit-docker.sh --output-dir documents scan https://example.com -v --open html
#   ./scripts/webaudit-docker.sh --image webaudit:local scan https://example.com
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_IMAGE="${WEBAUDIT_DOCKER_IMAGE:-ghcr.io/vlad-1618m/webaudit:latest}"
CONTAINER_OUTPUT="/work/audit_logs"
LAST_RUN_MARKER=".webaudit-last-run"

IMAGE="$DEFAULT_IMAGE"
OUTPUT_PRESET="cwd"
HOST_OPEN=""
ASSUME_YES=0
SHALLOW=0
SUBCMD=""
SCAN_ARGS=()
DOCKER_SCAN_ARGS=()

if [[ -t 1 ]] && command -v tput >/dev/null 2>&1; then
  _n="$(tput sgr0 2>/dev/null || true)"
  GREEN="$(tput setaf 2 2>/dev/null || true)"
  YELLOW="$(tput setaf 3 2>/dev/null || true)"
  CYAN="$(tput setaf 6 2>/dev/null || true)"
  RED="$(tput setaf 1 2>/dev/null || true)"
  BOLD="$(tput bold 2>/dev/null || true)"
  DIM="$(tput dim 2>/dev/null || true)"
  NC="$_n"
else
  GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'; CYAN=$'\033[0;36m'
  RED=$'\033[0;31m'; BOLD=$'\033[1m'; DIM=$'\033[2m'; NC=$'\033[0m'
fi

err() { printf '%b\n' "${RED}✖${NC} $*" >&2; }
ok()  { printf '%b\n' "${GREEN}✔${NC} $*"; }
warn() { printf '%b\n' "${YELLOW}⚠${NC} $*"; }

engine_version_line() {
  local ver=""
  if command -v docker >/dev/null 2>&1; then
    ver="$(docker run --rm "$IMAGE" --version 2>/dev/null | head -n 1 || true)"
  fi
  if [[ -n "$ver" ]]; then
    printf '%b\n' "${DIM}Engine:${NC} ${ver}  ${DIM}(${IMAGE})${NC}"
  else
    printf '%b\n' "${DIM}Engine:${NC} ${IMAGE}  ${DIM}(run: $(basename "$0") version)${NC}"
  fi
}

usage() {
  cat <<EOF
${BOLD}webaudit-docker${NC} — Web Audit Pro via Docker (host reports + host browser open)

EOF
  engine_version_line
  cat <<EOF

${BOLD}Usage${NC}
  $(basename "$0") [wrapper options] scan URL [webaudit scan flags...]
  $(basename "$0") version
  $(basename "$0") engine-help

${BOLD}Wrapper options${NC} (parsed before ${CYAN}scan${NC})
  --output-dir PRESET   Host folder for reports (default: cwd)
                        PRESET: cwd | home | desktop | documents | /absolute/path
  --open MODE           Open on ${BOLD}host${NC} after scan: html | json | txt | all | none | ask
                        (default: ask if TTY, else none). Strips --open from container args.
  --image IMAGE         Docker image (default: ${DEFAULT_IMAGE})
  --shallow             Static scan only — do not add default ${CYAN}--js --api${NC}
  -y, --yes             Skip post-scan open prompt (still honors explicit --open html|all|…)
  -h, --help            This help

${BOLD}Default scan depth${NC} (same as Mac app): adds ${CYAN}--js${NC} (Playwright) and ${CYAN}--api${NC}
  unless you pass them yourself or use ${CYAN}--shallow${NC}. Playwright is bundled in the GHCR image.

${BOLD}Examples${NC}
  $(basename "$0") scan https://example.com
  $(basename "$0") --output-dir documents scan https://example.com -v --open html
  $(basename "$0") --shallow scan https://example.com -v
  $(basename "$0") --image webaudit:local scan https://example.com

${BOLD}Engine flags${NC} (passed through to webaudit inside the container):
  ${CYAN}-v${NC} verbose  ${CYAN}--js${NC} Playwright pass  ${CYAN}--api${NC} GraphQL/OpenAPI probes
  ${CYAN}--sarif${NC} SARIF export  ${CYAN}--site-config FILE${NC} per-site YAML
  Full list: ${CYAN}$(basename "$0") engine-help${NC}  or  ${CYAN}docker run --rm ${DEFAULT_IMAGE} scan --help${NC}

${BOLD}Notes${NC}
  ${BOLD}Install:${NC} ${CYAN}curl -fsSL https://raw.githubusercontent.com/Vlad-1618M/web_audit/v.tools_main/v2_python_core/scripts/install-webaudit-docker.sh | bash${NC}
  Flags may appear before or after the URL; the wrapper reorders them for Typer (options first, URL last).
  Raw ${CYAN}docker run … --open html${NC} cannot open a browser — use this wrapper.
  See: docs/docker_ci.md
EOF
}

run_engine_help() {
  need_cmd docker
  docker run --rm "$IMAGE" scan --help
}

run_engine_version() {
  need_cmd docker
  docker run --rm "$IMAGE" --version
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { err "Missing command: $1"; exit 1; }
}

resolve_host_output_dir() {
  local preset="$1"
  case "$preset" in
    cwd|.) printf '%s\n' "$(pwd)/audit_logs" ;;
    home|~|"~") printf '%s\n' "${HOME}/WebAudit/audit_logs" ;;
    desktop) printf '%s\n' "${HOME}/Desktop/WebAudit" ;;
    documents) printf '%s\n' "${HOME}/Documents/WebAudit" ;;
    /*) printf '%s\n' "$preset" ;;
    *) err "Unknown --output-dir preset: $preset (use cwd|home|desktop|documents|/path)"; exit 2 ;;
  esac
}

normalize_open_mode() {
  local raw="${1:-}"
  raw="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')"
  case "$raw" in
    ""|ask) echo "ask" ;;
    none|n) echo "none" ;;
    html|h|report|p|pdf) echo "html" ;;
    json|j) echo "json" ;;
    txt|t) echo "txt" ;;
    all|a) echo "all" ;;
    *) echo "$raw" ;;
  esac
}

open_host_path() {
  local target="$1"
  if [[ ! -e "$target" ]]; then
    err "Not found: $target"
    return 1
  fi
  if [[ "$(uname -s)" == "Darwin" ]]; then
    open "$target"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$target"
  elif command -v sensible-browser >/dev/null 2>&1; then
    sensible-browser "$target"
  else
    err "No browser opener (macOS: open, Linux: xdg-open)"
    printf '%b\n' "${DIM}  $target${NC}"
    return 1
  fi
}

find_latest_run_dir() {
  local base="$1"
  local marker="$base/$LAST_RUN_MARKER"
  local run_dir=""

  if [[ -f "$marker" ]]; then
    run_dir="$(tr -d '\r\n' < "$marker")"
    if [[ -n "$run_dir" && -d "$run_dir" ]]; then
      printf '%s\n' "$run_dir"
      return 0
    fi
  fi

  shopt -s nullglob
  local -a dirs=("$base"/*/)
  shopt -u nullglob
  if ((${#dirs[@]} == 0)); then
    return 1
  fi
  local latest=""
  latest="$(printf '%s\n' "${dirs[@]%/}" | sort -r | head -n 1)"
  [[ -n "$latest" && -d "$latest" ]] || return 1
  printf '%s\n' "$latest"
}

host_open_reports() {
  local run_dir="$1"
  local mode="$2"
  local json="$run_dir/audit_run.json"
  local html="$run_dir/report.html"
  local txt="$run_dir/report.txt"

  case "$mode" in
    none) return 0 ;;
    html)
      [[ -f "$html" ]] && open_host_path "$html" && ok "Opened report.html on host"
      ;;
    json)
      [[ -f "$json" ]] && open_host_path "$json" && ok "Opened audit_run.json on host"
      ;;
    txt)
      [[ -f "$txt" ]] && open_host_path "$txt" && ok "Opened report.txt on host"
      ;;
    all)
      [[ -f "$html" ]] && open_host_path "$html"
      [[ -f "$txt" ]] && open_host_path "$txt"
      [[ -f "$json" ]] && open_host_path "$json"
      ok "Opened available reports on host"
      ;;
    ask)
      if [[ ! -t 0 ]]; then
        return 0
      fi
      local answer lower
      printf '\n%b\n' "${BOLD}Reports saved on your machine:${NC}"
      printf '%b\n' "  ${run_dir}/"
      [[ -f "$html" ]] && printf '%b\n' "    report.html"
      [[ -f "$json" ]] && printf '%b\n' "    audit_run.json"
      [[ -f "$txt" ]] && printf '%b\n' "    report.txt"
      printf '%b' "${YELLOW}?${NC} Open report.html in browser? ${DIM}[y/N]${NC} "
      read -r answer
      lower="$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')"
      if [[ "$lower" == "y" || "$lower" == "yes" ]]; then
        [[ -f "$html" ]] && open_host_path "$html"
      fi
      ;;
    *)
      warn "Unknown open mode: $mode"
      ;;
  esac
}

parse_wrapper_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      scan)
        SUBCMD="scan"
        shift
        SCAN_ARGS=("$@")
        return 0
        ;;
      version)
        SUBCMD="version"
        return 0
        ;;
      engine-help)
        SUBCMD="engine-help"
        return 0
        ;;
      -h|--help|help)
        usage
        exit 0
        ;;
      --output-dir)
        [[ $# -ge 2 ]] || { err "--output-dir requires a value"; exit 2; }
        OUTPUT_PRESET="$2"
        shift 2
        ;;
      --open)
        [[ $# -ge 2 ]] || { err "--open requires a value"; exit 2; }
        HOST_OPEN="$2"
        shift 2
        ;;
      --open=*)
        HOST_OPEN="${1#*=}"
        shift
        ;;
      --image)
        [[ $# -ge 2 ]] || { err "--image requires a value"; exit 2; }
        IMAGE="$2"
        shift 2
        ;;
      -y|--yes)
        ASSUME_YES=1
        shift
        ;;
      --shallow)
        SHALLOW=1
        shift
        ;;
      *)
        err "Unknown option: $1 (expected 'scan' or 'version' — try --help)"
        exit 2
        ;;
    esac
  done
  err "Missing subcommand: scan | version (try --help)"
  exit 2
}

scan_args_want_engine_help() {
  [[ ${#SCAN_ARGS[@]} -eq 0 ]] && return 1
  case "${SCAN_ARGS[0]}" in
    -h | --help | help) return 0 ;;
  esac
  return 1
}

ensure_default_scan_depth() {
  [[ "$SHALLOW" -eq 1 ]] && return 0
  local -a opts=() url="" arg
  local has_js=0 has_api=0

  for arg in "${DOCKER_SCAN_ARGS[@]}"; do
    case "$arg" in
      --js) has_js=1 ;;
      --api) has_api=1 ;;
      http://* | https://*) url="$arg" ;;
      *) opts+=("$arg") ;;
    esac
  done

  [[ -n "$url" ]] || return 0
  (( has_js )) || opts=(--js "${opts[@]}")
  (( has_api )) || opts=(--api "${opts[@]}")
  DOCKER_SCAN_ARGS=("${opts[@]}" "$url")
}

strip_open_for_container() {
  local scan_url=""
  local -a scan_opts=()
  local needs_value=0

  while [[ $# -gt 0 ]]; do
    if (( needs_value )); then
      scan_opts+=("$1")
      needs_value=0
      shift
      continue
    fi

    case "$1" in
      --open)
        if [[ -z "$HOST_OPEN" ]]; then
          HOST_OPEN="${2:-ask}"
        fi
        scan_opts+=(--open none)
        shift 2
        ;;
      --open=*)
        if [[ -z "$HOST_OPEN" ]]; then
          HOST_OPEN="${1#*=}"
        fi
        scan_opts+=(--open none)
        shift
        ;;
      --config|--site-config|-c|--output|-o)
        scan_opts+=("$1")
        needs_value=1
        shift
        ;;
      --config=*|--site-config=*|--output=*|-o=*)
        scan_opts+=("$1")
        shift
        ;;
      -?*)
        scan_opts+=("$1")
        shift
        ;;
      http://*|https://*)
        if [[ -z "$scan_url" ]]; then
          scan_url="$1"
        else
          err "Multiple URLs are not supported: $scan_url and $1"
          exit 2
        fi
        shift
        ;;
      scan)
        err "Unexpected 'scan' after subcommand — pass flags and URL only (try --help)"
        exit 2
        ;;
      *)
        if [[ -z "$scan_url" ]]; then
          scan_url="$1"
        else
          err "Unexpected argument: $1"
          exit 2
        fi
        shift
        ;;
    esac
  done

  if (( needs_value )); then
    err "Missing value for last option"
    exit 2
  fi

  if [[ -z "$scan_url" ]]; then
    err "Missing scan URL (usage: $(basename "$0") scan https://example.com [flags...])"
    exit 2
  fi

  DOCKER_SCAN_ARGS=("${scan_opts[@]}" "$scan_url")
}

main() {
  if [[ $# -eq 0 ]]; then
    usage
    exit 0
  fi

  need_cmd docker

  parse_wrapper_args "$@"

  case "$SUBCMD" in
    version)
      run_engine_version
      exit 0
      ;;
    engine-help)
      run_engine_help
      exit 0
      ;;
    scan) ;;
    *)
      err "Unsupported subcommand: $SUBCMD"
      exit 2
      ;;
  esac

  if scan_args_want_engine_help; then
    run_engine_help
    exit 0
  fi

  if [[ ${#SCAN_ARGS[@]} -lt 1 ]]; then
    err "Usage: $(basename "$0") scan URL [webaudit flags...]"
    exit 2
  fi

  strip_open_for_container "${SCAN_ARGS[@]}"
  ensure_default_scan_depth

  if [[ -z "$HOST_OPEN" ]]; then
    if [[ -t 0 ]]; then
      HOST_OPEN="ask"
    else
      HOST_OPEN="none"
    fi
  fi
  HOST_OPEN="$(normalize_open_mode "$HOST_OPEN")"

  local host_dir
  host_dir="$(resolve_host_output_dir "$OUTPUT_PRESET")"
  mkdir -p "$host_dir"

  printf '%b\n' "${DIM}Host reports:${NC} ${host_dir}/"
  printf '%b\n' "${DIM}Image:${NC} ${IMAGE}"

  local -a docker_run_args=(--rm)
  if [[ -t 1 ]]; then
    docker_run_args+=(-t)
  fi

  if ! docker run "${docker_run_args[@]}" \
    -e WEBAUDIT_IN_DOCKER=1 \
    -e "WEBAUDIT_HOST_OUTPUT_DIR=${host_dir}" \
    -e "WEBAUDIT_LAST_RUN_FILE=${CONTAINER_OUTPUT}/${LAST_RUN_MARKER}" \
    -e "TERM=${TERM:-xterm-256color}" \
    -v "${host_dir}:${CONTAINER_OUTPUT}" \
    "$IMAGE" \
    scan "${DOCKER_SCAN_ARGS[@]}"; then
    err "Container scan failed"
    exit 1
  fi

  local run_dir
  if ! run_dir="$(find_latest_run_dir "$host_dir")"; then
    warn "Scan finished but no report directory found under ${host_dir}/"
    exit 0
  fi

  ok "Reports: ${run_dir}/"

  if [[ "$HOST_OPEN" == "ask" && "$ASSUME_YES" -eq 1 ]]; then
    HOST_OPEN="none"
  fi

  if [[ "$HOST_OPEN" == "none" ]]; then
    printf '%b\n' "${DIM}Open manually: ${run_dir}/report.html${NC}"
  else
    host_open_reports "$run_dir" "$HOST_OPEN"
  fi
}

main "$@"
