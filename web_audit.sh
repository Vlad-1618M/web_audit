#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# web_security_audit.sh v2.5
# Framework-agnostic web security audit tool
# Supports: WordPress, Django, Laravel, Rails, PHP generic
# Compatible with bash 4+ (Arch/default Linux) and zsh (macOS)
# ─────────────────────────────────────────────────────────────────

# zsh compatibility: 0-based arrays, avoid read-only `status` conflicts
if [[ -n "${ZSH_VERSION:-}" ]]; then
  setopt KSH_ARRAYS 2>/dev/null
fi

# macOS ships bash 3.2 — re-exec with zsh when bash lacks associative arrays
if [[ -n "${BASH_VERSION:-}" ]] && [[ "${BASH_VERSION%%.*}" -lt 4 ]]; then
  if command -v zsh >/dev/null 2>&1; then
    exec zsh "$0" "$@"
  fi
  echo "Error: bash 4+ required (found ${BASH_VERSION}). Install bash 4+ or run: zsh $0" >&2
  exit 1
fi

AUDIT_PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PATH="${AUDIT_PATH}:${PATH}"

_resolve_tool() {
  local name="$1" fallback="$2" candidate
  for candidate in "/opt/homebrew/bin/${name}" "/usr/local/bin/${name}" "/usr/bin/${name}" "/bin/${name}"; do
    [[ -x "$candidate" ]] && { printf '%s' "$candidate"; return 0; }
  done
  command -v "$name" 2>/dev/null || printf '%s' "$fallback"
}

CURL=$(_resolve_tool curl /usr/bin/curl)
OPENSSL=$(_resolve_tool openssl /usr/bin/openssl)
DATE=$(_resolve_tool date /bin/date)
MKDIR=$(_resolve_tool mkdir /bin/mkdir)
HOSTNAME_CMD=$(_resolve_tool hostname /bin/hostname)
GREP=$(_resolve_tool grep /usr/bin/grep)
SED=$(_resolve_tool sed /usr/bin/sed)
HEAD=$(_resolve_tool head /usr/bin/head)
MKTEMP=$(_resolve_tool mktemp /usr/bin/mktemp)
export GREP SED HEAD MKTEMP CURL OPENSSL DATE MKDIR HOSTNAME_CMD

TIMEOUT=15

# audit_logs live next to this script — cwd-independent (standalone use outside repo)
if [[ -n "${ZSH_VERSION:-}" ]]; then
  SCRIPT_DIR="${0:A:h}"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
LOG_ROOT="${SCRIPT_DIR}/audit_logs"
SITE_CONFIG_DIR="${SCRIPT_DIR}/site_configs"
MISC_SCAN_MAX_PAGES=8
MISC_HTML_MAX=65536
MISC_HTML_IMG_MAX=98304

AUDIT_CONFIG=""
AUDIT_CONFIG_EXPLICIT=0
TARGET_AUDIT_CONFIG=""
NO_SITE_CONFIG=0
declare -a CONFIG_EXTRA_PATHS CONFIG_EXPECTED_OPEN CONFIG_APP_SURFACE CONFIG_RATE_LIMIT_POST
CONFIG_MISC_MAX_PROBE_URLS=250
CONFIG_MISC_MAX_INTERNAL_URLS=250
CONFIG_MISC_SHOW_PROBE_URLS=1
CONFIG_MISC_SHOW_INTERNAL_URLS=1
declare -a DISCOVERED_PATHS
declare -a DISCOVERED_FROM_LINKS
declare -a DISCOVERED_FROM_SITEMAP
CONFIG_GEN_ACTIVE_MAX=8

# CLI / run mode
QUIET=0
DRY_RUN=0
JSON_STDOUT=0
PROBE_THROTTLE_MS=0
FAIL_UNDER_HYGIENE=""
FAIL_UNDER_EXPOSURE=""
COMPARE_BASELINE=""
SESSION_EXIT=0
LAST_JSON_PATH=""

# Parsed artifacts (per-target; reset each audit)
CACHED_HEADERS=""
ARTIFACT_ROBOTS_RAW=""
declare -a ARTIFACT_ROBOTS_DISALLOW ARTIFACT_ROBOTS_ALLOW ARTIFACT_ROBOTS_SITEMAPS
ARTIFACT_SECURITY_TXT=""
ARTIFACT_SITEMAP_RAW=""
declare -a ARTIFACT_SITEMAP_LOCS
ARTIFACT_REDIRECT_CHAIN=""
ARTIFACT_HSTS_DETAIL=""
ARTIFACT_CSP_DETAIL=""
declare -a ARTIFACT_CORS_NOTES
DESIGNER_NAME=""
DESIGNER_SOURCE=""
DESIGNER_LINK=""
DESIGNER_CREDIBLE=0
DESIGNER_HAS_PROPER=0
DESIGNER_HAS_RISK=0
DESIGNER_HEADER_STATUS=""
DESIGNER_DISCOVERED_PATH=""
declare -a DESIGNER_TRACE   # path|placement|seo_impact|note
ARTIFACT_DESIGNER_SUMMARY=""
declare -a MISC_URLS        # full_url|source
declare -a MISC_IMAGES      # image_url|page_path
MISC_URL_COUNT=0
MISC_PROBE_URL_COUNT=0
MISC_INTERNAL_URL_COUNT=0
MISC_IMAGE_COUNT=0
MISC_PAGES_SCANNED=0
CACHED_HOME_HTML=""
declare -a SESSION_SCORES   # "url|hygiene|exposure|json_path"
COMPARE_BASELINE_LABEL=""
COMPARE_HYGIENE_DELTA=0
COMPARE_EXPOSURE_DELTA=0
COMPARE_PREV_HYGIENE=""
COMPARE_PREV_EXPOSURE=""
declare -a COMPARE_NEW_ACTIONS

# ── Run / session identifiers (set once per invocation) ───────────
RUN_DATE=$("$DATE" +"%Y-%m-%d")
RUN_TIME=$("$DATE" +"%H%M%S")
RUN_TIMESTAMP=$("$DATE" +"%Y%m%d_%H%M%S")
RUN_SESSION_DIR="${LOG_ROOT}/${RUN_DATE}_${RUN_TIME}"

# Per-target paths (set by setup_url_logs for each URL)
URL_SLUG=""
URL_LOG_DIR=""
LOG_TXT=""
LOG_JSON=""
LOG_HTML=""

"$MKDIR" -p "$RUN_SESSION_DIR"

# ── System / runtime metadata (included in every report) ──────────
collect_system_info() {
  SYS_ARCH=$(uname -m 2>/dev/null || echo "unknown")
  SYS_OS=$(uname -s 2>/dev/null || echo "unknown")
  SYS_KERNEL=$(uname -r 2>/dev/null || echo "unknown")
  SYS_HOST=$("$HOSTNAME_CMD" -s 2>/dev/null || "$HOSTNAME_CMD" 2>/dev/null || echo "unknown")
  if [[ -n "${ZSH_VERSION:-}" ]]; then
    SYS_SHELL="zsh ${ZSH_VERSION}"
  elif [[ -n "${BASH_VERSION:-}" ]]; then
    SYS_SHELL="bash ${BASH_VERSION}"
  else
    SYS_SHELL="${SHELL:-unknown}"
  fi
  if [[ -r /etc/os-release ]]; then
    SYS_OS_FULL=$(grep -E '^PRETTY_NAME=' /etc/os-release 2>/dev/null | cut -d= -f2- | tr -d '"')
  else
    SYS_OS_FULL="${SYS_OS} ${SYS_KERNEL}"
  fi
  SYS_UNAME=$(uname -a 2>/dev/null || echo "unknown")
}
collect_system_info

RED=$'\033[0;31m'
GRN=$'\033[0;32m'
YLW=$'\033[0;33m'
BLU=$'\033[0;34m'
CYN=$'\033[0;36m'
MGN=$'\033[0;35m'
RST=$'\033[0m'

BRAND_VENDOR="Vtools"
BRAND_APP="https://muzar.io/"
BRAND_GITHUB="https://github.com/Vlad-1618M"
TOOL_VERSION="2.5"

show_usage() {
  cat <<EOF
Usage: $(basename "$0") [options] [URL ...]

Options:
  --config FILE           Optional INI: extra paths, expected_open, rate_limit_post
                          (explicit — skips per-site auto-config prompts)
                          Template: site.conf.template (same directory as this script)
  --no-site-config        Never load or create site_configs/<host>.conf
  --framework, -f         django | wordpress | laravel | rails | php | auto
  --no-browser            Do not open HTML reports in a browser when done
  --quiet                 Minimal terminal output (errors still shown)
  --json-stdout           Print path to last target JSON on stdout when done
  --dry-run               Show probe/check plan without sending HTTP traffic
  --compare FILE          Compare scores to a previous audit JSON report
  --fail-under-hygiene N  Exit 1 if Hygiene score is below N (after all targets)
  --fail-under-exposure N Exit 1 if Exposure score is below N (after all targets)
  --throttle MS           Sleep MS milliseconds between path probes (polite mode)
  -h, --help              Show this help

Examples:
  $(basename "$0") --framework django https://example.com
  $(basename "$0") --config ./my-site.conf --framework django https://example.com
  OPEN_BROWSER=0 $(basename "$0") --framework django --fail-under-exposure 100 https://staging.example.com
  OPEN_BROWSER=0 $(basename "$0") --quiet --json-stdout --compare audit_logs/prev/host/audit_*.json --framework django https://example.com

See README.md for capabilities, limits, and requirements.
Non-interactive use requires URL(s) and --framework. Without URLs, the script prompts interactively.
EOF
}

parse_cli_args() {
  FORCE_FRAMEWORK=""
  TARGET_URLS=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --config)     AUDIT_CONFIG="$2"; AUDIT_CONFIG_EXPLICIT=1; shift 2 ;;
      --no-site-config) NO_SITE_CONFIG=1; shift ;;
      --framework|-f) FORCE_FRAMEWORK=$(printf '%s' "$2" | tr '[:upper:]' '[:lower:]'); shift 2 ;;
      --no-browser) export OPEN_BROWSER=0; shift ;;
      --quiet)      QUIET=1; shift ;;
      --json-stdout) JSON_STDOUT=1; shift ;;
      --dry-run)    DRY_RUN=1; shift ;;
      --compare)    COMPARE_BASELINE="$2"; shift 2 ;;
      --fail-under-hygiene) FAIL_UNDER_HYGIENE="$2"; shift 2 ;;
      --fail-under-exposure) FAIL_UNDER_EXPOSURE="$2"; shift 2 ;;
      --throttle)   PROBE_THROTTLE_MS="$2"; shift 2 ;;
      -h|--help)    show_usage; exit 0 ;;
      http://*|https://*) TARGET_URLS+=("${1%/}"); shift ;;
      *)
        echo "Unknown argument: $1" >&2
        show_usage
        exit 1
        ;;
    esac
  done
  [[ "$FORCE_FRAMEWORK" == "php" ]] && FORCE_FRAMEWORK="php_generic"
  [[ -n "$COMPARE_BASELINE" && ! -f "$COMPARE_BASELINE" ]] && { echo "Compare baseline not found: $COMPARE_BASELINE" >&2; exit 1; }
}

trim_line() {
  # Avoid zsh/bash trim quirks — use sed with absolute path when available
  local s="$1"
  if [[ -x /usr/bin/sed ]]; then
    /usr/bin/sed 's/#.*//;s/^[[:space:]]*//;s/[[:space:]]*$//' <<< "$s"
  else
    s="${s%%#*}"
    s="${s#${s%%[![:space:]]*}}"
    s="${s%${s##*[![:space:]]}}"
    printf '%s' "$s"
  fi
}

load_audit_config() {
  local f="$1" quiet="${2:-0}" line section="" path label val
  [[ -n "$f" ]] || return 0
  [[ -f "$f" ]] || { echo "Config not found: $f" >&2; exit 1; }
  [[ "$quiet" -eq 0 ]] && echo "Config   : $f"
  while IFS= read -r line || [[ -n "$line" ]]; do
    line=$(trim_line "$line")
    [[ -z "$line" ]] && continue
    if [[ "${line:0:1}" == "[" && "${line: -1}" == "]" ]]; then
      section="${line:1:${#line}-2}"
      continue
    fi
    case "$section" in
      paths)
        [[ "$line" == extra=* ]] || continue
        path="${line#extra=}"
        path=$(trim_line "$path")
        [[ "$path" != /* ]] && path="/${path}"
        CONFIG_EXTRA_PATHS+=("$path")
        ;;
      expected_open)
        path="${line%%=*}"; label="${line#*=}"
        path=$(trim_line "$path")
        label=$(trim_line "$label")
        [[ "$path" != /* ]] && path="/${path}"
        CONFIG_EXPECTED_OPEN+=("$path")
        [[ "$label" == "app_surface" ]] && CONFIG_APP_SURFACE+=("$path")
        ;;
      rate_limit_post)
        path="${line%%=*}"; val="${line#*=}"
        path=$(trim_line "$path")
        [[ "$path" != /* ]] && path="/${path}"
        CONFIG_RATE_LIMIT_POST+=("${path}|${val}")
        ;;
      misc)
        case "$line" in
          max_probe_urls=*)     CONFIG_MISC_MAX_PROBE_URLS="${line#*=}" ;;
          max_internal_urls=*)  CONFIG_MISC_MAX_INTERNAL_URLS="${line#*=}" ;;
          show_probe_urls=*)    [[ "$(printf '%s' "${line#*=}" | tr '[:upper:]' '[:lower:]')" == no ]] && CONFIG_MISC_SHOW_PROBE_URLS=0 || CONFIG_MISC_SHOW_PROBE_URLS=1 ;;
          show_internal_urls=*) [[ "$(printf '%s' "${line#*=}" | tr '[:upper:]' '[:lower:]')" == no ]] && CONFIG_MISC_SHOW_INTERNAL_URLS=0 || CONFIG_MISC_SHOW_INTERNAL_URLS=1 ;;
          max_html_bytes=*)
            val=$(trim_line "${line#*=}")
            [[ "$val" =~ ^[0-9]+$ ]] && MISC_HTML_MAX="$val" ;;
          max_html_img_bytes=*)
            val=$(trim_line "${line#*=}")
            [[ "$val" =~ ^[0-9]+$ ]] && MISC_HTML_IMG_MAX="$val" ;;
        esac
        ;;
    esac
  done < "$f"
  [[ "$quiet" -eq 0 && ${#CONFIG_EXTRA_PATHS[@]} -gt 0 ]] && echo "  Extra paths: ${#CONFIG_EXTRA_PATHS[@]}"
  [[ "$quiet" -eq 0 && ${#CONFIG_RATE_LIMIT_POST[@]} -gt 0 ]] && echo "  POST rate-limit probes: ${#CONFIG_RATE_LIMIT_POST[@]}"
}

reset_config_state() {
  CONFIG_EXTRA_PATHS=()
  CONFIG_EXPECTED_OPEN=()
  CONFIG_APP_SURFACE=()
  CONFIG_RATE_LIMIT_POST=()
  CONFIG_MISC_MAX_PROBE_URLS=250
  CONFIG_MISC_MAX_INTERNAL_URLS=250
  CONFIG_MISC_SHOW_PROBE_URLS=1
  CONFIG_MISC_SHOW_INTERNAL_URLS=1
}

parse_cli_args "$@"

# ── Input (interactive fallback) ────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════╗"
echo "║     Web Security Audit Tool v2.5     ║"
echo "╚══════════════════════════════════════╝"

if [[ ${#TARGET_URLS[@]} -eq 0 ]]; then
  echo ""
  echo "Enter target URL(s). Options:"
  echo "  • One URL per line (blank line when done)"
  echo "  • Or comma-separated on a single line"
  echo ""
  while true; do
    printf "> "
    read -r line || break
    line=$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [[ -z "$line" ]] && break
    local_part="$line"
    while [[ "$local_part" == *","* ]]; do
      entry="${local_part%%,*}"
      entry=$(printf '%s' "$entry" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
      [[ -n "$entry" ]] && TARGET_URLS+=("${entry%/}")
      local_part="${local_part#*,}"
    done
    local_part=$(printf '%s' "$local_part" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [[ -n "$local_part" ]] && TARGET_URLS+=("${local_part%/}")
  done
fi

[[ ${#TARGET_URLS[@]} -eq 0 ]] && { echo "No URL(s) provided. Exiting."; exit 1; }

if [[ -z "$FORCE_FRAMEWORK" ]]; then
  echo ""
  printf "Force framework for all targets? [django/wordpress/laravel/rails/php/auto]: "
  read FORCE_FRAMEWORK
  FORCE_FRAMEWORK=$(printf '%s' "$FORCE_FRAMEWORK" | tr '[:upper:]' '[:lower:]')
  [[ "$FORCE_FRAMEWORK" == "php" ]] && FORCE_FRAMEWORK="php_generic"
fi

"$MKDIR" -p "$SITE_CONFIG_DIR"

echo ""
echo "Session  : $RUN_SESSION_DIR"
echo "Started  : $("$DATE")"
echo "Host     : $SYS_HOST ($SYS_ARCH / $SYS_OS)"
echo "Shell    : $SYS_SHELL"
echo "Framework: ${FORCE_FRAMEWORK:-auto}"
echo "Targets  : ${#TARGET_URLS[@]}"
for u in "${TARGET_URLS[@]}"; do echo "           - $u"; done
echo "────────────────────────────────────────"

# ── Path Lists ────────────────────────────────────────────────────

PATHS_COMMON=(
  "/.env" "/.env.local" "/.env.production" "/.env.backup"
  "/.git/HEAD" "/.git/config"
  "/backup.zip" "/backup.tar.gz" "/dump.sql" "/db.sql"
  "/robots.txt" "/sitemap.xml" "/.htaccess"
  "/phpinfo.php" "/info.php" "/test.php" "/crossdomain.xml"
  "/config.py" "/config.php" "/configuration.php"
  "/.well-known/security.txt"
  "/.dockerenv"
  "/package.json" "/composer.json" "/Gemfile"
  "/web.config"
)

PATHS_WORDPRESS=(
  "/wp-admin" "/wp-admin/"
  "/wp-admin/install.php" "/wp-admin/install.php?step=1"
  "/wp-login.php" "/wp-config.php" "/wp-config.php.bak"
  "/wp-content/" "/wp-content/plugins/" "/wp-content/themes/" "/wp-content/uploads/"
  "/wp-includes/" "/xmlrpc.php" "/wp-cron.php"
  "/wp-json/" "/wp-json/wp/v2/users"
  "/?author=1" "/feed/"
  "/readme.html" "/license.txt" "/wp-links-opml.php"
)

PATHS_DJANGO=(
  "/admin" "/admin/" "/admin/login/"
  "/django-admin" "/django-admin/"
  "/api" "/api/" "/api/v1/" "/api/v2/"
  "/api/schema/" "/api/docs/"
  "/swagger/" "/swagger-ui/" "/redoc/"
  "/openapi.json" "/schema.json"
  "/static/" "/media/"
  "/db.sqlite3" "/database.sqlite3"
  "/settings.py" "/local_settings.py" "/secrets.py"
  "/__debug__/" "/silk/"
  "/api/token/" "/api/token/refresh/" "/accounts/login/"
)

PATHS_LARAVEL=(
  "/storage/logs/laravel.log" "/public/storage/"
  "/api/user" "/telescope" "/horizon"
  "/log-viewer" "/_debugbar/" "/artisan"
  "/login" "/logout" "/register"
)

PATHS_RAILS=(
  "/rails/info" "/rails/info/properties"
  "/rails/mailers" "/cable"
  "/sidekiq" "/delayed_job"
  "/users/sign_in" "/users/sign_out"
)

PATHS_GENERIC=(
  "/administrator/" "/admin" "/admin/"
  "/login/" "/user/login" "/panel/" "/dashboard/"
  "/phpmyadmin/" "/pma/" "/server-status" "/server-info"
)

# ── Results Storage ───────────────────────────────────────────────
declare -a R_PATH R_RAW R_FINAL R_NOTE
declare -a SEC_CHECKS      # "CATEGORY|ITEM|STATUS|SEVERITY|DETAIL"
declare -a API_CONTENT
declare -a VERSIONS_FOUND

# Finding record: CATEGORY|ITEM|STATUS|SEVERITY|CLASS|SCORED|DETAIL
# CLASS: ACTION | VERIFY | EXPECTED | INFO
# SCORED: yes | no (only ACTION findings with scored=yes affect hygiene score)

add_check() {
  local category="$1" item="$2" check_status="$3" severity="$4" detail="$5"
  local class="${6:-ACTION}" scored="${7:-yes}"
  case "$check_status" in
    OK|PROTECTED*|REJECTED|SUPPORTED|PRESENT|SECURE|OFF|NONE_FOUND)
      class="INFO"; scored="no"; severity="OK"
      ;;
  esac
  SEC_CHECKS+=("${category}|${item}|${check_status}|${severity}|${class}|${scored}|${detail}")
}

parse_check() {
  local check="$1"
  PC_CAT="${check%%|*}"; local r="${check#*|}"
  PC_ITEM="${r%%|*}"; r="${r#*|}"
  PC_STATUS="${r%%|*}"; r="${r#*|}"
  PC_SEV="${r%%|*}"; r="${r#*|}"
  PC_CLASS="${r%%|*}"; r="${r#*|}"
  PC_SCORED="${r%%|*}"; PC_DETAIL="${r#*|}"
}

is_public_by_design() {
  case "$1" in
    /robots.txt|/sitemap.xml|/feed/|/.well-known/security.txt) return 0 ;;
  esac
  return 1
}

is_login_surface() {
  local p="$1" fw="${FRAMEWORK:-unknown}"
  case "$p" in
    /admin|/admin/|/admin/login/)        [[ "$fw" == django ]] && return 0 ;;
    /wp-login.php|/wp-admin|/wp-admin/)  [[ "$fw" == wordpress ]] && return 0 ;;
    /login|/login/)                      [[ "$fw" == laravel ]] && return 0 ;;
    /users/sign_in)                      [[ "$fw" == rails ]] && return 0 ;;
    /login/|/administrator/)             return 0 ;;
  esac
  return 1
}

is_sensitive_path() {
  case "$1" in
    /.env|/.env.local|/.env.production|/.env.backup \
    |/.git/HEAD|/.git/config \
    |/backup.zip|/backup.tar.gz|/dump.sql|/db.sql \
    |/wp-config.php|/wp-config.php.bak \
    |/config.py|/config.php|/configuration.php \
    |/settings.py|/local_settings.py|/secrets.py \
    |/db.sqlite3|/database.sqlite3 \
    |/storage/logs/laravel.log|/phpinfo.php|/info.php|/test.php)
      return 0 ;;
  esac
  return 1
}

is_config_expected_path() {
  local p="$1" ep
  for ep in "${CONFIG_EXPECTED_OPEN[@]}"; do
    [[ "$ep" == "$p" ]] && return 0
  done
  return 1
}

is_app_surface() {
  local p="$1" ep
  for ep in "${CONFIG_APP_SURFACE[@]}"; do
    [[ "$ep" == "$p" ]] && return 0
  done
  return 1
}

is_expected_open() {
  is_public_by_design "$1" && return 0
  is_login_surface "$1" && return 0
  is_config_expected_path "$1" && return 0
  return 1
}

url_host_port() {
  # Sets URL_HOST and URL_PORT from TARGET_URL
  local u="${TARGET_URL#*://}"
  u="${u%%/*}"
  if [[ "$u" == *:* ]]; then
    URL_HOST="${u%%:*}"
    URL_PORT="${u#*:}"
  else
    URL_HOST="$u"
    URL_PORT="443"
  fi
}

is_unexpected_exposure() {
  local path="$1" note="$2"
  [[ "$note" != "OPEN" && "$note" != SERVER_ERROR* ]] && return 1
  is_expected_open "$path" && return 1
  is_sensitive_path "$path" && return 0
  # Unknown 200s are verify-only, not scored exposure
  [[ "$note" == "OPEN" ]] && return 0
  return 1
}

is_scored_exposure() {
  local path="$1" note="$2"
  [[ "$note" != "OPEN" && "$note" != SERVER_ERROR* ]] && return 1
  is_sensitive_path "$path" && return 0
  return 1
}

declare -A SEEN_URL_SLUGS
declare -a SESSION_AUDIT_RECORDS   # "url|slug|txt|json|html"

url_to_slug() {
  local u="${1%/}"
  u=${u#*://}
  u=${u%%/*}
  u=${u%%:*}
  u=${u//[^a-zA-Z0-9._-]/_}
  [[ -z "$u" ]] && u="unknown_host"
  printf '%s' "$u"
}

setup_url_logs() {
  local url="$1"
  local slug base n
  slug=$(url_to_slug "$url")
  if [[ -n "${SEEN_URL_SLUGS[$slug]:-}" ]]; then
    n=$((${SEEN_URL_SLUGS[$slug]} + 1))
    SEEN_URL_SLUGS[$slug]=$n
    slug="${slug}_${n}"
  else
    SEEN_URL_SLUGS[$slug]=1
  fi
  URL_SLUG="$slug"
  URL_LOG_DIR="${RUN_SESSION_DIR}/${URL_SLUG}"
  "$MKDIR" -p "$URL_LOG_DIR"
  base="audit_${URL_SLUG}_${RUN_DATE}_${RUN_TIMESTAMP}"
  LOG_TXT="${URL_LOG_DIR}/${base}.txt"
  LOG_JSON="${URL_LOG_DIR}/${base}.json"
  LOG_HTML="${URL_LOG_DIR}/${base}.html"
}

reset_audit_state() {
  R_PATH=(); R_RAW=(); R_FINAL=(); R_NOTE=()
  SEC_CHECKS=(); API_CONTENT=(); VERSIONS_FOUND=()
  SERVER_HEADER="" POWERED_BY="" CDN_DETECTED="" LANGUAGE_DETECTED=""
  FRAMEWORK_CONFIDENCE="" FRAMEWORK_SIGNALS="" FRAMEWORK="" EFFECTIVE_UA=""
  CACHED_HEADERS=""
  ARTIFACT_ROBOTS_RAW=""
  ARTIFACT_ROBOTS_DISALLOW=(); ARTIFACT_ROBOTS_ALLOW=(); ARTIFACT_ROBOTS_SITEMAPS=()
  ARTIFACT_SECURITY_TXT=""
  ARTIFACT_SITEMAP_RAW=""
  ARTIFACT_SITEMAP_LOCS=()
  ARTIFACT_REDIRECT_CHAIN=""
  ARTIFACT_HSTS_DETAIL=""
  ARTIFACT_CSP_DETAIL=""
  ARTIFACT_CORS_NOTES=()
  DESIGNER_NAME=""
  DESIGNER_SOURCE=""
  DESIGNER_LINK=""
  DESIGNER_CREDIBLE=0
  DESIGNER_HAS_PROPER=0
  DESIGNER_HAS_RISK=0
  DESIGNER_HEADER_STATUS=""
  DESIGNER_DISCOVERED_PATH=""
  DESIGNER_TRACE=()
  ARTIFACT_DESIGNER_SUMMARY=""
  MISC_URLS=()
  MISC_IMAGES=()
  MISC_URL_COUNT=0
  MISC_PROBE_URL_COUNT=0
  MISC_INTERNAL_URL_COUNT=0
  MISC_IMAGE_COUNT=0
  MISC_PAGES_SCANNED=0
  CACHED_HOME_HTML=""
  COMPARE_BASELINE_LABEL=""
  COMPARE_HYGIENE_DELTA=0
  COMPARE_EXPOSURE_DELTA=0
  COMPARE_PREV_HYGIENE=""
  COMPARE_PREV_EXPOSURE=""
  COMPARE_NEW_ACTIONS=()
}

system_info_txt() {
  cat <<EOF
 Audit Host   : $SYS_HOST
 Architecture : $SYS_ARCH
 OS           : $SYS_OS_FULL
 Kernel       : $SYS_KERNEL ($SYS_OS)
 Shell        : $SYS_SHELL
 System       : $SYS_UNAME
 Run Date     : $RUN_DATE
 Run Time     : $RUN_TIME
 Session Dir  : $RUN_SESSION_DIR
EOF
}

report_attribution_txt() {
  local when="${1:-}"
  local year=$("$DATE" +%Y)
  echo ""
  echo "────────────────────────────────────────"
  echo " Generated by ${BRAND_VENDOR} — Web Security Audit Tool v${TOOL_VERSION}${when:+ — $when}"
  echo " App     : ${BRAND_APP}"
  echo " GitHub  : ${BRAND_GITHUB}"
  echo " © ${year} ${BRAND_VENDOR}. All rights reserved."
  echo ""
  echo " This report is for authorized security assessment only."
  echo " Share with your web developer or hosting provider to address findings."
  echo "────────────────────────────────────────"
}

json_generator_block() {
  local year=$("$DATE" +%Y)
  echo "  \"generator\": {"
  echo "    \"vendor\": \"$(json_escape_str "$BRAND_VENDOR")\","
  echo "    \"tool\": \"Web Security Audit Tool\","
  echo "    \"version\": \"${TOOL_VERSION}\","
  echo "    \"app\": \"$(json_escape_str "$BRAND_APP")\","
  echo "    \"github\": \"$(json_escape_str "$BRAND_GITHUB")\","
  echo "    \"copyright\": \"© ${year} $(json_escape_str "$BRAND_VENDOR"). All rights reserved.\""
  echo "  }"
}

color_echo() {
  # Portable replacement for zsh print -P
  [[ "${QUIET:-0}" -eq 1 ]] && return 0
  printf '%b\n' "$1"
}

log_msg() {
  [[ "${QUIET:-0}" -eq 1 ]] && return 0
  printf '%s\n' "$*"
}

log_err() {
  printf '%s\n' "$*" >&2
}

# ── Per-site auto config (site_configs/<host>.conf) ───────────────

site_config_path_for() {
  printf '%s/%s.conf' "$SITE_CONFIG_DIR" "$(url_to_slug "$1")"
}

is_interactive_site_config() {
  [[ "${QUIET:-0}" -eq 1 ]] && return 1
  [[ "${NO_SITE_CONFIG:-0}" -eq 1 ]] && return 1
  [[ "${AUDIT_CONFIG_EXPLICIT:-0}" -eq 1 ]] && return 1
  [[ -t 0 ]] && return 0
  return 1
}

is_discoverable_path() {
  local p="$1"
  [[ -z "$p" || "$p" == "/" ]] && return 1
  echo "$p" | grep -qiE '\.(css|js|jpe?g|png|gif|webp|svg|ico|woff2?|ttf|eot|map|pdf|zip|tar|gz|mp4|webm)$' && return 1
  echo "$p" | grep -qiE '^/(wp-content/uploads|wp-includes/js|wp-includes/css|static/admin|_next/static|cdn-cgi/)' && return 1
  [[ ${#p} -gt 120 ]] && return 1
  return 0
}

url_to_site_path() {
  local u="$1" base="$2" path
  path="${u#"$base"}"
  path="${path%%\?*}"
  path="${path%%#*}"
  [[ -z "$path" ]] && path="/"
  [[ "$path" != /* ]] && path="/${path}"
  printf '%s' "$path"
}

discover_register_path() {
  local path="$1" source="${2:-link}" existing
  path=$(printf '%s' "$path" | sed 's/\+$//')
  [[ "$path" != */ ]] && path="${path}/"
  is_discoverable_path "$path" || return 0
  for existing in "${DISCOVERED_PATHS[@]}"; do
    [[ "$existing" == "$path" ]] && return 0
  done
  DISCOVERED_PATHS+=("$path")
  case "$source" in
    sitemap) DISCOVERED_FROM_SITEMAP+=("$path") ;;
    *)       DISCOVERED_FROM_LINKS+=("$path") ;;
  esac
}

discover_try_sitemap() {
  local url="$1" ua="$2" sm_url="$3" thost="$4" sm_body link_host path loc
  [[ "$("$CURL" -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" -A "$ua" "$sm_url" 2>/dev/null)" != "200" ]] && return 1
  sm_body=$("$CURL" -s -L --max-time "$TIMEOUT" -A "$ua" "$sm_url" 2>/dev/null | head -c 24000)
  while IFS= read -r loc; do
    [[ -z "$loc" ]] && continue
    link_host=$(printf '%s' "$loc" | sed -E 's|^https?://||; s|/.*||')
    [[ "$link_host" != "$thost" ]] && continue
    path=$(url_to_site_path "$loc" "${url%/}")
    discover_register_path "$path" "sitemap"
    [[ ${#DISCOVERED_PATHS[@]} -ge 40 ]] && break
  done < <(echo "$sm_body" | grep -oiE '<loc[^>]*>[^<]+</loc>' | sed 's/<[^>]*>//g' | head -50)
}

discover_site_paths() {
  local url="$1" ua="${EFFECTIVE_UA:-curl/8.7.1}"
  local html sm_body href abs link_host path target_host

  DISCOVERED_PATHS=()
  DISCOVERED_FROM_LINKS=()
  DISCOVERED_FROM_SITEMAP=()
  target_host=$(printf '%s' "$url" | "$SED" -E 's|^https?://||; s|/.*||')

  html=$("$CURL" -s -L --max-time "$TIMEOUT" -A "$ua" "$url" 2>/dev/null || true)
  html="${html:0:$MISC_HTML_MAX}"
  while IFS= read -r href; do
    [[ -z "$href" ]] && continue
    abs=$(absolutize_url "$url" "$href") || continue
    link_host=$(printf '%s' "$abs" | "$SED" -E 's|^https?://||; s|/.*||')
    [[ "$link_host" != "$target_host" ]] && continue
    path=$(url_to_site_path "$abs" "${url%/}")
    discover_register_path "$path" "link"
  done < <(printf '%s' "$html" | "$GREP" -oiE '<a[^>]+href=["'\''][^"'\'']+["'\'']' | "$SED" -E 's/.*href=["'\'']([^"'\'']+)["'\''].*/\1/I' | "$HEAD" -100)

  discover_try_sitemap "$url" "$ua" "${url%/}/sitemap.xml" "$target_host"
  discover_try_sitemap "$url" "$ua" "${url%/}/sitemap_index.xml" "$target_host"
  discover_try_sitemap "$url" "$ua" "${url%/}/wp-sitemap.xml" "$target_host"
}

write_site_config_header() {
  local url="$1" cfg_path="$2" fw_hint="$3" slug="$4" cfg_display="$2"
  local created_local created_utc n_links n_smap
  [[ "$cfg_path" == "${SCRIPT_DIR}/"* ]] && cfg_display="${cfg_path#${SCRIPT_DIR}/}"
  created_local=$("$DATE" +"%Y-%m-%d %H:%M:%S")
  created_utc=$("$DATE" -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || "$DATE" +"%Y-%m-%dT%H:%M:%SZ")
  n_links=${#DISCOVERED_FROM_LINKS[@]}
  n_smap=${#DISCOVERED_FROM_SITEMAP[@]}

  echo "# ============================================================================="
  echo "# AUTO-GENERATED SITE CONFIG"
  echo "# ============================================================================="
  echo "#"
  echo "# What           : Per-site overrides for web_audit.sh (security hygiene audit)"
  echo "# For URL         : ${url}"
  echo "# Host slug       : ${slug}"
  echo "# Config file     : ${cfg_path}"
  echo "#"
  echo "# Generated by    : web_audit.sh v${TOOL_VERSION}"
  echo "# Generated on    : ${created_local} (local audit host clock)"
  echo "# Generated UTC   : ${created_utc}"
  echo "# Framework hint  : ${fw_hint}  (from --framework; edit or re-run with -f if wrong)"
  echo "# Discovery run   : ${n_links} path(s) from homepage HTML links"
  echo "#                   ${n_smap} path(s) from sitemap.xml / sitemap_index / wp-sitemap"
  echo "#"
  echo "# HOW THIS CONFIG HELPS (vs audit with NO site config)"
  echo "#   Built-in-only run probes generic paths (.env, /wp-admin/, etc.) — not your"
  echo "#   marketing pages, portfolio routes, or custom /app/ surfaces."
  echo "#   When you enable this file (interactive Y, or --config, or site_configs auto-load):"
  echo "#     [paths] extra=       Extra GET probes on YOUR routes + misc URL/image sampling"
  echo "#                          (up to ${MISC_SCAN_MAX_PAGES} pages; Internal report tag site_config)"
  echo "#     [expected_open]      Intentional public 200s — Exposure score won't penalize them"
  echo "#     [rate_limit_post]    Optional POST brute-force checks on APIs/forms you list"
  echo "#     [misc]               Optional: show/cap URL lists; HTML scan bytes for links/images"
  echo "#     Path table           Fewer REVIEW rows for routes you mark as expected"
  echo "#"
  echo "# HOW TO EDIT"
  echo "#   Active   : lines like extra=/about/ or /about/=public_seo (no # prefix)"
  echo "#   Disabled : lines starting with # — remove # to enable that option"
  echo "#   Regenerate: delete this file and run web_audit interactively on the same URL"
  echo "#"
  if [[ $((n_links + n_smap)) -eq 0 ]]; then
    echo "# DISCOVERY NOTE: No same-origin page paths were found automatically."
    echo "#   Common on JS-heavy sites (React/Vue) or when curl is blocked/challenged."
    echo "#   Add routes manually below (copy from browser nav, sitemap, or Search Console)."
    echo "#"
  fi
  echo "# More reference : README.md · run_notes.md · site.conf.template"
  echo "# ============================================================================="
  echo ""
}

write_site_config_stub() {
  local url="$1" cfg_path="$2" fw_hint="${3:-auto}" slug created path i n_active n_total
  local -a active_paths=() commented_paths=()
  slug=$(url_to_slug "$url")
  n_total=${#DISCOVERED_PATHS[@]}
  for (( i=0; i<n_total; i++ )); do
    if [[ $i -lt $CONFIG_GEN_ACTIVE_MAX ]]; then
      active_paths+=("${DISCOVERED_PATHS[$i]}")
    else
      commented_paths+=("${DISCOVERED_PATHS[$i]}")
    fi
  done
  n_active=${#active_paths[@]}

  {
    write_site_config_header "$url" "$cfg_path" "$fw_hint" "$slug"

    echo "# -----------------------------------------------------------------------------"
    echo "# [paths] — Extra GET probes + misc page/image sampling (max ${MISC_SCAN_MAX_PAGES} pages)"
    echo "# -----------------------------------------------------------------------------"
    echo "[paths]"
    echo ""

    if [[ $n_active -gt 0 ]]; then
      echo "# --- Discovered on this site (ENABLED — comment out to disable) ---"
      for path in "${active_paths[@]}"; do
        echo "extra=${path}"
      done
      echo ""
    fi

    if [[ ${#commented_paths[@]} -gt 0 ]]; then
      echo "# --- Discovered on this site (disabled — remove # to enable) ---"
      for path in "${commented_paths[@]}"; do
        echo "# extra=${path}"
      done
      echo ""
    fi

    if [[ $n_total -eq 0 ]]; then
      echo "# --- No paths auto-discovered — add your public routes below ---"
      echo "# extra=/design-ideas/"
      echo "# extra=/about/"
      echo "# extra=/contact/"
      echo ""
    fi

    echo "# --- Common probes (any stack — uncomment as needed) ---"
    echo "# extra=/.well-known/security.txt"
    echo "# extra=/humans.txt"
    echo "# extra=/ads.txt"
    echo "# extra=/favicon.ico"
    echo "# extra=/apple-touch-icon.png"
    echo "# extra=/site.webmanifest"
    echo "# extra=/llms.txt"
    echo "# extra=/ai.txt"
    echo "# extra=/health"
    echo "# extra=/healthz"
    echo ""

    echo "# --- SEO / sitemap variants ---"
    echo "# extra=/sitemap_index.xml"
    echo "# extra=/sitemap-index.xml"
    echo "# extra=/post-sitemap.xml"
    echo "# extra=/page-sitemap.xml"
    echo ""

    case "$fw_hint" in
      django)
        echo "# --- Django (built-in also probes /admin/login/, /api/, /static/, …) ---"
        echo "# extra=/app/"
        echo "# extra=/portal/"
        echo "# extra=/tests/"
        echo "# extra=/api/status/"
        echo "# extra=/contact/"
        ;;
      wordpress)
        echo "# --- WordPress (built-in also probes /wp-admin/, /wp-json/, …) ---"
        echo "# extra=/wp-sitemap.xml"
        echo "# extra=/wp-sitemap-pages-1.xml"
        echo "# extra=/wp-sitemap-posts-post-1.xml"
        echo "# extra=/feed/"
        ;;
      laravel)
        echo "# --- Laravel ---"
        echo "# extra=/horizon"
        echo "# extra=/telescope"
        echo "# extra=/log-viewer"
        ;;
      rails)
        echo "# --- Rails ---"
        echo "# extra=/rails/info"
        echo "# extra=/sidekiq"
        echo "# extra=/cable"
        ;;
      *)
        echo "# --- Generic / unknown stack ---"
        echo "# extra=/admin/"
        echo "# extra=/login/"
        ;;
    esac
    echo ""

    echo "# -----------------------------------------------------------------------------"
    echo "# [expected_open] — Intentional public 200s (Exposure score ignores these)"
    echo "# Labels: public_seo | app_surface | login_surface | staging | internal"
    echo "# -----------------------------------------------------------------------------"
    echo "[expected_open]"
    echo ""

    if [[ $n_active -gt 0 ]]; then
      echo "# --- Matches ENABLED paths above ---"
      for path in "${active_paths[@]}"; do
        echo "${path}=public_seo"
      done
      echo ""
    fi

    if [[ ${#commented_paths[@]} -gt 0 ]]; then
      echo "# --- Matches disabled paths above (uncomment together with extra=) ---"
      for path in "${commented_paths[@]}"; do
        echo "# ${path}=public_seo"
      done
      echo ""
    fi

    if [[ $n_total -eq 0 ]]; then
      echo "# --- Examples when discovery is empty (uncomment with matching extra=) ---"
      echo "# /design-ideas/=public_seo"
      echo "# /about/=public_seo"
      echo ""
    fi

    echo "# --- Other labels (examples) ---"
    echo "# /app/=app_surface"
    echo "# /portal/=app_surface"
    echo "# /panel/login/=login_surface"
    echo "# /__debug__/=staging"
    echo ""

    echo "# -----------------------------------------------------------------------------"
    echo "# [misc] — Miscellaneous report: URL list display (optional)"
    echo "#   show_probe_urls=yes|no     Show security probe URL list in HTML report"
    echo "#   show_internal_urls=yes|no  Show internal site URL list in HTML report"
    echo "#   max_probe_urls=N           Cap probe URLs shown in HTML (default 250)"
    echo "#   max_internal_urls=N        Cap internal URLs shown in HTML (default 250)"
    echo "#   max_html_bytes=N           Link scan window per page (default 65536)"
    echo "#   max_html_img_bytes=N       Image scan window per page (default 98304)"
    echo "# [paths] extra= routes appear as site_config under Internal (not security_probe)."
    echo "# -----------------------------------------------------------------------------"
    echo "[misc]"
    echo "# show_probe_urls=yes"
    echo "# show_internal_urls=yes"
    echo "# max_probe_urls=250"
    echo "# max_internal_urls=250"
    echo ""

    echo "# -----------------------------------------------------------------------------"
    echo "# [rate_limit_post] — Extra POST brute-force probes (15 invalid POSTs each)"
    echo "# Types: json | django_admin | wordpress | laravel | rails | form"
    echo "# Default framework login is always tested — lines below are optional extras"
    echo "# -----------------------------------------------------------------------------"
    echo "[rate_limit_post]"
    echo ""

    case "$fw_hint" in
      django)
        echo "# /api/chat/=json"
        echo "# /api/token/=json"
        echo "# /api/contact/=json"
        echo "# /contact/=form"
        ;;
      wordpress)
        echo "# /xmlrpc.php=form"
        echo "# /wp-comments-post.php=form"
        echo "# /wp-json/wp/v2/comments=form"
        ;;
      laravel)
        echo "# /api/user=json"
        echo "# /api/login=json"
        echo "# /contact=form"
        ;;
      rails)
        echo "# /api/v1/auth=json"
        echo "# /contact=form"
        ;;
      *)
        echo "# /api/login/=json"
        echo "# /api/v1/auth/=json"
        echo "# /contact/=form"
        ;;
    esac
    echo ""
    echo "# Framework login (already probed without config):"
    case "$fw_hint" in
      django)    echo "#   /admin/login/  (django_admin)" ;;
      wordpress) echo "#   /wp-login.php  (wordpress)" ;;
      laravel)   echo "#   /login         (laravel)" ;;
      rails)     echo "#   /users/sign_in (rails)" ;;
      *)         echo "#   /login/        (form)" ;;
    esac
    echo ""

  } > "$cfg_path"
}

prompt_yes_no() {
  local prompt="$1" default="${2:-Y}" answer="" prompt_text
  if [[ "$default" == "Y" || "$default" == "y" ]]; then
    prompt_text="${prompt} [Y/n]: "
  else
    prompt_text="${prompt} [y/N]: "
  fi
  while true; do
    printf '%b' "${CYN}${prompt_text}${RST}"
    read -r answer || answer=""
    answer=$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')
    if [[ -z "$answer" ]]; then
      answer=$(printf '%s' "$default" | tr '[:upper:]' '[:lower:]')
    fi
    case "$answer" in
      y|yes) return 0 ;;
      n|no) return 1 ;;
      *) color_echo "${YLW}  Please enter y or n.${RST}" ;;
    esac
  done
}

show_site_config_banner() {
  local title="$1" cfg_path="$2" url="$3" created=""
  [[ -f "$cfg_path" ]] && {
    if [[ "$SYS_OS" == "Darwin" ]]; then
      created=$(stat -f "%Sm" -t "%Y-%m-%d" "$cfg_path" 2>/dev/null || echo "")
    else
      created=$("$DATE" -r "$cfg_path" +"%Y-%m-%d" 2>/dev/null || echo "")
    fi
  }
  color_echo ""
  color_echo "${CYN}╔══════════════════════════════════════════════════════════════╗${RST}"
  color_echo "${CYN}║${RST}  ${title}"
  color_echo "${CYN}╚══════════════════════════════════════════════════════════════╝${RST}"
  color_echo ""
  color_echo "  ${BLU}Site${RST}        : ${url}"
  color_echo "  ${MGN}Config file${RST} : ${cfg_path}"
  [[ -n "$created" && "$created" != "unknown" ]] && color_echo "  ${BLU}Modified${RST}    : ${created}"
  color_echo ""
}

explain_config_vs_baseline() {
  local url="$1" cfg_path="$2" slug path i max=6
  slug=$(url_to_slug "$url")
  color_echo "${GRN}  With this config (vs built-in run with no config):${RST}"
  color_echo ""
  if [[ ${#CONFIG_EXTRA_PATHS[@]} -gt 0 ]]; then
    color_echo "  ${GRN}✓${RST} Extra GET probes     : ${#CONFIG_EXTRA_PATHS[@]} path(s) — also sampled for misc URLs/images"
    for (( i=0; i<${#CONFIG_EXTRA_PATHS[@]} && i<max; i++ )); do
      color_echo "      ${BLU}•${RST} ${CONFIG_EXTRA_PATHS[$i]}"
    done
    [[ ${#CONFIG_EXTRA_PATHS[@]} -gt $max ]] && color_echo "      ${BLU}…${RST} and $((${#CONFIG_EXTRA_PATHS[@]} - max)) more"
  else
    color_echo "  ${YLW}○${RST} Extra GET probes     : none (add ${BLU}extra=/path/${RST} under [paths])"
  fi
  if [[ ${#CONFIG_EXPECTED_OPEN[@]} -gt 0 ]]; then
    color_echo "  ${GRN}✓${RST} Expected-open marks  : ${#CONFIG_EXPECTED_OPEN[@]} path(s) — intentional 200s won't lower Exposure"
  else
    color_echo "  ${YLW}○${RST} Expected-open marks  : none"
  fi
  if [[ ${#CONFIG_RATE_LIMIT_POST[@]} -gt 0 ]]; then
    color_echo "  ${GRN}✓${RST} POST rate-limit      : ${#CONFIG_RATE_LIMIT_POST[@]} extra target(s)"
    for rp in "${CONFIG_RATE_LIMIT_POST[@]}"; do
      color_echo "      ${BLU}•${RST} ${rp%%|*}"
    done
  else
    color_echo "  ${YLW}○${RST} POST rate-limit      : login only (add paths under [rate_limit_post] to probe APIs)"
  fi
  color_echo "  ${GRN}✓${RST} Fewer REVIEW rows    : public pages classified instead of unknown 200s"
  color_echo ""
  color_echo "${YLW}  NOTE:${RST} Edit anytime — ${MGN}${cfg_path}${RST}"
  color_echo "${YLW}  NOTE:${RST} Full reference — ${BLU}site.conf.template${RST} · ${BLU}run_notes.md${RST} (With config vs without)"
  color_echo ""
}

resolve_config_for_target() {
  local url="$1" cfg_path answer cfg_quiet="${QUIET:-0}"
  reset_config_state
  TARGET_AUDIT_CONFIG=""

  if [[ -n "$AUDIT_CONFIG" ]]; then
    load_audit_config "$AUDIT_CONFIG" "$cfg_quiet"
    TARGET_AUDIT_CONFIG="$AUDIT_CONFIG"
    return 0
  fi

  cfg_path=$(site_config_path_for "$url")

  if [[ "${DRY_RUN:-0}" -eq 1 ]]; then
    if [[ -f "$cfg_path" ]]; then
      load_audit_config "$cfg_path" "$cfg_quiet"
      TARGET_AUDIT_CONFIG="$cfg_path"
      log_msg "Site config (dry-run): $cfg_path"
    fi
    return 0
  fi

  if ! is_interactive_site_config; then
    if [[ -f "$cfg_path" ]]; then
      load_audit_config "$cfg_path" "$cfg_quiet"
      TARGET_AUDIT_CONFIG="$cfg_path"
      log_msg "Site config: $cfg_path"
    fi
    return 0
  fi

  if [[ -f "$cfg_path" ]]; then
    show_site_config_banner "Site config found for $(url_to_slug "$url")" "$cfg_path" "$url"
    if prompt_yes_no "Use this config for this run?" "Y"; then
      load_audit_config "$cfg_path" 1
      explain_config_vs_baseline "$url" "$cfg_path"
      TARGET_AUDIT_CONFIG="$cfg_path"
    else
      color_echo "${CYN}  Continuing without site config (built-in probes only).${RST}"
      color_echo ""
    fi
    return 0
  fi

  color_echo ""
  color_echo "${CYN}No site config yet for $(url_to_slug "$url") — scanning homepage + sitemap…${RST}\n"
  discover_site_paths "$url"
  write_site_config_stub "$url" "$cfg_path" "${FORCE_FRAMEWORK:-auto}"
  show_site_config_banner "Created site config for $(url_to_slug "$url")" "$cfg_path" "$url"
  if [[ ${#DISCOVERED_PATHS[@]} -gt 0 ]]; then
    local _en=${#DISCOVERED_PATHS[@]}
    [[ $_en -gt $CONFIG_GEN_ACTIVE_MAX ]] && _en=$CONFIG_GEN_ACTIVE_MAX
    color_echo "  ${GRN}Pre-filled${RST} ${#DISCOVERED_PATHS[@]} path(s) (${_en} enabled, rest commented in file)."
  else
    color_echo "  ${YLW}No paths auto-detected${RST} — edit the file and add ${BLU}extra=/your-path/${RST} lines."
  fi
  color_echo ""
  if prompt_yes_no "Use this new config for this run?" "Y"; then
    load_audit_config "$cfg_path" 1
    explain_config_vs_baseline "$url" "$cfg_path"
    TARGET_AUDIT_CONFIG="$cfg_path"
  else
    color_echo "${CYN}  Continuing without site config. Saved for a future run:${RST}"
    color_echo "  ${MGN}${cfg_path}${RST}"
    color_echo ""
  fi
}

json_score_field() {
  local file="$1" key="$2"
  grep -o "\"${key}\": [0-9]*" "$file" 2>/dev/null | head -1 | awk '{print $2}'
}

resolve_redirect_url() {
  local base="$1" loc="$2"
  loc=$(printf '%s' "$loc" | tr -d '\r\n' | sed 's/^[Ll]ocation:[[:space:]]*//')
  [[ -z "$loc" ]] && return 1
  if [[ "$loc" == http://* || "$loc" == https://* ]]; then
    printf '%s' "$loc"
  elif [[ "$loc" == //* ]]; then
    printf '%s:%s' "${base%%://*}:" "$loc"
  elif [[ "$loc" == /* ]]; then
    printf '%s%s' "${base%/}" "$loc"
  else
    printf '%s/%s' "${base%/}" "$loc"
  fi
}

probe_throttle_sleep() {
  [[ "${PROBE_THROTTLE_MS:-0}" -le 0 ]] && return 0
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import time; time.sleep(${PROBE_THROTTLE_MS}/1000.0)" 2>/dev/null
  elif [[ "$PROBE_THROTTLE_MS" -ge 1000 ]]; then
    sleep $((PROBE_THROTTLE_MS / 1000))
  else
    sleep 1
  fi
}

html_escape() {
  local s="$1"
  s=${s//&/&amp;}
  s=${s//</&lt;}
  s=${s//>/&gt;}
  s=${s//\"/&quot;}
  printf '%s' "$s"
}

json_escape_str() {
  local s="$1"
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\n'/\\n}
  s=${s//$'\r'/\\r}
  printf '%s' "$s"
}

get_remediation() {
  local category="$1" item="$2" sev="$3" detail="$4"
  local fw="${FRAMEWORK:-unknown}"
  case "$category|$item" in
    "HEADERS|Strict-Transport-Security")
      if [[ "$fw" == django ]]; then
        printf '%s' "Enable HSTS at Cloudflare (SSL/TLS → Edge Certificates) or set SECURE_PROXY_SSL_HEADER so Django SecurityMiddleware can emit HSTS behind the load balancer."
      else
        printf '%s' "Enable HTTPS-only access. In Cloudflare: SSL/TLS → Edge Certificates → enable HSTS. Or add the header in your web server config."
      fi ;;
    "HEADERS|Content-Security-Policy")
      printf '%s' "Add a Content-Security-Policy header to control which scripts and resources can load. Start with a report-only policy, then enforce. Cloudflare Transform Rules or framework middleware can help." ;;
    "HEADERS|X-Frame-Options")
      printf '%s' "Add X-Frame-Options: SAMEORIGIN (or CSP frame-ancestors) to prevent clickjacking via iframe embedding." ;;
    "HEADERS|X-Content-Type-Options")
      printf '%s' "Add X-Content-Type-Options: nosniff to stop browsers from guessing file types incorrectly." ;;
    "HEADERS|Referrer-Policy")
      printf '%s' "Add Referrer-Policy: strict-origin-when-cross-origin to limit information sent to third-party sites." ;;
    "HEADERS|Permissions-Policy")
      printf '%s' "Add a Permissions-Policy header to restrict access to camera, microphone, and geolocation APIs." ;;
    COOKIES|csrftoken)
      printf '%s' "Django intentionally omits HttpOnly on csrftoken so JavaScript can read it for AJAX CSRF — this is expected, not a vulnerability." ;;
    COOKIES|XSRF-TOKEN)
      printf '%s' "Laravel XSRF-TOKEN is intentionally readable by JavaScript for CSRF protection — expected behavior." ;;
    COOKIES|*)
      case "$fw" in
        django)
          printf '%s' "Ensure sessionid has Secure, HttpOnly, and SameSite. csrftoken may omit HttpOnly by design." ;;
        laravel)
          printf '%s' "Ensure laravel_session has Secure, HttpOnly, and SameSite. XSRF-TOKEN may omit HttpOnly by design." ;;
        rails)
          printf '%s' "Ensure _session_id has Secure, HttpOnly, and SameSite on all session cookies." ;;
        wordpress)
          printf '%s' "Set Secure, HttpOnly, and SameSite on WordPress auth cookies via wp-config.php or a security plugin." ;;
        *)
          printf '%s' "Set Secure, HttpOnly, and SameSite flags on session and auth cookies." ;;
      esac ;;
    RATE_LIMIT|*)
      case "$fw" in
        django)
          printf '%s' "Add login rate limiting on /admin/login/ POST: Cloudflare rate rule, django-axes, or fail2ban." ;;
        wordpress)
          printf '%s' "Add login rate limiting: Cloudflare rule on /wp-login.php POST, Wordfence, or Limit Login Attempts." ;;
        laravel)
          printf '%s' "Enable Laravel throttle middleware on /login POST or add a CDN/WAF rate limit rule." ;;
        rails)
          printf '%s' "Add Rack::Attack or a CDN rate limit on /users/sign_in POST." ;;
        *)
          printf '%s' "Add login rate limiting via CDN/WAF rules or server-side throttling on authentication POST endpoints." ;;
      esac ;;
    "API_CONTENT|/wp-json/wp/v2/users")
      printf '%s' "Disable public user listing. Block /wp-json/wp/v2/users for unauthenticated visitors." ;;
    WORDPRESS|/?author=1*)
      printf '%s' "Block author enumeration. Redirect /?author= requests to homepage, or disable author archives." ;;
    "WORDPRESS|/wp-cron.php")
      printf '%s' "Disable public wp-cron: add define('DISABLE_WP_CRON', true) to wp-config.php and schedule cron via server crontab." ;;
    "VERSION|/readme.html")
      printf '%s' "Block access to readme.html via web server rules or Cloudflare WAF — it reveals WordPress version." ;;
    "VERSION|/license.txt")
      printf '%s' "Block public access to license.txt — it confirms WordPress is installed." ;;
    VERSION|Generator*)
      printf '%s' "Remove the WordPress version from the HTML generator tag via theme functions or SEO plugin." ;;
    VERSION|*)
      printf '%s' "Hide software version information. Update dependencies and remove version strings from headers and public files." ;;
    DIR_LISTING|*)
      printf '%s' "Disable directory listing on the web server. Apache: Options -Indexes; nginx: ensure autoindex is off." ;;
    "DIR_LISTING|HTML_DOCUMENT")
      printf '%s' "An open directory-style URL is serving a full HTML page. Confirm it is intentional (e.g. default index file). Remove or restrict access to leftover templates or uploads if not needed publicly." ;;
    TLS|TLS\ 1.3)
      printf '%s' "Verify TLS 1.3 support with SSL Labs or browser DevTools — curl probes often fail even when 1.3 is enabled at the CDN." ;;
    TLS|TLS*)
      printf '%s' "Disable deprecated TLS versions on your server or CDN. Only TLS 1.2 and 1.3 should be accepted." ;;
    OPEN_REDIRECT|*)
      printf '%s' "Validate all redirect URLs against an allowlist. Never redirect to external domains from user-supplied parameters." ;;
    PLUGIN_VERSION|*)
      printf '%s' "Block direct access to plugin readme.txt files. Keep plugins updated — check wpscan.com for known vulnerabilities." ;;
    "GENERAL|security.txt")
      printf '%s' "Create a /.well-known/security.txt file with your security contact email, as recommended by RFC 9116." ;;
    "ATTRIBUTION|Name in <title>")
      printf '%s' "Remove the designer name from <title> on public pages — titles should reflect your brand and page topic, not the template author." ;;
    "ATTRIBUTION|Name in meta tags")
      printf '%s' "Set meta author/description/OG fields to your business or page content. Designer credit belongs in a footer or HTML comment, not indexed metadata." ;;
    "ATTRIBUTION|Hidden placement")
      printf '%s' "Remove designer credits hidden with CSS (display:none). Search engines may treat this as cloaking or low-quality hidden text." ;;
    "ATTRIBUTION|Designer credit link")
      printf '%s' "Fix or remove the broken designer portfolio link, or add rel=\"nofollow noopener\" if you keep a working credit link." ;;
    "ATTRIBUTION|Comment-only credit"|"ATTRIBUTION|HTML comment credit")
      printf '%s' "No action needed — HTML comment credits are invisible to search engines. Respectful attribution for developers who built the site well." ;;
    "ATTRIBUTION|Designer credit (proper)")
      printf '%s' "Credit is in an acceptable location — keep HTML-comment or visible footer attribution; avoid moving the name into <title>, meta tags, or hidden CSS." ;;
    "ATTRIBUTION|Designer / creator credit")
      printf '%s' "Optional: add a Designed by / Created by credit in an HTML comment after DOCTYPE or in the site footer if you want attribution recorded in future audits." ;;
    "ATTRIBUTION|Credit off homepage")
      printf '%s' "Designer credit was found on a non-homepage URL. No change required for attribution — confirm that path should remain publicly reachable." ;;
    ATTRIBUTION|*)
      printf '%s' "Review where the designer/creator name appears. Footer or HTML-comment credits are fine; avoid polluting title, meta, or hidden text." ;;
    DJANGO|DEBUG\ mode)
      printf '%s' "Set DEBUG=False in production Django settings and use proper logging for errors." ;;
    *)
      case "$sev" in
        CRITICAL) printf '%s' "Address immediately — this exposes sensitive data or enables direct attacks. Consult your developer or hosting provider." ;;
        HIGH)     printf '%s' "Fix soon — this increases attack risk. Review with your web administrator." ;;
        MEDIUM)   printf '%s' "Schedule a fix — this weakens your security posture over time." ;;
        LOW)      printf '%s' "Improve when convenient — low immediate risk but good security hygiene." ;;
        INFO)     printf '%s' "Informational — no urgent action required." ;;
        *)        printf '%s' "Review this finding with your technical team." ;;
      esac
      ;;
  esac
}

severity_color() {
  case "$1" in
    CRITICAL) printf "${RED}CRITICAL${RST}" ;;
    HIGH)     printf "${RED}HIGH    ${RST}" ;;
    MEDIUM)   printf "${YLW}MEDIUM  ${RST}" ;;
    LOW)      printf "${BLU}LOW     ${RST}" ;;
    INFO)     printf "${CYN}INFO    ${RST}" ;;
    OK)       printf "${GRN}OK      ${RST}" ;;
    *)        printf "%-8s" "$1"            ;;
  esac
}

# ── Framework Detection ───────────────────────────────────────────
SERVER_HEADER="" POWERED_BY="" CDN_DETECTED="" LANGUAGE_DETECTED=""
FRAMEWORK_CONFIDENCE="" FRAMEWORK_SIGNALS="" FRAMEWORK="" EFFECTIVE_UA=""

detect_framework() {
  local url="$1"
  local headers body cookies

  local probe_ua="curl/8.7.1"
  local probe_code
  probe_code=$($CURL -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -A "$probe_ua" "$url" 2>/dev/null)

  if [[ "$probe_code" == "415" || "$probe_code" == "403" || -z "$probe_code" ]]; then
    probe_ua="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    probe_code=$($CURL -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -A "$probe_ua" "$url" 2>/dev/null)
  fi

  EFFECTIVE_UA="$probe_ua"

  if [[ "$probe_code" == "415" || -z "$probe_code" ]]; then
    CDN_DETECTED="unknown"; LANGUAGE_DETECTED="unknown"
    FRAMEWORK_CONFIDENCE="none"; FRAMEWORK_SIGNALS="blocked"
    FRAMEWORK="blocked"; return
  fi

  headers=$($CURL -sI -L --max-time $TIMEOUT -A "$probe_ua" "$url" 2>/dev/null)
  body=$(  $CURL -s  -L --max-time $TIMEOUT -A "$probe_ua" "$url" 2>/dev/null | head -c 8000)
  cookies=$($CURL -s -L --max-time $TIMEOUT -A "$probe_ua" -c - -o /dev/null "$url" 2>/dev/null)

  SERVER_HEADER=$(echo "$headers" | grep -i "^server:"       | tail -1 | tr -d '\r\n' | sed 's/^[Ss]erver: //')
  POWERED_BY=$(   echo "$headers" | grep -i "^x-powered-by:" | tail -1 | tr -d '\r\n' | sed 's/^[Xx]-[Pp]owered-[Bb]y: //')

  local cdn="none"
  if   echo "$headers" | grep -qi "^cf-ray:\|^cf-cache-status:"; then cdn="Cloudflare"
  elif echo "$headers" | grep -qi "^x-amz-\|^x-amzn-";          then cdn="AWS CloudFront"
  elif echo "$headers" | grep -qi "^x-fastly-\|^fastly-";        then cdn="Fastly"
  elif echo "$headers" | grep -qi "^x-akamai-\|^akamai-";        then cdn="Akamai"
  elif echo "$headers" | grep -qi "via:.*varnish";               then cdn="Varnish"
  fi
  CDN_DETECTED="$cdn"

  local lang="unknown"
  if   echo "$POWERED_BY" | grep -qi "php";                                          then lang="PHP"
  elif echo "$headers"    | grep -qi "set-cookie:.*JSESSIONID\|x-powered-by:.*java"; then lang="Java"
  elif echo "$headers"    | grep -qi "x-powered-by:.*express\|x-powered-by:.*node";  then lang="Node.js"
  elif echo "$headers"    | grep -qi "x-powered-by:.*asp.net\|x-aspnet";             then lang="ASP.NET"
  elif echo "$headers"    | grep -qi "x-powered-by:.*ruby\|x-rack";                  then lang="Ruby"
  fi
  LANGUAGE_DETECTED="$lang"

  local django_score=0 wp_score=0 laravel_score=0 rails_score=0
  local signals_d="" signals_w="" signals_l="" signals_r=""

  echo "$cookies" | grep -qi "csrftoken"            && { django_score=$((django_score+3)); signals_d+="csrftoken "; }
  echo "$cookies" | grep -qi "sessionid"            && { django_score=$((django_score+2)); signals_d+="sessionid "; }
  echo "$body"    | grep -qi "csrfmiddlewaretoken"  && { django_score=$((django_score+3)); signals_d+="csrfmiddlewaretoken "; }
  echo "$body"    | grep -qi "django"               && { django_score=$((django_score+2)); signals_d+="django-body "; }
  echo "$headers" | grep -qi "django"               && { django_score=$((django_score+2)); signals_d+="django-header "; }
  local admin_body
  admin_body=$($CURL -s -L --max-time $TIMEOUT -A "$probe_ua" "${url%/}/admin/" 2>/dev/null | head -c 2000)
  echo "$admin_body" | grep -qi "django administration\|id_username\|grp-" && { django_score=$((django_score+3)); signals_d+="django-admin "; }

  echo "$body"    | grep -qi "wp-content\|wp-includes" && { wp_score=$((wp_score+3)); signals_w+="wp-content "; }
  echo "$body"    | grep -qi "wordpress\|wp-json"       && { wp_score=$((wp_score+2)); signals_w+="wordpress-body "; }
  echo "$cookies" | grep -qi "wordpress_\|wp-settings"  && { wp_score=$((wp_score+3)); signals_w+="wp-cookies "; }
  echo "$headers" | grep -qi "x-powered-by:.*wordpress" && { wp_score=$((wp_score+3)); signals_w+="wp-header "; }

  echo "$cookies" | grep -qi "laravel_session\|XSRF-TOKEN" && { laravel_score=$((laravel_score+3)); signals_l+="laravel-session "; }
  echo "$body"    | grep -qi "laravel\|illuminate"          && { laravel_score=$((laravel_score+2)); signals_l+="laravel-body "; }
  echo "$headers" | grep -qi "laravel"                      && { laravel_score=$((laravel_score+2)); signals_l+="laravel-header "; }

  echo "$headers" | grep -qi "x-runtime:\|x-request-id:" && { rails_score=$((rails_score+2)); signals_r+="rails-headers "; }
  echo "$cookies" | grep -qi "_session_id\|_rails"         && { rails_score=$((rails_score+2)); signals_r+="rails-cookies "; }
  echo "$body"    | grep -qi "authenticity_token"           && { rails_score=$((rails_score+3)); signals_r+="authenticity_token "; }

  local detected="unknown"; local max_score=0
  FRAMEWORK_SIGNALS="no signals"

  if [[ $django_score  -gt $max_score ]]; then max_score=$django_score;  detected="django";    FRAMEWORK_SIGNALS="${signals_d:-none}"; [[ "$LANGUAGE_DETECTED" == "unknown" ]] && LANGUAGE_DETECTED="Python"; fi
  if [[ $wp_score      -gt $max_score ]]; then max_score=$wp_score;      detected="wordpress"; FRAMEWORK_SIGNALS="${signals_w:-none}"; [[ "$LANGUAGE_DETECTED" == "unknown" ]] && LANGUAGE_DETECTED="PHP";    fi
  if [[ $laravel_score -gt $max_score ]]; then max_score=$laravel_score; detected="laravel";   FRAMEWORK_SIGNALS="${signals_l:-none}"; [[ "$LANGUAGE_DETECTED" == "unknown" ]] && LANGUAGE_DETECTED="PHP";    fi
  if [[ $rails_score   -gt $max_score ]]; then max_score=$rails_score;   detected="rails";     FRAMEWORK_SIGNALS="${signals_r:-none}"; [[ "$LANGUAGE_DETECTED" == "unknown" ]] && LANGUAGE_DETECTED="Ruby";   fi

  if   [[ $max_score -ge 6 ]]; then FRAMEWORK_CONFIDENCE="high"
  elif [[ $max_score -ge 3 ]]; then FRAMEWORK_CONFIDENCE="medium"
  elif [[ $max_score -ge 1 ]]; then FRAMEWORK_CONFIDENCE="low"
  else                               FRAMEWORK_CONFIDENCE="none"; fi

  if [[ "$detected" == "unknown" ]] && echo "$POWERED_BY" | grep -qi "php"; then
    detected="php_generic"; FRAMEWORK_CONFIDENCE="medium"
    FRAMEWORK_SIGNALS="x-powered-by:php"; LANGUAGE_DETECTED="PHP"
  fi

  FRAMEWORK="$detected"
}

# ── Path Probe ────────────────────────────────────────────────────

PROBE_STATUS_WIDTH=16

_status_plain() {
  local code="$1"
  case "$code" in
    200)                 printf "%-${PROBE_STATUS_WIDTH}s" "200 OPEN" ;;
    301|302|303|307|308) printf "%-${PROBE_STATUS_WIDTH}s" "${code} REDIRECT" ;;
    401)                 printf "%-${PROBE_STATUS_WIDTH}s" "401 Auth" ;;
    403)                 printf "%-${PROBE_STATUS_WIDTH}s" "403 Forbidden" ;;
    404)                 printf "%-${PROBE_STATUS_WIDTH}s" "404 Not Found" ;;
    429)                 printf "%-${PROBE_STATUS_WIDTH}s" "429 Rate Limit" ;;
    500|502|503)         printf "%-${PROBE_STATUS_WIDTH}s" "${code} Server Err" ;;
    520|521|522|524)     printf "%-${PROBE_STATUS_WIDTH}s" "${code} CF-Block" ;;
    ""|000)              printf "%-${PROBE_STATUS_WIDTH}s" "No Response" ;;
    *)                   printf "%-${PROBE_STATUS_WIDTH}s" "$code" ;;
  esac
}

_status_colored() {
  local code="$1" plain
  plain="$(_status_plain "$code")"
  case "$code" in
    200)                 printf "${RED}%s${RST}" "$plain" ;;
    301|302|303|307|308) printf "${YLW}%s${RST}" "$plain" ;;
    401)                 printf "${GRN}%s${RST}" "$plain" ;;
    403)                 printf "${GRN}%s${RST}" "$plain" ;;
    404)                 printf "${BLU}%s${RST}" "$plain" ;;
    429)                 printf "${MGN}%s${RST}" "$plain" ;;
    500|502|503)         printf "${RED}%s${RST}" "$plain" ;;
    520|521|522|524)     printf "${YLW}%s${RST}" "$plain" ;;
    ""|000)              printf "${YLW}%s${RST}" "$plain" ;;
    *)                   printf "%s" "$plain" ;;
  esac
}

probe_path() {
  local url_path="$1"
  if [[ "${DRY_RUN:-0}" -eq 1 ]]; then
    R_PATH+=("$url_path"); R_RAW+=("-"); R_FINAL+=("-"); R_NOTE+=("DRY_RUN")
    return 0
  fi
  local full_url="${TARGET_URL}${url_path}"
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"

  local raw_code final_code
  raw_code=$($CURL -s -o /dev/null -w "%{http_code}" \
    --max-time $TIMEOUT -A "$ua" \
    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
    -H "Accept-Language: en-US,en;q=0.5" -H "Connection: keep-alive" \
    "$full_url" 2>/dev/null)

  final_code=$($CURL -s -o /dev/null -w "%{http_code}" \
    -L --max-time $TIMEOUT -A "$ua" \
    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
    -H "Accept-Language: en-US,en;q=0.5" -H "Connection: keep-alive" \
    "$full_url" 2>/dev/null)

  local note sep
  case "$final_code" in
    200)                 note="OPEN"               ;;
    301|302|303|307|308) note="REDIRECT"           ;;
    401)                 note="PROTECTED_401"      ;;
    403)                 note="PROTECTED_403"      ;;
    404)                 note="NOT_FOUND"          ;;
    429)                 note="RATE_LIMITED"       ;;
    500|502|503)         note="SERVER_ERROR"       ;;
    520|521|522|524)     note="CF_BLOCKED"        ;;
    ""|000)              note="NO_RESPONSE"        ;;
    *)                   note="OTHER_${final_code}" ;;
  esac

  if [[ "$raw_code" == "$final_code" ]]; then
    sep="   "
  else
    sep=" → "
  fi

  [[ "${QUIET:-0}" -eq 1 ]] && return 0
  printf "  %-42s [raw: %b]%s[final: %b]\n" \
    "$url_path" "$(_status_colored "$raw_code")" "$sep" "$(_status_colored "$final_code")"

  R_PATH+=("$url_path"); R_RAW+=("$raw_code"); R_FINAL+=("$final_code"); R_NOTE+=("$note")
  probe_throttle_sleep
}

# ── Enhanced checks (artifacts, policies, transport) ────────────────

robots_path_disallowed() {
  local path="$1" rule
  for rule in "${ARTIFACT_ROBOTS_DISALLOW[@]}"; do
    [[ -z "$rule" || "$rule" == "/" ]] && continue
    if [[ "$rule" == "$path" || "$path" == "$rule"* ]]; then
      for rule in "${ARTIFACT_ROBOTS_ALLOW[@]}"; do
        [[ "$path" == "$rule"* ]] && return 1
      done
      return 0
    fi
  done
  return 1
}

parse_robots_txt() {
  local body="$1" line val lower
  ARTIFACT_ROBOTS_DISALLOW=(); ARTIFACT_ROBOTS_ALLOW=(); ARTIFACT_ROBOTS_SITEMAPS=()
  while IFS= read -r line || [[ -n "$line" ]]; do
    line=$(printf '%s' "$line" | sed 's/#.*//;s/^[[:space:]]*//;s/[[:space:]]*$//')
    [[ -z "$line" ]] && continue
    lower=$(printf '%s' "$line" | tr '[:upper:]' '[:lower:]')
    case "$lower" in
      disallow:*)
        val=$(printf '%s' "${line#*:}" | sed 's/^[[:space:]]*//')
        [[ -n "$val" ]] && ARTIFACT_ROBOTS_DISALLOW+=("$val")
        ;;
      allow:*)
        val=$(printf '%s' "${line#*:}" | sed 's/^[[:space:]]*//')
        [[ -n "$val" ]] && ARTIFACT_ROBOTS_ALLOW+=("$val")
        ;;
      sitemap:*)
        val=$(printf '%s' "${line#*:}" | sed 's/^[[:space:]]*//')
        [[ -n "$val" ]] && ARTIFACT_ROBOTS_SITEMAPS+=("$val")
        ;;
    esac
  done <<< "$body"
}

parse_security_txt() {
  local body="$1" line key val
  local expires="" contact="" policy="" canonical=""
  while IFS= read -r line || [[ -n "$line" ]]; do
    line=$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [[ -z "$line" || "$line" == \#* ]] && continue
    key="${line%%:*}"; val="${line#*:}"; val=$(printf '%s' "$val" | sed 's/^[[:space:]]*//')
    case "$(printf '%s' "$key" | tr '[:upper:]' '[:lower:]')" in
      expires)   expires="$val" ;;
      contact)   contact="$val" ;;
      policy)    policy="$val" ;;
      canonical) canonical="$val" ;;
    esac
  done <<< "$body"
  ARTIFACT_SECURITY_TXT="Expires: ${expires:-n/a}\nContact: ${contact:-n/a}\nPolicy: ${policy:-n/a}\nCanonical: ${canonical:-n/a}"
  if [[ -n "$expires" ]]; then
    local exp_epoch now_epoch days_left
    exp_epoch=$("$DATE" -j -f "%Y-%m-%d" "$expires" +%s 2>/dev/null || "$DATE" -d "$expires" +%s 2>/dev/null || echo 0)
    now_epoch=$("$DATE" +%s)
    if [[ "$exp_epoch" -gt 0 ]]; then
      days_left=$(( (exp_epoch - now_epoch) / 86400 ))
      if [[ $days_left -lt 0 ]]; then
        add_check "ARTIFACTS" "security.txt Expires" "STALE" "MEDIUM" "security.txt Expires date is in the past ($expires)" "ACTION" "yes"
      elif [[ $days_left -lt 30 ]]; then
        add_check "ARTIFACTS" "security.txt Expires" "EXPIRING" "LOW" "security.txt expires in ${days_left}d ($expires)" "INFO" "no"
      else
        add_check "ARTIFACTS" "security.txt Expires" "OK" "OK" "Valid until $expires (~${days_left}d)"
      fi
    fi
  fi
  [[ -z "$contact" ]] && add_check "ARTIFACTS" "security.txt Contact" "MISSING" "LOW" "No Contact: field in security.txt" "INFO" "no"
}

check_policy_parse() {
  local hsts csp val maxage
  hsts=$(echo "$CACHED_HEADERS" | grep -i "^Strict-Transport-Security:" | tail -1 | tr -d '\r\n' | sed 's/^[Ss]trict-[Tt]ransport-[Ss]ecurity:[[:space:]]*//')
  if [[ -n "$hsts" ]]; then
    ARTIFACT_HSTS_DETAIL="$hsts"
    maxage=$(echo "$hsts" | grep -oiE 'max-age=[0-9]+' | head -1 | cut -d= -f2)
    val="max-age=${maxage:-unknown}"
    echo "$hsts" | grep -qi 'includesubdomains' && val+=", includeSubDomains"
    echo "$hsts" | grep -qi 'preload' && val+=", preload"
    ARTIFACT_HSTS_DETAIL="$val (raw: ${hsts:0:120})"
    if [[ -n "$maxage" && "$maxage" -lt 15552000 ]]; then
      add_check "POLICY" "HSTS max-age" "SHORT" "MEDIUM" "HSTS max-age=${maxage}s (< 180 days) — consider ≥ 31536000 for preload eligibility" "ACTION" "yes"
    else
      add_check "POLICY" "HSTS max-age" "OK" "OK" "HSTS max-age=${maxage:-unknown}"
    fi
    echo "$hsts" | grep -qi 'includesubdomains' \
      || add_check "POLICY" "HSTS includeSubDomains" "MISSING" "LOW" "HSTS present but includeSubDomains not set" "INFO" "no"
  fi

  csp=$(echo "$CACHED_HEADERS" | grep -i "^Content-Security-Policy:" | tail -1 | tr -d '\r\n' | sed 's/^[Cc]ontent-[Ss]ecurity-[Pp]olicy:[[:space:]]*//')
  if [[ -n "$csp" ]]; then
    ARTIFACT_CSP_DETAIL="${csp:0:500}"
    echo "$csp" | grep -qi 'unsafe-inline' \
      && add_check "POLICY" "CSP unsafe-inline" "PRESENT" "MEDIUM" "CSP allows unsafe-inline — weakens XSS protection" "ACTION" "yes"
    echo "$csp" | grep -qi 'unsafe-eval' \
      && add_check "POLICY" "CSP unsafe-eval" "PRESENT" "MEDIUM" "CSP allows unsafe-eval" "ACTION" "yes"
    echo "$csp" | grep -qE '(script-src|default-src)[^;]*\*' \
      && add_check "POLICY" "CSP wildcard" "PRESENT" "HIGH" "CSP uses wildcard (*) in script-src or default-src" "ACTION" "yes"
    echo "$csp" | grep -qi 'unsafe-inline\|unsafe-eval\|\*' \
      || add_check "POLICY" "CSP review" "OK" "OK" "No obvious unsafe-inline/eval/wildcard patterns detected"
  fi
}

check_redirect_chain() {
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"
  local url="$TARGET_URL" hops=0 chain="" code loc next
  while [[ $hops -lt 12 ]]; do
    code=$($CURL -sI -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -A "$ua" "$url" 2>/dev/null)
    loc=$($CURL -sI --max-time $TIMEOUT -A "$ua" "$url" 2>/dev/null | grep -i "^Location:" | tail -1 | tr -d '\r\n')
    chain+="${code} ${url}"
    case "$code" in
      301|302|303|307|308)
        [[ -z "$loc" ]] && break
        next=$(resolve_redirect_url "$url" "$loc")
        [[ -z "$next" || "$next" == "$url" ]] && break
        chain+=" → "
        url="$next"
        hops=$((hops + 1))
        ;;
      *) break ;;
    esac
  done
  [[ $hops -gt 0 ]] && chain+=" → ${code} ${url}"
  ARTIFACT_REDIRECT_CHAIN="$chain"

  if [[ "$TARGET_URL" == https://* ]]; then
    local http_url="${TARGET_URL/https:\/\//http:\/\/}"
    local http_code
    http_code=$($CURL -sI -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -A "$ua" "$http_url" 2>/dev/null)
    case "$http_code" in
      200)
        add_check "TRANSPORT" "HTTP cleartext" "OPEN" "HIGH" "HTTP version returns 200 without redirecting to HTTPS" "ACTION" "yes" ;;
      301|302|303|307|308)
        add_check "TRANSPORT" "HTTP cleartext" "REDIRECTS" "OK" "HTTP redirects (${http_code}) — good" ;;
      *)
        add_check "TRANSPORT" "HTTP cleartext" "OTHER" "INFO" "HTTP probe returned ${http_code}" "INFO" "no" ;;
    esac
  fi

  if [[ $hops -ge 5 ]]; then
    add_check "TRANSPORT" "Redirect chain" "LONG" "LOW" "${hops} redirects before final response — review chain length" "INFO" "no"
  elif [[ $hops -gt 0 ]]; then
    add_check "TRANSPORT" "Redirect chain" "OK" "OK" "${hops} redirect(s) — final URL reachable"
  else
    add_check "TRANSPORT" "Redirect chain" "NONE" "OK" "No redirects on canonical URL"
  fi
}

check_artifacts() {
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"
  local robots_code robots_body sec_body sm_code sm_body loc

  robots_code=$($CURL -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/robots.txt" 2>/dev/null)
  if [[ "$robots_code" == "200" ]]; then
    robots_body=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/robots.txt" 2>/dev/null | head -c 12000)
    ARTIFACT_ROBOTS_RAW="$robots_body"
    parse_robots_txt "$robots_body"
    add_check "ARTIFACTS" "robots.txt" "PRESENT" "OK" "Parsed ${#ARTIFACT_ROBOTS_DISALLOW[@]} Disallow, ${#ARTIFACT_ROBOTS_ALLOW[@]} Allow, ${#ARTIFACT_ROBOTS_SITEMAPS[@]} Sitemap rule(s)"

    local i conflicts=0
    for (( i=0; i<${#R_PATH[@]}; i++ )); do
      [[ "${R_NOTE[$i]}" == "OPEN" ]] || continue
      robots_path_disallowed "${R_PATH[$i]}" || continue
      is_expected_open "${R_PATH[$i]}" && continue
      conflicts=$((conflicts + 1))
      add_check "ARTIFACTS" "robots vs probe ${R_PATH[$i]}" "CONFLICT" "MEDIUM" "Path returns 200 but is Disallow'd in robots.txt — crawlers may still find it; consider 401/403 or robots update" "VERIFY" "no"
    done
    [[ $conflicts -eq 0 && ${#ARTIFACT_ROBOTS_DISALLOW[@]} -gt 0 ]] \
      && add_check "ARTIFACTS" "robots.txt cross-check" "OK" "OK" "No probed OPEN paths conflict with Disallow rules"
  else
    add_check "ARTIFACTS" "robots.txt" "MISSING" "INFO" "robots.txt returned ${robots_code}" "INFO" "no"
  fi

  sec_body=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/.well-known/security.txt" 2>/dev/null | head -c 8000)
  if [[ -n "$sec_body" ]] && ! echo "$sec_body" | grep -qi "<html"; then
    parse_security_txt "$sec_body"
    add_check "ARTIFACTS" "security.txt parse" "PARSED" "OK" "security.txt fields extracted (see report artifacts section)"
  fi

  sm_code=$($CURL -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/sitemap.xml" 2>/dev/null)
  if [[ "$sm_code" == "200" ]]; then
    sm_body=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/sitemap.xml" 2>/dev/null | head -c 16000)
    ARTIFACT_SITEMAP_RAW="$sm_body"
    ARTIFACT_SITEMAP_LOCS=()
    while IFS= read -r loc; do
      [[ -n "$loc" ]] && ARTIFACT_SITEMAP_LOCS+=("$loc")
    done < <(echo "$sm_body" | grep -oiE '<loc[^>]*>[^<]+</loc>' | sed 's/<[^>]*>//g' | head -150)
    add_check "ARTIFACTS" "sitemap.xml" "PARSED" "OK" "Parsed ${#ARTIFACT_SITEMAP_LOCS[@]} URL(s) from sitemap.xml"
  fi
}

check_cors() {
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"
  local -a cors_paths=("/api/" "/api/v1/")
  local p ep path url headers acao acac origin="https://evil.example.com"

  for p in "${CONFIG_EXTRA_PATHS[@]}"; do
    [[ "$p" == /api/* ]] && cors_paths+=("$p")
  done

  local seen="" path
  for path in "${cors_paths[@]}"; do
    [[ " $seen " == *" $path "* ]] && continue
    seen+=" $path"
    url="${TARGET_URL}${path}"
    headers=$($CURL -sI --max-time $TIMEOUT -A "$ua" -H "Origin: ${origin}" "$url" 2>/dev/null)
    acao=$(echo "$headers" | grep -i "^Access-Control-Allow-Origin:" | tail -1 | tr -d '\r\n')
    acac=$(echo "$headers" | grep -i "^Access-Control-Allow-Credentials:" | tail -1 | tr -d '\r\n')
    [[ -z "$acao" ]] && continue
    local note="path=${path} ACAO=${acao}"
    [[ -n "$acac" ]] && note+=", ACAC=${acac}"
    ARTIFACT_CORS_NOTES+=("$note")
    if echo "$acao" | grep -qi '\*'; then
      add_check "CORS" "$path" "WILDCARD" "HIGH" "Access-Control-Allow-Origin: * on ${path}" "ACTION" "yes"
    elif echo "$acao" | grep -qi 'evil.example.com'; then
      add_check "CORS" "$path" "REFLECTED" "CRITICAL" "Origin reflected in ACAO on ${path} — credentialed CORS risk if cookies used" "ACTION" "yes"
    else
      add_check "CORS" "$path" "PRESENT" "INFO" "CORS headers present: ${acao:0:80}" "INFO" "no"
    fi
  done
  [[ ${#ARTIFACT_CORS_NOTES[@]} -eq 0 ]] && add_check "CORS" "API paths" "NONE" "OK" "No Access-Control-Allow-Origin on probed API paths"
}

check_http_methods() {
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"
  local -a paths=("$TARGET_URL")
  local path url code

  case "$FRAMEWORK" in
    django)    paths+=("${TARGET_URL}/admin/login/") ;;
    wordpress) paths+=("${TARGET_URL}/wp-login.php") ;;
    laravel)   paths+=("${TARGET_URL}/login") ;;
    rails)     paths+=("${TARGET_URL}/users/sign_in") ;;
    *)         paths+=("${TARGET_URL}/login/") ;;
  esac

  for url in "${paths[@]}"; do
    code=$($CURL -s -o /dev/null -w "%{http_code}" -X TRACE --max-time $TIMEOUT -A "$ua" "$url" 2>/dev/null)
    if [[ "$code" == "200" ]]; then
      add_check "METHODS" "TRACE ${url#$TARGET_URL}" "ENABLED" "HIGH" "TRACE method returned 200 — disable on production servers" "ACTION" "yes"
    else
      add_check "METHODS" "TRACE ${url#$TARGET_URL}" "DISABLED" "OK" "TRACE returned ${code}"
    fi
    code=$($CURL -s -o /dev/null -w "%{http_code}" -X OPTIONS --max-time $TIMEOUT -A "$ua" "$url" 2>/dev/null)
    if [[ "$code" == "200" ]]; then
      local allow
      allow=$($CURL -sI -X OPTIONS --max-time $TIMEOUT -A "$ua" "$url" 2>/dev/null | grep -i "^Allow:" | tail -1 | tr -d '\r\n')
      add_check "METHODS" "OPTIONS ${url#$TARGET_URL}" "OPEN" "INFO" "OPTIONS allowed${allow:+ — ${allow:0:80}}" "INFO" "no"
    fi
  done
}

# ── Designer / creator attribution + site misc (URLs, images) ─────

CREDIT_LABEL_RE='Designed by|Design by|Created by|Developed by|Built by|Crafted by|Theme by|Site by|Powered by|Powered with|Made by|Maintained by|Author:|Creator:|Coded by|Programmed by|Website by|Web design by|Webdesign by|Built with'

designer_name_pattern() {
  printf '%s' "$1" | sed 's/[.[\*^$]/\\&/g'
}

is_credit_noise() {
  local n="$1"
  echo "$n" | grep -qiE '^(wordpress|wp engine|shopify|wix|squarespace|weebly|elementor|divi|cloudflare|nginx|apache|php|javascript|jquery|bootstrap|google|automattic|vercel|netlify|react|vue|next\.js|laravel|django|rails|hostinger|godaddy|bluehost|siteground|webflow|framer)$'
}

sanitize_credit_name() {
  local n="$1"
  n=$(printf '%s' "$n" | sed -E 's/[[:space:]]+/ /g; s/^[[:space:][:punct:]]+//; s/[[:space:][:punct:]]+$//; s/[|<].*//; s/^(https?:\/\/|www\.).*//i')
  printf '%s' "$n"
}

designer_trim_person_name() {
  local n="$1"
  n=$(sanitize_credit_name "$n")
  # Keep person/brand name; drop job title, org, trailing clauses (e.g. "Harsh Agarwal, Senior … @ GeeksforGeeks")
  n=$(printf '%s' "$n" | sed -E \
    's/,.*//;
     s/[[:space:]]@.*//;
     s/[[:space:]]+[—–|-][[:space:]].*//;
     s/[[:space:]]+\|.*//;
     s/[[:space:]]+(Senior|Junior|Lead|Principal|Staff)[[:space:]].*//I')
  n=$(sanitize_credit_name "$n")
  printf '%s' "$n"
}

extract_credit_name_from_label() {
  local raw="$1"
  local name
  name=$(printf '%s' "$raw" | sed -E "s/.*(${CREDIT_LABEL_RE})[[:space:]]*//i; s/-->.*//; s/--.*//; s/[<|].*//")
  name=$(designer_trim_person_name "$name")
  [[ -n "$name" && ${#name} -ge 3 && ${#name} -le 60 ]] || return 1
  is_credit_noise "$name" && return 1
  printf '%s' "$name"
}

extract_designer_from_html() {
  local html="$1" scan_part raw name

  DESIGNER_SOURCE=""
  DESIGNER_NAME=""

  for scan_part in "${html:0:8000}" "${html:0:25000}"; do
    raw=$(echo "$scan_part" | tr '\n' ' ' | grep -oiE "<!--[[:space:]]*((${CREDIT_LABEL_RE})[[:print:][:space:]]{2,220})[[:space:]]*-->" | head -1)
    if [[ -n "$raw" ]]; then
      name=$(extract_credit_name_from_label "$raw") && { DESIGNER_SOURCE="html_comment"; DESIGNER_NAME="$name"; return 0; }
    fi
    raw=$(echo "$scan_part" | tr '\n' ' ' | grep -oiE "<!--[^!][^>]{0,500}(${CREDIT_LABEL_RE})[^\-]{2,220}" | head -1)
    if [[ -n "$raw" ]]; then
      name=$(extract_credit_name_from_label "$raw") && { DESIGNER_SOURCE="html_comment"; DESIGNER_NAME="$name"; return 0; }
    fi
    # Malformed comment blocks (e.g. <!--\nDesigned by X\n-- job title without -->)
    if echo "$scan_part" | grep -qiE '<!--'; then
      raw=$(echo "$scan_part" | grep -oiE "(${CREDIT_LABEL_RE})[[:space:]]+[A-Za-z][A-Za-z0-9 .'-]{2,55}" | head -1)
      if [[ -n "$raw" ]]; then
        name=$(extract_credit_name_from_label "$raw") && { DESIGNER_SOURCE="html_comment"; DESIGNER_NAME="$name"; return 0; }
      fi
    fi
  done

  name=$(echo "${html:0:25000}" | grep -oiE '<meta[^>]+name=["'\''](author|designer|creator|web_author|copyright|publisher)["'\''][^>]*content=["'\''][^"'\'']{2,80}["'\'']' | head -1 | sed -E 's/.*content=["'\'']([^"'\'']+)["'\''].*/\1/I')
  if [[ -z "$name" ]]; then
    name=$(echo "${html:0:25000}" | grep -oiE '<meta[^>]+content=["'\''][^"'\'']{2,80}["'\''][^>]+name=["'\''](author|designer|creator|publisher)["'\'']' | head -1 | sed -E 's/.*content=["'\'']([^"'\'']+)["'\''].*/\1/I')
  fi
  name=$(designer_trim_person_name "$name")
  if [[ -n "$name" && ${#name} -ge 3 && ${#name} -le 60 ]] && ! is_credit_noise "$name"; then
    DESIGNER_SOURCE="meta_tag"
    DESIGNER_NAME="$name"
    return 0
  fi

  raw=$(echo "${html:0:25000}" | tr '\n' ' ' | grep -oiE "(${CREDIT_LABEL_RE})[[:space:]]+[A-Za-z][A-Za-z0-9 .'\''&-]{2,55}" | head -1)
  if [[ -n "$raw" ]]; then
    name=$(extract_credit_name_from_label "$raw") && { DESIGNER_SOURCE="visible_text"; DESIGNER_NAME="$name"; return 0; }
  fi

  DESIGNER_NAME=""
  return 1
}

body_is_directory_listing() {
  echo "$1" | grep -qiE 'index of|directory listing|parent directory'
}

body_is_html_document() {
  echo "$1" | grep -qiE '<!DOCTYPE[[:space:]]+html|<html[[:space:>]'
}

path_is_site_root() {
  [[ "$1" == "/" || -z "$1" ]]
}

designer_open_path_candidates() {
  local -A seen=()
  local -a out=()
  local i path

  for (( i=0; i<${#R_PATH[@]}; i++ )); do
    [[ "${R_NOTE[$i]}" == "OPEN" ]] || continue
    path="${R_PATH[$i]}"
    [[ "$path" == */ ]] || continue
    path_is_site_root "$path" && continue
    [[ -n "${seen[$path]:-}" ]] && continue
    out+=("$path")
    seen[$path]=1
  done
  for path in "${CONFIG_EXTRA_PATHS[@]}"; do
    [[ "$path" == */ ]] || continue
    path_is_site_root "$path" && continue
    [[ -n "${seen[$path]:-}" ]] && continue
    out+=("$path")
    seen[$path]=1
  done
  printf '%s\n' "${out[@]}"
}

discover_designer_from_open_paths() {
  local ua="$1" path chunk tries=0 max_tries=8
  local -a candidates=()

  while IFS= read -r path; do
    [[ -n "$path" ]] && candidates+=("$path")
  done < <(designer_open_path_candidates)

  for path in "${candidates[@]}"; do
    [[ $tries -ge $max_tries ]] && break
    chunk=$($CURL -s -L --max-time "$TIMEOUT" -A "$ua" "${TARGET_URL%/}${path}" 2>/dev/null | head -c 8000)
    tries=$((tries + 1))
    [[ -z "$chunk" ]] && continue
    extract_designer_from_html "$chunk" && [[ -n "$DESIGNER_NAME" ]] && {
      DESIGNER_DISCOVERED_PATH="$path"
      return 0
    }
  done
  return 1
}

absolutize_url() {
  local base="$1" ref="$2"
  ref=$(printf '%s' "$ref" | "$SED" 's/^[[:space:]]*//; s/[[:space:]]*$//')
  [[ -z "$ref" || "$ref" == \#* ]] && return 1
  echo "$ref" | "$GREP" -qiE '^(javascript|mailto|tel|data):' && return 1
  [[ "$ref" == http://* || "$ref" == https://* ]] && { printf '%s' "$ref"; return 0; }
  [[ "$ref" == //* ]] && { printf '%s' "${base%%://*}:$ref"; return 0; }
  [[ "$ref" == /* ]] && { printf '%s%s' "${base%/}" "$ref"; return 0; }
  printf '%s/%s' "${base%/}" "$ref"
}

misc_source_is_probe() {
  [[ "$1" == "security_probe" ]]
}

misc_path_is_config_extra() {
  local probe_path="$1" cfg p probe_norm cfg_norm
  [[ ${#CONFIG_EXTRA_PATHS[@]} -eq 0 ]] && return 1
  probe_norm="${probe_path%/}"
  [[ "$probe_norm" != /* ]] && probe_norm="/${probe_norm}"
  for p in "${CONFIG_EXTRA_PATHS[@]}"; do
    cfg_norm="${p%/}"
    [[ "$cfg_norm" != /* ]] && cfg_norm="/${cfg_norm}"
    [[ "$probe_norm" == "$cfg_norm" ]] && return 0
  done
  return 1
}

misc_recount_url_buckets() {
  MISC_PROBE_URL_COUNT=0
  MISC_INTERNAL_URL_COUNT=0
  for entry in "${MISC_URLS[@]}"; do
    if misc_source_is_probe "${entry#*|}"; then
      MISC_PROBE_URL_COUNT=$((MISC_PROBE_URL_COUNT + 1))
    else
      MISC_INTERNAL_URL_COUNT=$((MISC_INTERNAL_URL_COUNT + 1))
    fi
  done
}

misc_register_url() {
  local url="$1" source="$2" entry idx=0 existing_src
  [[ -z "$url" ]] && return 0
  if [[ "$source" == "security_probe" ]]; then
    for entry in "${MISC_URLS[@]}"; do
      [[ "${entry%%|*}" == "$url" ]] && return 0
    done
    MISC_URLS+=("${url}|${source}")
  else
    for entry in "${MISC_URLS[@]}"; do
      if [[ "${entry%%|*}" == "$url" ]]; then
        existing_src="${entry#*|}"
        if [[ "$existing_src" == "security_probe" ]]; then
          MISC_URLS[$idx]="${url}|${source}"
        fi
        MISC_URL_COUNT=${#MISC_URLS[@]}
        return 0
      fi
      idx=$((idx + 1))
    done
    MISC_URLS+=("${url}|${source}")
  fi
  MISC_URL_COUNT=${#MISC_URLS[@]}
}

misc_register_image() {
  local img="$1" page="$2" entry
  [[ -z "$img" ]] && return 0
  for entry in "${MISC_IMAGES[@]}"; do
    [[ "${entry%%|*}" == "$img" ]] && return 0
  done
  MISC_IMAGES+=("${img}|${page}")
  MISC_IMAGE_COUNT=${#MISC_IMAGES[@]}
}

collect_urls_from_html() {
  local base_url="$1" html="$2" source="$3"
  local href abs target_host link_host html_scan="${html:0:$MISC_HTML_MAX}"

  target_host=$(printf '%s' "$base_url" | "$SED" -E 's|^https?://||; s|/.*||')
  while IFS= read -r href; do
    [[ -z "$href" ]] && continue
    abs=$(absolutize_url "$base_url" "$href") || continue
    link_host=$(printf '%s' "$abs" | "$SED" -E 's|^https?://||; s|/.*||')
    [[ "$link_host" == "$target_host" ]] && misc_register_url "$abs" "$source"
  done < <(printf '%s' "$html_scan" | "$GREP" -oiE '<a[^>]+href=["'\''][^"'\'']+["'\'']' | "$SED" -E 's/.*href=["'\'']([^"'\'']+)["'\''].*/\1/I' | "$HEAD" -80)
}

collect_images_from_html() {
  local base_url="$1" html="$2" page_path="$3"
  local src abs part item html_scan="${html:0:$MISC_HTML_IMG_MAX}"

  while IFS= read -r src; do
    [[ -z "$src" ]] && continue
    abs=$(absolutize_url "$base_url" "$src") || continue
    misc_register_image "$abs" "$page_path"
  done < <(printf '%s' "$html_scan" | "$GREP" -oiE '<img[^>]+src=["'\''][^"'\'']+["'\'']' | "$SED" -E 's/.*src=["'\'']([^"'\'']+)["'\''].*/\1/I' | "$HEAD" -60)

  while IFS= read -r part; do
    [[ -z "$part" ]] && continue
    for item in ${part//,/ }; do
      src="${item%% *}"
      src=$(printf '%s' "$src" | "$SED" 's/^[[:space:]]*//; s/[[:space:]]*$//')
      [[ -z "$src" ]] && continue
      abs=$(absolutize_url "$base_url" "$src") || continue
      misc_register_image "$abs" "$page_path"
    done
  done < <(printf '%s' "$html_scan" | "$GREP" -oiE '<img[^>]+srcset=["'\''][^"'\'']+["'\'']' | "$SED" -E 's/.*srcset=["'\'']([^"'\'']+)["'\''].*/\1/I' | "$HEAD" -20)
}

scan_designer_on_page() {
  local url="$1" html="$2" name="$3"
  local chunk="${html:0:$MISC_HTML_MAX}" path name_pat link

  path="${url#$TARGET_URL}"
  [[ -z "$path" ]] && path="/"
  name_pat=$(designer_name_pattern "$name")

  if echo "$chunk" | grep -qiE "<!--[^>]{0,600}${name_pat}"; then
    DESIGNER_TRACE+=("${path}|html_comment|none|HTML comment — not indexed by search engines")
  fi
  if echo "$chunk" | grep -qiE "<title[^>]*>[^<]*${name_pat}"; then
    DESIGNER_TRACE+=("${path}|title_tag|high|<title> contains designer name — dilutes brand SEO")
  fi
  if echo "$chunk" | grep -qiE "<meta[^>]+name=[\"'](author|description|og:title|og:description|twitter:title|twitter:description)[\"'][^>]+content=[\"'][^\"']*${name_pat}"; then
    DESIGNER_TRACE+=("${path}|meta_tag|medium|Indexed meta tag contains designer name")
  fi
  if echo "$chunk" | grep -qi 'application/ld+json' && echo "$chunk" | grep -qiE '"@type"[[:space:]]*:[[:space:]]*"(Person|Organization|WebSite|WebPage)"[^}]{0,1200}'"${name_pat}"; then
    DESIGNER_TRACE+=("${path}|json_ld|medium|JSON-LD structured data references designer")
  fi
  if echo "$chunk" | grep -qiE 'display:[[:space:]]*none[^>]{0,200}'"${name_pat}"'|'"${name_pat}"'[^<]{0,160}display:[[:space:]]*none'; then
    DESIGNER_TRACE+=("${path}|hidden_css|high|Name near display:none — review hidden-text risk")
  fi
  link=$(echo "$chunk" | grep -oiE '<a[^>]+href=["'\'']([^"'\'']+)["'\''][^>]*>[^<]{0,120}'"${name_pat}" | head -1 | sed -E 's/.*href=["'\'']([^"'\'']+)["'\''].*/\1/I')
  if [[ -n "$link" ]]; then
    DESIGNER_TRACE+=("${path}|footer_link|low|Visible linked designer credit")
    [[ -z "$DESIGNER_LINK" ]] && DESIGNER_LINK="$link"
  elif echo "$chunk" | tr '\n' ' ' | grep -qiE "(${CREDIT_LABEL_RE})[^<]{0,60}${name_pat}"; then
    if ! echo "$chunk" | head -c 10000 | grep -qiE "<!--[^>]*${name_pat}"; then
      DESIGNER_TRACE+=("${path}|visible_text|low|Visible on-page designer credit")
    fi
  fi
}

check_site_miscellaneous() {
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"
  local html name url loc target_host chunk loc_host path i
  local comment_pages=0 title_pages=0 meta_pages=0 hidden_pages=0 link_pages=0
  local -a scan_urls=()
  local -A seen_scan_urls

  DESIGNER_NAME=""
  DESIGNER_SOURCE=""
  DESIGNER_LINK=""
  DESIGNER_CREDIBLE=0
  DESIGNER_HAS_PROPER=0
  DESIGNER_HAS_RISK=0
  DESIGNER_HEADER_STATUS=""
  DESIGNER_DISCOVERED_PATH=""
  DESIGNER_TRACE=()
  ARTIFACT_DESIGNER_SUMMARY=""
  MISC_URLS=()
  MISC_IMAGES=()
  MISC_URL_COUNT=0
  MISC_PROBE_URL_COUNT=0
  MISC_INTERNAL_URL_COUNT=0
  MISC_IMAGE_COUNT=0
  MISC_PAGES_SCANNED=0

  for (( i=0; i<${#R_PATH[@]}; i++ )); do
    if misc_path_is_config_extra "${R_PATH[$i]}"; then
      misc_register_url "${TARGET_URL%/}${R_PATH[$i]}" "site_config"
    else
      misc_register_url "${TARGET_URL%/}${R_PATH[$i]}" "security_probe"
    fi
  done
  for loc in "${ARTIFACT_SITEMAP_LOCS[@]}"; do
    misc_register_url "$loc" "sitemap.xml"
  done
  for loc in "${ARTIFACT_ROBOTS_SITEMAPS[@]}"; do
    misc_register_url "$loc" "robots.txt"
  done

  html=$("$CURL" -s -L --max-time "$TIMEOUT" -A "$ua" "$TARGET_URL" 2>/dev/null || true)
  html="${html:0:$MISC_HTML_MAX}"
  CACHED_HOME_HTML="$html"

  if [[ -n "$html" ]]; then
    misc_register_url "$TARGET_URL" "homepage"
    collect_urls_from_html "$TARGET_URL" "$html" "homepage_links"
  fi

  scan_urls=()
  if [[ -n "$html" ]]; then
    scan_urls+=("$TARGET_URL")
    seen_scan_urls["$TARGET_URL"]=1
  fi
  target_host=$(printf '%s' "$TARGET_URL" | "$SED" -E 's|^https?://||; s|/.*||')

  for path in "${CONFIG_EXTRA_PATHS[@]}"; do
    [[ ${#scan_urls[@]} -ge $MISC_SCAN_MAX_PAGES ]] && break
    url="${TARGET_URL%/}${path}"
    [[ -n "${seen_scan_urls[$url]:-}" ]] && continue
    scan_urls+=("$url")
    seen_scan_urls["$url"]=1
  done

  for loc in "${ARTIFACT_SITEMAP_LOCS[@]}"; do
    [[ ${#scan_urls[@]} -ge $MISC_SCAN_MAX_PAGES ]] && break
    [[ -n "${seen_scan_urls[$loc]:-}" ]] && continue
    loc_host=$(printf '%s' "$loc" | sed -E 's|^https?://||; s|/.*||')
    [[ "$loc_host" != "$target_host" ]] && continue
    scan_urls+=("$loc")
    seen_scan_urls["$loc"]=1
  done

  for url in "${scan_urls[@]}"; do
    if [[ "$url" == "$TARGET_URL" && -n "$html" ]]; then
      chunk="$html"
    else
      chunk=$("$CURL" -s -L --max-time "$TIMEOUT" -A "$ua" "$url" 2>/dev/null || true)
      chunk="${chunk:0:$MISC_HTML_MAX}"
      [[ -z "$chunk" ]] && continue
    fi
    path="${url#$TARGET_URL}"; [[ -z "$path" ]] && path="/"
    MISC_PAGES_SCANNED=$((MISC_PAGES_SCANNED + 1))
    collect_urls_from_html "$url" "$chunk" "page_links"
    collect_images_from_html "$url" "$chunk" "$path"
  done

  misc_recount_url_buckets

  add_check "MISC" "Security probe URL inventory" "CATALOGUED" "INFO" "${MISC_PROBE_URL_COUNT} unique URL(s) from GET path probes" "INFO" "no"
  add_check "MISC" "Internal site URL inventory" "CATALOGUED" "INFO" "${MISC_INTERNAL_URL_COUNT} unique URL(s) from site config, homepage, sitemap, robots, and sampled page links" "INFO" "no"
  add_check "MISC" "Image inventory" "COUNTED" "INFO" "${MISC_IMAGE_COUNT} unique image(s) on ${MISC_PAGES_SCANNED} sampled page(s)" "INFO" "no"

  [[ -z "$html" ]] && {
    DESIGNER_HEADER_STATUS="not_found"
    add_check "ATTRIBUTION" "Designer / creator credit" "NOT_FOUND" "INFO" "Homepage HTML empty — could not scan for designer/creator credit" "INFO" "no"
    return 0
  }

  extract_designer_from_html "$html"
  [[ -z "$DESIGNER_NAME" ]] && discover_designer_from_open_paths "$ua"
  name=$(designer_trim_person_name "$DESIGNER_NAME")

  if [[ -z "$name" ]]; then
    DESIGNER_NAME=""
    DESIGNER_HEADER_STATUS="not_found"
    add_check "ATTRIBUTION" "Designer / creator credit" "NOT_FOUND" "INFO" "No Designed by / Created by pattern on homepage or open directory paths — may be JS-rendered or omitted" "INFO" "no"
    return 0
  fi

  [[ ${#name} -lt 3 || ${#name} -gt 60 ]] && {
    DESIGNER_NAME=""
    DESIGNER_HEADER_STATUS="not_found"
    add_check "ATTRIBUTION" "Designer / creator credit" "NOT_FOUND" "INFO" "Credit pattern matched but name could not be parsed reliably" "INFO" "no"
    return 0
  }
  is_credit_noise "$name" && {
    DESIGNER_NAME=""
    DESIGNER_HEADER_STATUS="not_found"
    add_check "ATTRIBUTION" "Designer / creator credit" "NOT_FOUND" "INFO" "Credit matched CMS/platform boilerplate only — no individual designer name" "INFO" "no"
    return 0
  }

  DESIGNER_NAME="$name"

  if [[ -n "$DESIGNER_DISCOVERED_PATH" ]]; then
    local found_in_scan=0 su
    for su in "${scan_urls[@]}"; do
      [[ "$su" == "${TARGET_URL%/}${DESIGNER_DISCOVERED_PATH}" || "$su" == "${TARGET_URL%/}${DESIGNER_DISCOVERED_PATH%/}" ]] && { found_in_scan=1; break; }
    done
    if [[ $found_in_scan -eq 0 ]]; then
      chunk=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL%/}${DESIGNER_DISCOVERED_PATH}" 2>/dev/null | head -c 25000)
      [[ -n "$chunk" ]] && scan_designer_on_page "${TARGET_URL%/}${DESIGNER_DISCOVERED_PATH}" "$chunk" "$name"
    fi
  fi

  for url in "${scan_urls[@]}"; do
    if [[ "$url" == "$TARGET_URL" ]]; then
      chunk="$html"
    else
      chunk=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "$url" 2>/dev/null | head -c 25000)
      [[ -z "$chunk" ]] && continue
    fi
    scan_designer_on_page "$url" "$chunk" "$name"
  done

  local entry place impact
  for entry in "${DESIGNER_TRACE[@]}"; do
    local r="${entry#*|}"
    place="${r%%|*}"; r="${r#*|}"
    impact="${r%%|*}"
    case "$place" in
      html_comment) comment_pages=$((comment_pages+1)) ;;
      title_tag) title_pages=$((title_pages+1)) ;;
      meta_tag|json_ld) meta_pages=$((meta_pages+1)) ;;
      hidden_css) hidden_pages=$((hidden_pages+1)) ;;
      footer_link|visible_text) link_pages=$((link_pages+1)) ;;
    esac
  done

  DESIGNER_HAS_RISK=0
  [[ $title_pages -gt 0 || $hidden_pages -gt 0 ]] && DESIGNER_HAS_RISK=1

  DESIGNER_HAS_PROPER=0
  DESIGNER_CREDIBLE=0
  if [[ $comment_pages -gt 0 || $link_pages -gt 0 || "$DESIGNER_SOURCE" == "html_comment" || "$DESIGNER_SOURCE" == "visible_text" ]]; then
    DESIGNER_HAS_PROPER=1
    DESIGNER_CREDIBLE=1
  fi

  if [[ $DESIGNER_HAS_PROPER -eq 1 && $DESIGNER_HAS_RISK -eq 1 ]]; then
    DESIGNER_HEADER_STATUS="found_mixed"
  elif [[ $DESIGNER_HAS_PROPER -eq 1 ]]; then
    DESIGNER_HEADER_STATUS="found_proper"
  elif [[ $DESIGNER_HAS_RISK -eq 1 ]]; then
    DESIGNER_HEADER_STATUS="found_risky"
  else
    DESIGNER_HEADER_STATUS="found_other"
  fi

  add_check "ATTRIBUTION" "Designer detected" "FOUND" "INFO" "Designer/creator: ${name} (first seen: ${DESIGNER_SOURCE}${DESIGNER_DISCOVERED_PATH:+ at ${DESIGNER_DISCOVERED_PATH}})" "INFO" "no"
  ARTIFACT_DESIGNER_SUMMARY="name=${name}; source=${DESIGNER_SOURCE}; path=${DESIGNER_DISCOVERED_PATH:-homepage}; credible=${DESIGNER_CREDIBLE}; proper=${DESIGNER_HAS_PROPER}; risk=${DESIGNER_HAS_RISK}; pages_traced=${#scan_urls[@]}; placements=${#DESIGNER_TRACE[@]}"

  [[ $DESIGNER_HAS_PROPER -eq 1 ]] \
    && add_check "ATTRIBUTION" "Designer credit (proper)" "OK" "OK" "${name} credited in acceptable location (${DESIGNER_SOURCE}) — shown in report header" "EXPECTED" "no"

  [[ -n "$DESIGNER_DISCOVERED_PATH" ]] \
    && add_check "ATTRIBUTION" "Credit off homepage" "FOUND" "INFO" "Designer/creator credit read from ${DESIGNER_DISCOVERED_PATH} (not the site homepage) — verify that URL should be public" "INFO" "no"

  if [[ $comment_pages -gt 0 && $title_pages -eq 0 && $meta_pages -eq 0 && $hidden_pages -eq 0 ]]; then
    add_check "ATTRIBUTION" "Comment-only credit" "OK" "OK" "Credit in HTML comment(s) on ${comment_pages} sampled page(s) — not indexed by Google (no SEO harm)" "EXPECTED" "no"
  elif [[ $comment_pages -gt 0 ]]; then
    add_check "ATTRIBUTION" "HTML comment credit" "OK" "OK" "Proper HTML comment credit on ${comment_pages} page(s) — good developer attribution" "EXPECTED" "no"
  fi

  [[ $link_pages -gt 0 ]] \
    && add_check "ATTRIBUTION" "Visible credit" "PRESENT" "OK" "Visible designer credit on ${link_pages} sampled page(s) — normal footer attribution" "EXPECTED" "no"

  [[ $title_pages -gt 0 ]] \
    && add_check "ATTRIBUTION" "Name in <title>" "PRESENT" "MEDIUM" "Designer name in <title> on ${title_pages} sampled page(s) — dilutes brand keywords in SERPs" "ACTION" "yes"

  [[ $meta_pages -gt 0 ]] \
    && add_check "ATTRIBUTION" "Name in meta tags" "PRESENT" "LOW" "Designer name in meta/JSON-LD on ${meta_pages} sampled page(s) — verify metadata matches site owner intent" "VERIFY" "no"

  [[ $hidden_pages -gt 0 ]] \
    && add_check "ATTRIBUTION" "Hidden placement" "DETECTED" "HIGH" "Designer name near display:none on ${hidden_pages} page(s) — review hidden-text SEO risk" "ACTION" "yes"

  if [[ -n "$DESIGNER_LINK" ]]; then
    local abs_link="$DESIGNER_LINK" lc
    [[ "$abs_link" != http* ]] && abs_link="${TARGET_URL%/}/${abs_link#/}"
    lc=$($CURL -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -A "$ua" "$abs_link" 2>/dev/null)
    if [[ "$lc" == "404" || "$lc" == "410" ]]; then
      add_check "ATTRIBUTION" "Designer credit link" "BROKEN" "LOW" "Designer link ${DESIGNER_LINK} returned ${lc} — broken outbound ref for crawlers" "VERIFY" "no"
    elif [[ "$lc" == "200" || "$lc" == "301" || "$lc" == "302" ]]; then
      add_check "ATTRIBUTION" "Designer credit link" "OK" "OK" "Designer credit link reachable (${DESIGNER_LINK} → ${lc})"
    fi
  fi
}

compare_with_baseline() {
  local baseline="$1" check
  [[ -f "$baseline" ]] || return 0
  COMPARE_BASELINE_LABEL="$baseline"
  COMPARE_PREV_HYGIENE=$(json_score_field "$baseline" "hygiene")
  COMPARE_PREV_EXPOSURE=$(json_score_field "$baseline" "exposure")
  compute_scores
  COMPARE_HYGIENE_DELTA=$((SCORE_HYGIENE - ${COMPARE_PREV_HYGIENE:-0}))
  COMPARE_EXPOSURE_DELTA=$((SCORE_EXPOSURE - ${COMPARE_PREV_EXPOSURE:-0}))

  COMPARE_NEW_ACTIONS=()
  for check in "${SEC_CHECKS[@]}"; do
    parse_check "$check"
    [[ "$PC_CLASS" != "ACTION" ]] && continue
    case "$PC_STATUS" in OK|PROTECTED*|REJECTED|SUPPORTED|PRESENT|SECURE|OFF|NONE_FOUND|EXPECTED) continue ;; esac
    grep -qF "\"item\":\"${PC_ITEM}\"" "$baseline" 2>/dev/null && continue
    COMPARE_NEW_ACTIONS+=("${PC_ITEM}: ${PC_DETAIL:0:120}")
  done

  local summary="vs baseline: Hygiene ${COMPARE_PREV_HYGIENE:-?}→${SCORE_HYGIENE} (${COMPARE_HYGIENE_DELTA}), Exposure ${COMPARE_PREV_EXPOSURE:-?}→${SCORE_EXPOSURE} (${COMPARE_EXPOSURE_DELTA})"
  if [[ ${#COMPARE_NEW_ACTIONS[@]} -gt 0 ]]; then
    add_check "COMPARE" "Drift summary" "CHANGED" "INFO" "${summary}; ${#COMPARE_NEW_ACTIONS[@]} new ACTION item(s)" "INFO" "no"
  else
    add_check "COMPARE" "Drift summary" "STABLE" "OK" "$summary; no new ACTION items vs baseline" "INFO" "no"
  fi
}

print_dry_run_plan() {
  local -a paths=("$@")
  log_msg ""
  log_msg "DRY RUN — no HTTP traffic will be sent"
  log_msg "Target     : $TARGET_URL"
  log_msg "Framework  : ${FRAMEWORK:-pending detection}"
  log_msg "GET probes : ${#paths[@]} paths"
  local p
  for p in "${paths[@]}"; do log_msg "  GET  $p"; done
  log_msg "Checks     : headers, TLS, cookies, rate limits (6 GET + 15 POST on login), dir listing,"
  log_msg "              version disclosure, API content, open redirect, plugins, framework specifics,"
  log_msg "              policy parse (HSTS/CSP), redirect chain, robots.txt/security.txt/sitemap,"
  log_msg "              designer/creator attribution, site URL/image inventory,"
  log_msg "              CORS on /api/, HTTP TRACE/OPTIONS"
  [[ ${#CONFIG_RATE_LIMIT_POST[@]} -gt 0 ]] && {
    log_msg "Extra POST rate-limit targets:"
    local rp pt
    for rp in "${CONFIG_RATE_LIMIT_POST[@]}"; do
      pt="${rp#*|}"; rp="${rp%%|*}"
      log_msg "  POST ${rp} (${pt})"
    done
  }
  log_msg ""
}

# ── Security Checks ───────────────────────────────────────────────

check_headers() {
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"
  local headers
  headers=$($CURL -sI -L --max-time $TIMEOUT -A "$ua" "$TARGET_URL" 2>/dev/null)
  CACHED_HEADERS="$headers"

  local -a defs=(
    "Strict-Transport-Security|HIGH|Forces HTTPS — prevents protocol downgrade attacks"
    "Content-Security-Policy|HIGH|Controls resource loading — primary XSS mitigation"
    "X-Frame-Options|MEDIUM|Prevents clickjacking via iframe embedding"
    "X-Content-Type-Options|MEDIUM|Stops MIME-type sniffing attacks"
    "Referrer-Policy|LOW|Controls referrer info leaked to third parties"
    "Permissions-Policy|LOW|Restricts browser API access (camera, mic, geolocation)"
  )
  for def in "${defs[@]}"; do
    local name="${def%%|*}"; local r="${def#*|}"; local sev="${r%%|*}"; local desc="${r#*|}"
    local val class="ACTION" scored="yes"
    val=$(echo "$headers" | grep -i "^${name}:" | tail -1 | tr -d '\r\n')
    if [[ -n "$val" ]]; then
      add_check "HEADERS" "$name" "PRESENT" "OK" "${val:0:80}"
    else
      if [[ "$name" == "Permissions-Policy" ]]; then
        sev="LOW"; class="INFO"; scored="no"
      elif [[ "$name" == "Strict-Transport-Security" ]] && [[ "$CDN_DETECTED" != "none" && "$CDN_DETECTED" != "unknown" ]]; then
        sev="MEDIUM"; class="VERIFY"; desc+=" — not visible externally; may be configured at ${CDN_DETECTED} edge or blocked by proxy SSL detection"
        scored="no"
      fi
      add_check "HEADERS" "$name" "MISSING" "$sev" "$desc" "$class" "$scored"
    fi
  done
  local xpb; xpb=$(echo "$headers" | grep -i "^x-powered-by:" | tail -1 | tr -d '\r\n')
  [[ -n "$xpb" ]] && add_check "HEADERS" "X-Powered-By" "LEAKING" "LOW" "Discloses stack: $xpb"
  echo "$SERVER_HEADER" | grep -qE '/[0-9.]+' && add_check "HEADERS" "Server version" "LEAKING" "LOW" "Version in Server header: $SERVER_HEADER"
}

openssl_tls_handshake() {
  local host="$1" port="$2" tls_flag="$3"
  local out
  if [[ -n "$tls_flag" ]]; then
    out=$(echo | "$OPENSSL" s_client -connect "${host}:${port}" -servername "$host" $tls_flag 2>&1)
  else
    out=$(echo | "$OPENSSL" s_client -connect "${host}:${port}" -servername "$host" 2>&1)
  fi
  echo "$out" | grep -q "CONNECTED\|^Protocol"
}

openssl_cert_info() {
  local host="$1" port="$2"
  echo | "$OPENSSL" s_client -connect "${host}:${port}" -servername "$host" 2>/dev/null \
    | "$OPENSSL" x509 -noout -subject -issuer -enddate 2>/dev/null
}

body_indicates_rate_limit() {
  local body="$1"
  echo "$body" | grep -qiE "too many (login )?attempts|rate limit|locked out|temporarily blocked|slow down|try again later|challenge-platform|cf-chl"
}

check_tls() {
  url_host_port
  local host="$URL_HOST" port="$URL_PORT"

  if ! command -v "$OPENSSL" >/dev/null 2>&1 || ! "$OPENSSL" version >/dev/null 2>&1; then
    add_check "TLS" "OpenSSL probe" "UNAVAILABLE" "LOW" "openssl not available" "VERIFY" "no"
    return
  fi

  local -a vers=("1.0" "1.1" "1.2" "1.3")
  local -a flags=("-tls1" "-tls1_1" "-tls1_2" "-tls1_3")
  local -a sevs=("HIGH" "MEDIUM" "OK" "OK")
  local -a good=("0" "0" "1" "1")
  local i cert subject issuer enddate days_left end_epoch now_epoch

  for i in 0 1 2 3; do
    if openssl_tls_handshake "$host" "$port" "${flags[$i]}"; then
      [[ "${good[$i]}" == "1" ]] \
        && add_check "TLS" "TLS ${vers[$i]}" "SUPPORTED" "OK" "TLS ${vers[$i]} handshake succeeded (${host}:${port})" \
        || add_check "TLS" "TLS ${vers[$i]}" "ACCEPTED" "${sevs[$i]}" "Deprecated TLS ${vers[$i]} accepted — should be disabled" "ACTION" "yes"
    else
      [[ "${good[$i]}" == "0" ]] \
        && add_check "TLS" "TLS ${vers[$i]}" "REJECTED" "OK" "Deprecated TLS ${vers[$i]} correctly rejected" \
        || add_check "TLS" "TLS ${vers[$i]}" "UNAVAILABLE" "LOW" "TLS ${vers[$i]} handshake failed at ${host}:${port}" "VERIFY" "no"
    fi
  done

  cert=$(openssl_cert_info "$host" "$port")
  if [[ -n "$cert" ]]; then
    subject=$(echo "$cert" | grep -i "^subject=" | head -1 | sed 's/subject=//')
    issuer=$(echo "$cert" | grep -i "^issuer=" | head -1 | sed 's/issuer=//')
    enddate=$(echo "$cert" | grep -i "^notAfter=" | head -1 | sed 's/notAfter=//')
    add_check "TLS" "Certificate subject" "PRESENT" "OK" "${subject:0:120}"
    add_check "TLS" "Certificate issuer" "PRESENT" "OK" "${issuer:0:120}"
    if [[ -n "$enddate" ]]; then
      end_epoch=$("$DATE" -j -f "%b %d %T %Y %Z" "$enddate" +%s 2>/dev/null || "$DATE" -d "$enddate" +%s 2>/dev/null || echo 0)
      now_epoch=$("$DATE" +%s)
      if [[ "$end_epoch" -gt 0 ]]; then
        days_left=$(( (end_epoch - now_epoch) / 86400 ))
        if [[ $days_left -lt 0 ]]; then
          add_check "TLS" "Certificate expiry" "EXPIRED" "CRITICAL" "Certificate expired: $enddate" "ACTION" "yes"
        elif [[ $days_left -lt 30 ]]; then
          add_check "TLS" "Certificate expiry" "EXPIRING" "HIGH" "Expires in ${days_left}d ($enddate)" "ACTION" "yes"
        else
          add_check "TLS" "Certificate expiry" "OK" "OK" "Valid ~${days_left}d — expires $enddate"
        fi
      else
        add_check "TLS" "Certificate expiry" "PRESENT" "INFO" "$enddate" "INFO" "no"
      fi
    fi
  else
    add_check "TLS" "Certificate" "UNAVAILABLE" "LOW" "Could not read certificate from ${host}:${port}" "VERIFY" "no"
  fi
}

check_cookies() {
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"
  local login_url
  case "$FRAMEWORK" in
    wordpress) login_url="${TARGET_URL}/wp-login.php"   ;;
    django)    login_url="${TARGET_URL}/admin/login/"   ;;
    laravel)   login_url="${TARGET_URL}/login"          ;;
    rails)     login_url="${TARGET_URL}/users/sign_in"  ;;
    *)         login_url="${TARGET_URL}/login/"         ;;
  esac

  local set_cookies
  set_cookies=$($CURL -sI -L --max-time $TIMEOUT -A "$ua" "$login_url" 2>/dev/null | grep -i "^Set-Cookie:" | tr -d '\r')
  [[ -z "$set_cookies" ]] && set_cookies=$($CURL -sI -L --max-time $TIMEOUT -A "$ua" "$TARGET_URL" 2>/dev/null | grep -i "^Set-Cookie:" | tr -d '\r')

  if [[ -z "$set_cookies" ]]; then
    add_check "COOKIES" "Detection" "NONE_FOUND" "INFO" "No Set-Cookie headers found on login page or homepage"; return
  fi

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    local cname; cname=$(echo "$line" | sed 's/^[Ss]et-[Cc]ookie:[[:space:]]*//' | cut -d'=' -f1 | xargs)
    [[ -z "$cname" ]] && continue

    # Framework-expected CSRF cookies (HttpOnly intentionally omitted)
    case "$cname|${FRAMEWORK:-unknown}" in
      csrftoken|django)
        add_check "COOKIES" "$cname" "EXPECTED" "OK" "Django CSRF cookie — HttpOnly intentionally omitted for JavaScript CSRF token access" "EXPECTED" "no"
        continue ;;
      XSRF-TOKEN|laravel)
        add_check "COOKIES" "$cname" "EXPECTED" "OK" "Laravel CSRF cookie — readable by JavaScript by design" "EXPECTED" "no"
        continue ;;
    esac

    # CDN / bot-management cookies
    case "$cname" in
      __cf_bm|_cfuvid|cf_clearance)
        local cdn_missing=""
        echo "$line" | grep -qi "secure" || cdn_missing+="Secure "
        if [[ -z "$cdn_missing" ]]; then
          add_check "COOKIES" "$cname" "SECURE" "OK" "CDN cookie — acceptable flags for ${CDN_DETECTED:-edge}"
        else
          add_check "COOKIES" "$cname" "INSECURE" "LOW" "CDN cookie missing: ${cdn_missing% }" "VERIFY" "no"
        fi
        continue ;;
    esac

    local missing=""
    echo "$line" | grep -qi "httponly" || missing+="HttpOnly "
    echo "$line" | grep -qi "secure"   || missing+="Secure "
    echo "$line" | grep -qi "samesite" || missing+="SameSite "
    if [[ -z "$missing" ]]; then
      add_check "COOKIES" "$cname" "SECURE" "OK" "All flags present"
    else
      local sev="MEDIUM" class="ACTION" scored="yes"
      echo "$missing" | grep -qE "HttpOnly|Secure" && sev="HIGH"
      add_check "COOKIES" "$cname" "INSECURE" "$sev" "Missing: ${missing% }" "$class" "$scored"
    fi
  done <<EOF
$set_cookies
EOF
}

_rate_limit_get_probe() {
  local login_path="$1" label="$2"
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"
  local got_limited=0 limited_at=0 i code

  for i in {1..6}; do
    code=$($CURL -s -o /dev/null -w "%{http_code}" --max-time 10 -A "$ua" "${TARGET_URL}${login_path}" 2>/dev/null)
    if [[ "$code" == "429" || "$code" == "503" ]]; then
      got_limited=1; limited_at=$i; break
    fi
  done

  if [[ $got_limited -eq 1 ]]; then
    add_check "RATE_LIMIT" "$label GET" "PROTECTED" "OK" "Rate limiting triggered after $limited_at GET requests"
  else
    local note="No 429/503 after 6 rapid GET requests"
    local sev="LOW" class="INFO" scored="no"
    if [[ "$CDN_DETECTED" == "none" || "$CDN_DETECTED" == "unknown" ]]; then
      note+=" — see POST probe for login abuse signal"
    else
      note+=" (${CDN_DETECTED} edge may not limit GET — see POST probe)"
    fi
    add_check "RATE_LIMIT" "$label GET" "UNPROTECTED" "$sev" "$note" "$class" "$scored"
  fi
}

_rate_limit_post_probe() {
  local login_path="$1" post_kind="$2" label="$3"
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"
  local url="${TARGET_URL}${login_path}"
  local tmp_body tmp_jar i code resp_body got_limited=0 limited_at=0 lockout_at=0 csrf token
  tmp_body=$(mktemp "${TMPDIR:-/tmp}/wa_body.XXXXXX")
  tmp_jar=$(mktemp "${TMPDIR:-/tmp}/wa_jar.XXXXXX")

  for i in {1..15}; do
    case "$post_kind" in
      django_admin)
        resp_body=$($CURL -s -c "$tmp_jar" -b "$tmp_jar" --max-time $TIMEOUT -A "$ua" "$url" 2>/dev/null)
        csrf=$(echo "$resp_body" | grep -oE 'name="csrfmiddlewaretoken" value="[^"]+"' | head -1 | sed -E 's/.*value="([^"]+)".*/\1/')
        code=$($CURL -s -o "$tmp_body" -w "%{http_code}" -c "$tmp_jar" -b "$tmp_jar" --max-time 10 -A "$ua" \
          -X POST -H "Content-Type: application/x-www-form-urlencoded" -H "Referer: $url" \
          --data "username=audit_probe_${i}&password=invalid_probe&csrfmiddlewaretoken=${csrf}" \
          "$url" 2>/dev/null)
        ;;
      wordpress)
        code=$($CURL -s -o "$tmp_body" -w "%{http_code}" --max-time 10 -A "$ua" \
          -X POST -H "Content-Type: application/x-www-form-urlencoded" \
          --data "log=audit_probe_${i}&pwd=invalid_probe&wp-submit=Log+In" \
          "$url" 2>/dev/null)
        ;;
      laravel)
        resp_body=$($CURL -s -c "$tmp_jar" -b "$tmp_jar" --max-time $TIMEOUT -A "$ua" "$url" 2>/dev/null)
        token=$(echo "$resp_body" | grep -oE 'name="_token" value="[^"]+"' | head -1 | sed -E 's/.*value="([^"]+)".*/\1/')
        code=$($CURL -s -o "$tmp_body" -w "%{http_code}" -c "$tmp_jar" -b "$tmp_jar" --max-time 10 -A "$ua" \
          -X POST -H "Content-Type: application/x-www-form-urlencoded" \
          --data "email=audit_probe_${i}@example.com&password=invalid_probe&_token=${token}" \
          "$url" 2>/dev/null)
        ;;
      rails)
        resp_body=$($CURL -s -c "$tmp_jar" -b "$tmp_jar" --max-time $TIMEOUT -A "$ua" "$url" 2>/dev/null)
        token=$(echo "$resp_body" | grep -oE 'name="authenticity_token" value="[^"]+"' | head -1 | sed -E 's/.*value="([^"]+)".*/\1/')
        code=$($CURL -s -o "$tmp_body" -w "%{http_code}" -c "$tmp_jar" -b "$tmp_jar" --max-time 10 -A "$ua" \
          -X POST -H "Content-Type: application/x-www-form-urlencoded" \
          --data "user[email]=audit_probe_${i}@example.com&user[password]=invalid_probe&authenticity_token=${token}" \
          "$url" 2>/dev/null)
        ;;
      json)
        code=$($CURL -s -o "$tmp_body" -w "%{http_code}" --max-time 10 -A "$ua" \
          -X POST -H "Content-Type: application/json" \
          --data "{\"message\":\"audit_probe_${i}\"}" \
          "$url" 2>/dev/null)
        ;;
      *)
        code=$($CURL -s -o "$tmp_body" -w "%{http_code}" --max-time 10 -A "$ua" \
          -X POST -H "Content-Type: application/x-www-form-urlencoded" \
          --data "probe=${i}" \
          "$url" 2>/dev/null)
        ;;
    esac
    resp_body=$(cat "$tmp_body" 2>/dev/null)
    if [[ "$code" == "429" || "$code" == "503" ]]; then
      got_limited=1; limited_at=$i; break
    fi
    if [[ "$code" == "403" ]] && body_indicates_rate_limit "$resp_body"; then
      got_limited=1; limited_at=$i; break
    fi
    if body_indicates_rate_limit "$resp_body"; then
      lockout_at=$i; got_limited=1; break
    fi
  done

  rm -f "$tmp_body" "$tmp_jar"

  if [[ $got_limited -eq 1 ]]; then
    if [[ $lockout_at -gt 0 ]]; then
      add_check "RATE_LIMIT" "$label POST" "PROTECTED" "OK" "Lockout/rate-limit signal in response body after $lockout_at POST attempts"
    else
      add_check "RATE_LIMIT" "$label POST" "PROTECTED" "OK" "HTTP $code after $limited_at POST attempts"
    fi
  else
    local note="No 429/503/lockout after 15 POST attempts with invalid credentials/data"
    local sev="HIGH" class="ACTION" scored="yes"
    if [[ "$CDN_DETECTED" != "none" && "$CDN_DETECTED" != "unknown" ]]; then
      sev="MEDIUM"
    fi
    add_check "RATE_LIMIT" "$label POST" "UNPROTECTED" "$sev" "$note" "$class" "$scored"
  fi
}

check_rate_limiting() {
  local login_path post_kind label entry path ptype
  case "$FRAMEWORK" in
    wordpress) login_path="/wp-login.php"; post_kind="wordpress" ;;
    django)    login_path="/admin/login/"; post_kind="django_admin" ;;
    laravel)   login_path="/login"; post_kind="laravel" ;;
    rails)     login_path="/users/sign_in"; post_kind="rails" ;;
    *)         login_path="/login/"; post_kind="form" ;;
  esac
  label="$login_path"
  _rate_limit_get_probe "$login_path" "$label"
  _rate_limit_post_probe "$login_path" "$post_kind" "$label"
  for entry in "${CONFIG_RATE_LIMIT_POST[@]}"; do
    path="${entry%%|*}"; ptype="${entry#*|}"
    [[ -n "$path" ]] && _rate_limit_post_probe "$path" "$ptype" "$path"
  done
}

check_dir_listing() {
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"
  declare -A seen_dirs
  local -a dir_paths=()

  for (( i=0; i<${#R_PATH[@]}; i++ )); do
    if [[ "${R_NOTE[$i]}" == "OPEN" && "${R_PATH[$i]}" == */ && -z "${seen_dirs[${R_PATH[$i]}]:-}" ]]; then
      dir_paths+=("${R_PATH[$i]}"); seen_dirs[${R_PATH[$i]}]=1
    fi
  done
  for path in "${CONFIG_EXTRA_PATHS[@]}"; do
    [[ "$path" == */ ]] || continue
    path_is_site_root "$path" && continue
    [[ -n "${seen_dirs[$path]:-}" ]] && continue
    dir_paths+=("$path"); seen_dirs[$path]=1
  done

  for dp in "${dir_paths[@]}"; do
    local dir_body
    dir_body=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}${dp}" 2>/dev/null | head -c 3000)
    if body_is_directory_listing "$dir_body"; then
      add_check "DIR_LISTING" "$dp" "EXPOSED" "HIGH" "Directory listing enabled — file structure publicly browsable"
    elif body_is_html_document "$dir_body"; then
      add_check "DIR_LISTING" "$dp" "HTML_DOCUMENT" "INFO" "Open path returns a full HTML page (not a directory index) — verify public access is intended (static file, default document, or leftover template)" "INFO" "no"
    else
      local code; code=$($CURL -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -A "$ua" "${TARGET_URL}${dp}" 2>/dev/null)
      [[ "$code" == "200" ]] \
        && add_check "DIR_LISTING" "$dp" "OPEN_NO_INDEX" "INFO" "Returns 200 but no directory listing (blank or custom response)" "INFO" "no" \
        || add_check "DIR_LISTING" "$dp" "PROTECTED" "OK" "Returns $code"
    fi
  done
}

check_version_disclosure() {
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"

  echo "$SERVER_HEADER" | grep -qE '/[0-9.]+' && add_check "VERSION" "Server header" "LEAKING" "LOW" "Version string: $SERVER_HEADER"

  case "$FRAMEWORK" in
    wordpress)
      local rm_code; rm_code=$($CURL -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/readme.html" 2>/dev/null)
      if [[ "$rm_code" == "200" ]]; then
        local rm_body ver
        rm_body=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/readme.html" 2>/dev/null | head -c 3000)
        ver=$(echo "$rm_body" | grep -ioE 'version [0-9.]+' | head -1 | sed 's/[Vv]ersion //')
        [[ -n "$ver" ]] \
          && { add_check "VERSION" "/readme.html" "EXPOSED" "HIGH" "WordPress $ver disclosed"; VERSIONS_FOUND+=("readme.html|$ver"); } \
          || add_check "VERSION" "/readme.html" "EXPOSED" "MEDIUM" "Accessible — contains version info"
      fi

      local lic_code; lic_code=$($CURL -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/license.txt" 2>/dev/null)
      [[ "$lic_code" == "200" ]] && add_check "VERSION" "/license.txt" "EXPOSED" "LOW" "Accessible — ships with WordPress, hints at version"

      local hb; hb=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "$TARGET_URL" 2>/dev/null | head -c 10000)
      local gen_ver; gen_ver=$(echo "$hb" | grep -i "generator" | grep -oE 'WordPress [0-9.]+' | head -1 | sed 's/WordPress //')
      [[ -n "$gen_ver" ]] && { add_check "VERSION" "Generator meta tag" "EXPOSED" "MEDIUM" "WordPress $gen_ver in <meta name=generator> — remove via functions.php or Rank Math"; VERSIONS_FOUND+=("meta-generator|$gen_ver"); }

      local opml; opml=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/wp-links-opml.php" 2>/dev/null)
      local opml_ver; opml_ver=$(echo "$opml" | grep -oE 'generator="WordPress/[0-9.]+' | head -1 | sed 's/.*WordPress\///; s/"//')
      [[ -n "$opml_ver" ]] && { add_check "VERSION" "/wp-links-opml.php" "EXPOSED" "MEDIUM" "WordPress $opml_ver via OPML generator attribute"; VERSIONS_FOUND+=("wp-links-opml|$opml_ver"); }
      ;;

    django)
      local hh; hh=$($CURL -sI -L --max-time $TIMEOUT -A "$ua" "$TARGET_URL" 2>/dev/null)
      local dj_ver; dj_ver=$(echo "$hh" | grep -i "x-django-version:" | sed 's/.*: //' | tr -d '\r\n')
      [[ -n "$dj_ver" ]] && { add_check "VERSION" "X-Django-Version header" "EXPOSED" "MEDIUM" "Django $dj_ver in response header"; VERSIONS_FOUND+=("header|$dj_ver"); }

      local eb; eb=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/this-path-not-exist-$(date +%s)" 2>/dev/null | head -c 6000)
      local dj_ev; dj_ev=$(echo "$eb" | grep -oE 'Django Version:[[:space:]]*[0-9.]+|Django/[0-9.]+' | head -1 | sed -E 's/Django Version:[[:space:]]*//; s/Django\///')
      [[ -n "$dj_ev" ]] && { add_check "VERSION" "404 error page" "EXPOSED" "CRITICAL" "Django $dj_ev in debug error page — DEBUG=True leaks stack info"; VERSIONS_FOUND+=("error-page|$dj_ev"); }
      ;;

    laravel)
      local eb; eb=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/this-path-not-exist-$(date +%s)" 2>/dev/null | head -c 5000)
      local lv; lv=$(echo "$eb" | grep -oE 'Laravel [0-9.]+|laravel/framework [0-9.]+' | head -1 | sed -E 's/Laravel //; s/laravel\/framework //')
      [[ -n "$lv" ]] && { add_check "VERSION" "Error page" "EXPOSED" "HIGH" "Laravel $lv in error response — set APP_DEBUG=false"; VERSIONS_FOUND+=("error-page|$lv"); }
      ;;

    rails)
      local hh; hh=$($CURL -sI -L --max-time $TIMEOUT -A "$ua" "$TARGET_URL" 2>/dev/null)
      local rv; rv=$(echo "$hh" | grep -i "x-powered-by:" | grep -oE 'Rails [0-9.]+' | head -1 | sed 's/Rails //')
      [[ -n "$rv" ]] && { add_check "VERSION" "X-Powered-By header" "EXPOSED" "MEDIUM" "Rails $rv in header"; VERSIONS_FOUND+=("header|$rv"); }
      ;;
  esac
}

check_api_content() {
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"

  _path_open() { local j; for (( j=0; j<${#R_PATH[@]}; j++ )); do [[ "${R_PATH[$j]}" == "$1" && "${R_NOTE[$j]}" == "OPEN" ]] && return 0; done; return 1; }

  case "$FRAMEWORK" in
    wordpress)
      if _path_open "/wp-json/wp/v2/users"; then
        local body; body=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/wp-json/wp/v2/users" 2>/dev/null)
        local slugs; slugs=$(echo "$body" | grep -oE '"slug"[[:space:]]*:[[:space:]]*"[^"]+"' | sed -E 's/"slug"[[:space:]]*:[[:space:]]*"([^"]+)"/\1/' | tr '\n' ', ' | sed 's/, $//')
        local names; names=$(echo "$body" | grep -oE '"name"[[:space:]]*:[[:space:]]*"[^"]+"' | sed -E 's/"name"[[:space:]]*:[[:space:]]*"([^"]+)"/\1/' | tr '\n' ', ' | sed 's/, $//')
        [[ -n "$slugs" ]] \
          && { add_check "API_CONTENT" "/wp-json/wp/v2/users" "CRITICAL" "CRITICAL" "Usernames: [$slugs] | Display names: [$names]"; API_CONTENT+=("/wp-json/wp/v2/users|${slugs}"); } \
          || add_check "API_CONTENT" "/wp-json/wp/v2/users" "OPEN" "HIGH" "Endpoint open but not parseable — check manually"
      fi
      if _path_open "/wp-json/"; then
        local wj; wj=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/wp-json/" 2>/dev/null | head -c 3000)
        local apv; apv=$(echo "$wj" | grep -oE '"version"[[:space:]]*:[[:space:]]*"[0-9.]+' | head -1 | sed -E 's/"version"[[:space:]]*:[[:space:]]*"//; s/"//')
        [[ -n "$apv" ]] && { add_check "API_CONTENT" "/wp-json/ root" "OPEN" "MEDIUM" "WordPress $apv disclosed via REST API namespace"; VERSIONS_FOUND+=("wp-json|$apv"); }
      fi ;;

    django)
      for ap in "/api/" "/api/v1/" "/api/v2/"; do
        if _path_open "$ap"; then
          local body; body=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}${ap}" 2>/dev/null | head -c 4000)
          echo "$body" | grep -qi "django rest framework\|api root\|browsable" \
            && { add_check "API_CONTENT" "$ap" "OPEN" "HIGH" "DRF Browsable API accessible — exposes all endpoints. Restrict with authentication."; API_CONTENT+=("${ap}|DRF browsable API"); }
        fi
      done ;;

    laravel)
      if _path_open "/api/user"; then
        local body; body=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/api/user" 2>/dev/null | head -c 1000)
        echo "$body" | grep -qi '"email"\|"name"\|"id"' \
          && add_check "API_CONTENT" "/api/user" "CRITICAL" "CRITICAL" "User data returned unauthenticated"
      fi ;;
  esac
}

check_open_redirect() {
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"
  local test_target="https://example.com"
  local -a test_urls=()

  case "$FRAMEWORK" in
    wordpress) test_urls+=("${TARGET_URL}/wp-login.php?redirect_to=${test_target}") ;;
    django)    test_urls+=("${TARGET_URL}/admin/login/?next=${test_target}" "${TARGET_URL}/login/?next=${test_target}") ;;
    laravel)   test_urls+=("${TARGET_URL}/login?redirect=${test_target}" "${TARGET_URL}/login?intended=${test_target}") ;;
    rails)     test_urls+=("${TARGET_URL}/users/sign_in?redirect_uri=${test_target}") ;;
  esac
  test_urls+=("${TARGET_URL}/?redirect=${test_target}" "${TARGET_URL}/?next=${test_target}" "${TARGET_URL}/?url=${test_target}" "${TARGET_URL}/?return=${test_target}")

  local found=0
  for tu in "${test_urls[@]}"; do
    local loc; loc=$($CURL -sI --max-time $TIMEOUT -A "$ua" "$tu" 2>/dev/null | grep -i "^Location:" | tail -1 | tr -d '\r\n')
    if echo "$loc" | grep -q "example.com"; then
      add_check "OPEN_REDIRECT" "${tu#$TARGET_URL}" "VULNERABLE" "HIGH" "Unvalidated redirect to $test_target — phishing risk"
      found=1; break
    fi
  done
  [[ $found -eq 0 ]] && add_check "OPEN_REDIRECT" "Redirect params" "PROTECTED" "OK" "No open redirect detected on standard redirect parameters"
}

check_plugin_versions() {
  [[ "$FRAMEWORK" != "wordpress" ]] && return
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"

  local hb; hb=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "$TARGET_URL" 2>/dev/null | head -c 20000)
  declare -A seen_p; declare -a all_p

  while IFS= read -r slug; do
    [[ -z "$slug" || -n "${seen_p[$slug]}" ]] && continue
    seen_p[$slug]=1; all_p+=("$slug")
  done < <(echo "$hb" | grep -oE 'wp-content/plugins/[^/?#"]+' | sed 's|wp-content/plugins/||' | sort -u)

  local -a high_risk=("contact-form-7" "woocommerce" "yoast-seo" "all-in-one-seo-pack" "wordfence" "jetpack" "wpforms-lite" "akismet" "elementor" "elementor-pro" "rank-math")
  for p in "${high_risk[@]}"; do [[ -n "${seen_p[$p]}" ]] && continue; seen_p[$p]=1; all_p+=("$p"); done

  local found_count=0
  for slug in "${all_p[@]}"; do
    local url="${TARGET_URL}/wp-content/plugins/${slug}/readme.txt"
    local code; code=$($CURL -s -o /dev/null -w "%{http_code}" --max-time 8 -A "$ua" "$url" 2>/dev/null)
    [[ "$code" != "200" ]] && continue
    local body ver
    body=$($CURL -s -L --max-time 8 -A "$ua" "$url" 2>/dev/null | head -c 2000)
    ver=$(echo "$body" | grep -i "stable tag" | head -1 | grep -oE '[0-9.]+' | head -1)
    [[ -n "$ver" ]] \
      && { add_check "PLUGIN_VERSION" "$slug" "EXPOSED" "MEDIUM" "v$ver — check https://wpscan.com/plugins/$slug"; found_count=$((found_count+1)); } \
      || { add_check "PLUGIN_VERSION" "$slug" "EXPOSED" "LOW"    "readme.txt accessible, version unclear"; found_count=$((found_count+1)); }
  done
  [[ $found_count -eq 0 ]] && add_check "PLUGIN_VERSION" "All probed" "PROTECTED" "OK" "No plugin readme.txt files accessible"
}

check_framework_specifics() {
  local ua="${EFFECTIVE_UA:-curl/8.7.1}"

  case "$FRAMEWORK" in
    wordpress)
      local cron_code; cron_code=$($CURL -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/wp-cron.php" 2>/dev/null)
      [[ "$cron_code" == "200" ]] \
        && add_check "WORDPRESS" "/wp-cron.php" "EXPOSED" "MEDIUM" "Publicly accessible — can trigger scheduled tasks. Add DISABLE_WP_CRON=true and use server cron." \
        || add_check "WORDPRESS" "/wp-cron.php" "PROTECTED" "OK" "Returns $cron_code"

      local auth_code; auth_code=$($CURL -s -o /dev/null -w "%{http_code}" -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/?author=1" 2>/dev/null)
      if [[ "$auth_code" == "200" ]]; then
        local auth_body au_name
        auth_body=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/?author=1" 2>/dev/null | head -c 3000)
        au_name=$(echo "$auth_body" | grep -oE 'author/[^/"<]+' | head -1 | sed 's|author/||')
        [[ -n "$au_name" ]] \
          && add_check "WORDPRESS" "/?author=1 enum" "CRITICAL" "CRITICAL" "Username '$au_name' exposed via author archive" \
          || add_check "WORDPRESS" "/?author=1 enum" "HIGH" "HIGH" "Author archive 200 — username enumeration possible"
      fi ;;

    django)
      local eb; eb=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/probe-debug-$(date +%s)" 2>/dev/null | head -c 5000)
      if echo "$eb" | grep -qi "django.core\|Traceback\|RequestContext\|DEBUG.*True"; then
        add_check "DJANGO" "DEBUG mode" "ACTIVE" "CRITICAL" "DEBUG=True in production — leaks source paths, settings, and environment variables"
      else
        add_check "DJANGO" "DEBUG mode" "OFF" "OK" "No Django debug page on 404 — DEBUG appears False"
      fi
      echo "$eb" | grep -qi "invalid http_host\|ALLOWED_HOSTS" \
        && add_check "DJANGO" "ALLOWED_HOSTS" "LEAKING" "HIGH" "ALLOWED_HOSTS misconfiguration visible in response" ;;

    laravel)
      local eb; eb=$($CURL -s -L --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/probe-debug-$(date +%s)" 2>/dev/null | head -c 5000)
      if echo "$eb" | grep -qi "whoops\|illuminate\|laravel.*exception"; then
        add_check "LARAVEL" "APP_DEBUG" "ACTIVE" "CRITICAL" "APP_DEBUG=true — Whoops error page leaks stack traces and config"
      else
        add_check "LARAVEL" "APP_DEBUG" "OFF" "OK" "No Laravel debug page detected"
      fi ;;

    rails)
      local ri_code; ri_code=$($CURL -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/rails/info/properties" 2>/dev/null)
      [[ "$ri_code" == "200" ]] \
        && add_check "RAILS" "/rails/info/properties" "EXPOSED" "CRITICAL" "Rails info endpoint accessible in production — exposes Ruby, Rails, and app properties" \
        || add_check "RAILS" "/rails/info/properties" "PROTECTED" "OK" "Returns $ri_code" ;;
  esac

  local sec_code; sec_code=$($CURL -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -A "$ua" "${TARGET_URL}/.well-known/security.txt" 2>/dev/null)
  [[ "$sec_code" == "200" ]] \
    && add_check "GENERAL" "security.txt" "PRESENT" "OK" "Security disclosure policy found" \
    || add_check "GENERAL" "security.txt" "MISSING" "INFO" "No security.txt — consider adding (RFC 9116)" "INFO" "no"
}

# ── Display ───────────────────────────────────────────────────────

print_check_section() {
  local category="$1" title="$2"
  echo ""; echo "  [$title]"
  local found=0 check
  for check in "${SEC_CHECKS[@]}"; do
    parse_check "$check"
    [[ "$PC_CAT" != "$category" ]] && continue
    found=1
    local icon sev_c
    case "$PC_SEV" in
      CRITICAL)         icon="✗"; sev_c=$(severity_color CRITICAL) ;;
      HIGH)             icon="✗"; sev_c=$(severity_color HIGH)     ;;
      MEDIUM)           icon="!"; sev_c=$(severity_color MEDIUM)   ;;
      LOW|INFO)         icon="i"; sev_c=$(severity_color "$PC_SEV")   ;;
      OK|*PROTECTED*|SUPPORTED|PRESENT|SECURE|OFF|NONE_FOUND|EXPECTED)
                        icon="✓"; sev_c=$(severity_color OK)       ;;
      *)                icon=" "; sev_c="$PC_SEV"                     ;;
    esac
    printf "  %s  %-44s [%-8b] [%s] %s\n" "$icon" "${PC_ITEM:0:44}" "$sev_c" "$PC_CLASS" "${PC_DETAIL:0:72}"
  done
  [[ $found -eq 0 ]] && echo "    (no results)"
}

print_security_summary() {
  local -a crits highs meds lows infos verifies expecteds
  local check
  for check in "${SEC_CHECKS[@]}"; do
    parse_check "$check"
    case "$PC_CLASS" in
      ACTION)
        case "$PC_STATUS" in OK|PROTECTED*|REJECTED|SUPPORTED|PRESENT|SECURE|OFF|NONE_FOUND|EXPECTED) continue ;; esac
        local entry="$PC_ITEM — $PC_DETAIL"
        case "$PC_SEV" in
          CRITICAL) crits+=("$entry") ;; HIGH) highs+=("$entry") ;;
          MEDIUM) meds+=("$entry") ;; LOW) lows+=("$entry") ;;
          *) infos+=("$entry") ;;
        esac ;;
      VERIFY)
        case "$PC_STATUS" in OK|PROTECTED*|REJECTED|SUPPORTED|PRESENT|SECURE|OFF|NONE_FOUND) continue ;; esac
        verifies+=("$PC_ITEM — $PC_DETAIL") ;;
      EXPECTED)
        expecteds+=("$PC_ITEM — $PC_DETAIL") ;;
      INFO)
        case "$PC_STATUS" in OK|PROTECTED*|REJECTED|SUPPORTED|PRESENT|SECURE|OFF|NONE_FOUND|EXPECTED) continue ;; esac
        infos+=("$PC_ITEM — $PC_DETAIL") ;;
    esac
  done

  echo ""; echo "── Security Findings by Class ────────────────────────"
  [[ ${#crits[@]}  -gt 0 ]] && { color_echo "${RED}  ACTION — CRITICAL (${#crits[@]}):${RST}";  for f in "${crits[@]}";  do echo "    • $f"; done; echo ""; }
  [[ ${#highs[@]}  -gt 0 ]] && { color_echo "${RED}  ACTION — HIGH (${#highs[@]}):${RST}";      for f in "${highs[@]}";  do echo "    • $f"; done; echo ""; }
  [[ ${#meds[@]}   -gt 0 ]] && { color_echo "${YLW}  ACTION — MEDIUM (${#meds[@]}):${RST}";     for f in "${meds[@]}";   do echo "    • $f"; done; echo ""; }
  [[ ${#lows[@]}   -gt 0 ]] && { color_echo "${BLU}  ACTION — LOW (${#lows[@]}):${RST}";        for f in "${lows[@]}";   do echo "    • $f"; done; echo ""; }
  [[ ${#verifies[@]} -gt 0 ]] && { color_echo "${CYN}  VERIFY (${#verifies[@]}):${RST}";        for f in "${verifies[@]}"; do echo "    • $f"; done; echo ""; }
  [[ ${#expecteds[@]} -gt 0 ]] && { color_echo "${GRN}  EXPECTED (${#expecteds[@]}):${RST}";     for f in "${expecteds[@]}"; do echo "    • $f"; done; echo ""; }
  [[ ${#infos[@]}  -gt 0 ]] && { color_echo "${CYN}  INFO (${#infos[@]}):${RST}";              for f in "${infos[@]}";  do echo "    • $f"; done; echo ""; }
  [[ ${#crits[@]} -eq 0 && ${#highs[@]} -eq 0 && ${#meds[@]} -eq 0 && ${#lows[@]} -eq 0 && ${#verifies[@]} -eq 0 && ${#infos[@]} -eq 0 ]] && color_echo "  ${GRN}No issues found.${RST}"
}

compute_scores() {
  local check
  SCORE_HYGIENE=100
  SCORE_EXPOSURE=100
  SCORE_ACTION_CRIT=0 SCORE_ACTION_HIGH=0 SCORE_ACTION_MED=0 SCORE_ACTION_LOW=0
  SCORE_VERIFY=0 SCORE_EXPECTED=0 SCORE_EXPOSED=0 SCORE_SENSITIVE=0

  for check in "${SEC_CHECKS[@]}"; do
    parse_check "$check"
    case "$PC_STATUS" in OK|PROTECTED*|REJECTED|SUPPORTED|PRESENT|SECURE|OFF|NONE_FOUND|EXPECTED) continue ;; esac
    case "$PC_CLASS" in
      ACTION)
        [[ "$PC_SCORED" != "yes" ]] && continue
        case "$PC_SEV" in
          CRITICAL) SCORE_ACTION_CRIT=$((SCORE_ACTION_CRIT+1)); SCORE_HYGIENE=$((SCORE_HYGIENE-25)) ;;
          HIGH)     SCORE_ACTION_HIGH=$((SCORE_ACTION_HIGH+1)); SCORE_HYGIENE=$((SCORE_HYGIENE-10)) ;;
          MEDIUM)   SCORE_ACTION_MED=$((SCORE_ACTION_MED+1));  SCORE_HYGIENE=$((SCORE_HYGIENE-4)) ;;
          LOW)      SCORE_ACTION_LOW=$((SCORE_ACTION_LOW+1));   SCORE_HYGIENE=$((SCORE_HYGIENE-1)) ;;
        esac ;;
      VERIFY)  SCORE_VERIFY=$((SCORE_VERIFY+1)) ;;
      EXPECTED) SCORE_EXPECTED=$((SCORE_EXPECTED+1)) ;;
    esac
  done

  local i total=${#R_PATH[@]}
  for (( i=0; i<total; i++ )); do
    if is_scored_exposure "${R_PATH[$i]}" "${R_NOTE[$i]}"; then
      SCORE_SENSITIVE=$((SCORE_SENSITIVE+1))
      SCORE_EXPOSURE=$((SCORE_EXPOSURE-25))
    elif is_unexpected_exposure "${R_PATH[$i]}" "${R_NOTE[$i]}" && ! is_sensitive_path "${R_PATH[$i]}"; then
      SCORE_EXPOSED=$((SCORE_EXPOSED+1))
    fi
  done

  [[ $SCORE_HYGIENE -lt 0 ]] && SCORE_HYGIENE=0
  [[ $SCORE_EXPOSURE -lt 0 ]] && SCORE_EXPOSURE=0
}

score_color_for() {
  local s="$1"
  if [[ $s -ge 80 ]]; then printf '#22c55e'
  elif [[ $s -ge 60 ]]; then printf '#eab308'
  elif [[ $s -ge 40 ]]; then printf '#f97316'
  else printf '#ef4444'
  fi
}

html_emit_findings_for_class() {
  local want_class="$1" heading="$2" heading_color="$3"
  local check has=0 fix bc
  for check in "${SEC_CHECKS[@]}"; do
    parse_check "$check"
    [[ "$PC_CLASS" != "$want_class" ]] && continue
    if [[ "$want_class" != "EXPECTED" ]]; then
      case "$PC_STATUS" in OK|PROTECTED*|REJECTED|SUPPORTED|PRESENT|SECURE|OFF|NONE_FOUND|EXPECTED) continue ;; esac
    fi
    if [[ $has -eq 0 ]]; then
      has=1
      echo "<h2 style=\"color:${heading_color}\">${heading}</h2>"
    fi
    fix=$(get_remediation "$PC_CAT" "$PC_ITEM" "$PC_SEV" "$PC_DETAIL")
    bc="$heading_color"
    echo "<div class=\"finding\" style=\"border-left-color:${bc}\">"
    echo "  <span class=\"badge sev-${PC_SEV}\">${PC_SEV}</span>"
    echo "  <span class=\"badge sev-${PC_CLASS}\" style=\"margin-left:6px\">${PC_CLASS}</span>"
    echo "  <div class=\"title\">$(html_escape "$PC_ITEM")</div>"
    echo "  <div class=\"detail\">$(html_escape "$PC_DETAIL")</div>"
    echo "  <div class=\"fix\"><div class=\"fix-label\">Recommended Action</div>$(html_escape "$fix")</div>"
    echo "</div>"
  done
}

html_emit_artifacts_section() {
  local rule loc note

  echo "<h2>Discovered Artifacts &amp; Policy Details</h2>"
  echo "<p style=\"color:var(--muted);margin-bottom:16px\">Parsed robots.txt, security.txt, sitemap, transport chain, and header policy breakdown.</p>"

  if [[ -n "$ARTIFACT_REDIRECT_CHAIN" ]]; then
    echo "<h3>Redirect Chain</h3>"
    echo "<pre class=\"artifact-block\">$(html_escape "$ARTIFACT_REDIRECT_CHAIN")</pre>"
  fi

  if [[ -n "$ARTIFACT_HSTS_DETAIL" || -n "$ARTIFACT_CSP_DETAIL" ]]; then
    echo "<h3>Header Policy Parse</h3>"
    [[ -n "$ARTIFACT_HSTS_DETAIL" ]] && echo "<p><strong>HSTS:</strong> $(html_escape "$ARTIFACT_HSTS_DETAIL")</p>"
    [[ -n "$ARTIFACT_CSP_DETAIL" ]] && echo "<p><strong>CSP:</strong></p><pre class=\"artifact-block\">$(html_escape "$ARTIFACT_CSP_DETAIL")</pre>"
  fi

  if [[ -n "$ARTIFACT_ROBOTS_RAW" ]]; then
    echo "<h3>robots.txt</h3>"
    if [[ ${#ARTIFACT_ROBOTS_DISALLOW[@]} -gt 0 ]]; then
      echo "<p><strong>Disallow rules (${#ARTIFACT_ROBOTS_DISALLOW[@]}):</strong></p><ul>"
      for rule in "${ARTIFACT_ROBOTS_DISALLOW[@]}"; do echo "<li><code>$(html_escape "$rule")</code></li>"; done
      echo "</ul>"
    fi
    if [[ ${#ARTIFACT_ROBOTS_ALLOW[@]} -gt 0 ]]; then
      echo "<p><strong>Allow rules (${#ARTIFACT_ROBOTS_ALLOW[@]}):</strong></p><ul>"
      for rule in "${ARTIFACT_ROBOTS_ALLOW[@]}"; do echo "<li><code>$(html_escape "$rule")</code></li>"; done
      echo "</ul>"
    fi
    if [[ ${#ARTIFACT_ROBOTS_SITEMAPS[@]} -gt 0 ]]; then
      echo "<p><strong>Sitemap URLs:</strong></p><ul>"
      for rule in "${ARTIFACT_ROBOTS_SITEMAPS[@]}"; do echo "<li>$(html_escape "$rule")</li>"; done
      echo "</ul>"
    fi
    echo "<details><summary>Raw robots.txt</summary><pre class=\"artifact-block\">$(html_escape "$ARTIFACT_ROBOTS_RAW")</pre></details>"
  fi

  if [[ -n "$ARTIFACT_SECURITY_TXT" ]]; then
    echo "<h3>security.txt (parsed)</h3>"
    echo "<pre class=\"artifact-block\">$(html_escape "$ARTIFACT_SECURITY_TXT")</pre>"
  fi

  if [[ ${#ARTIFACT_SITEMAP_LOCS[@]} -gt 0 ]]; then
    echo "<h3>sitemap.xml (parsed URLs, ${#ARTIFACT_SITEMAP_LOCS[@]})</h3><ul>"
    for loc in "${ARTIFACT_SITEMAP_LOCS[@]}"; do echo "<li><a href=\"$(html_escape "$loc")\" target=\"_blank\" rel=\"noopener\">$(html_escape "$loc")</a></li>"; done
    echo "</ul>"
    [[ -n "$ARTIFACT_SITEMAP_RAW" ]] && echo "<details><summary>Raw sitemap.xml (truncated)</summary><pre class=\"artifact-block\">$(html_escape "${ARTIFACT_SITEMAP_RAW:0:4000}")</pre></details>"
  fi

  if [[ ${#ARTIFACT_CORS_NOTES[@]} -gt 0 ]]; then
    echo "<h3>CORS Probes</h3><ul>"
    for note in "${ARTIFACT_CORS_NOTES[@]}"; do echo "<li>$(html_escape "$note")</li>"; done
    echo "</ul>"
  fi

  if [[ -n "$COMPARE_BASELINE_LABEL" ]]; then
    echo "<h3>Baseline Comparison</h3>"
    echo "<p>Baseline: <code>$(html_escape "$COMPARE_BASELINE_LABEL")</code></p>"
    echo "<p>Hygiene: ${COMPARE_PREV_HYGIENE:-?} → ${SCORE_HYGIENE} (${COMPARE_HYGIENE_DELTA:+}${COMPARE_HYGIENE_DELTA}) &nbsp;|&nbsp; Exposure: ${COMPARE_PREV_EXPOSURE:-?} → ${SCORE_EXPOSURE} (${COMPARE_EXPOSURE_DELTA:+}${COMPARE_EXPOSURE_DELTA})</p>"
    if [[ ${#COMPARE_NEW_ACTIONS[@]} -gt 0 ]]; then
      echo "<p><strong>New ACTION items vs baseline:</strong></p><ul>"
      for note in "${COMPARE_NEW_ACTIONS[@]}"; do echo "<li>$(html_escape "$note")</li>"; done
      echo "</ul>"
    else
      echo "<p class=\"status-ok\">No new ACTION items compared to baseline.</p>"
    fi
  fi
}

html_emit_misc_url_bucket() {
  local bucket="$1" title="$2" count="$3" show="$4" max="$5"
  local entry url source idx=0

  echo "<h3>${title} <span style=\"color:var(--muted);font-weight:400\">(${count} total)</span></h3>"
  if [[ "$show" -eq 0 ]]; then
    echo "<p class=\"status-info\">Hidden in report (<code>[misc] show_${bucket}_urls=no</code> in site config).</p>"
    return
  fi
  if [[ "$count" -eq 0 ]]; then
    echo "<p class=\"status-info\">None catalogued.</p>"
    return
  fi
  echo "<details open><summary>Click to expand/collapse URL list</summary>"
  echo "<ul class=\"misc-list\">"
  for entry in "${MISC_URLS[@]}"; do
    url="${entry%%|*}"; source="${entry#*|}"
    if [[ "$bucket" == probe ]]; then
      misc_source_is_probe "$source" || continue
    else
      misc_source_is_probe "$source" && continue
    fi
    idx=$((idx + 1))
    [[ $idx -gt $max ]] && break
    echo "<li><a href=\"$(html_escape "$url")\" target=\"_blank\" rel=\"noopener\">$(html_escape "$url")</a> <span style=\"color:var(--muted)\">[$(html_escape "$source")]</span></li>"
  done
  echo "</ul>"
  [[ $count -gt $max ]] && echo "<p style=\"color:var(--muted)\">Showing first ${max} of ${count} URLs.</p>"
  echo "</details>"
}

html_emit_misc_section() {
  local entry url src source page show max=250 idx=0

  echo "<h2>Miscellaneous</h2>"
  echo "<p style=\"color:var(--muted);margin-bottom:16px\">Site discovery from security probes and sampled site pages — URLs are clickable for manual review. <strong>Probe</strong> = generic security paths the audit tried (.env, /wp-admin/, …). <strong>Internal</strong> = your site routes (<code>site_config</code>), plus same-origin links from homepage, sitemap, robots, and sampled pages.</p>"

  echo "<h3>Designer / Creator</h3>"
  if [[ -n "$DESIGNER_NAME" ]]; then
    echo "<p><strong>$(html_escape "$DESIGNER_NAME")</strong>"
    echo " &nbsp;(<em>$(html_escape "$DESIGNER_SOURCE")</em>"
    if [[ $DESIGNER_HAS_PROPER -eq 1 ]]; then
      echo "; <span class=\"status-ok\">proper credit — thank you</span>"
    elif [[ $DESIGNER_HAS_RISK -eq 1 ]]; then
      echo "; <span class=\"status-warn\">risky placement detected</span>"
    else
      echo "; <span class=\"status-warn\">review placement</span>"
    fi
    echo ")</p>"
    if [[ ${#DESIGNER_TRACE[@]} -gt 0 ]]; then
      echo "<table><tr><th>Page</th><th>Placement</th><th>SEO impact</th><th>Note</th></tr>"
      for entry in "${DESIGNER_TRACE[@]}"; do
        local dpath="${entry%%|*}" dr="${entry#*|}"
        local dplace="${dr%%|*}"; dr="${dr#*|}"
        local dimpact="${dr%%|*}" dnote="${dr#*|}"
        echo "<tr><td><code>$(html_escape "$dpath")</code></td><td>$(html_escape "$dplace")</td><td>$(html_escape "$dimpact")</td><td>$(html_escape "$dnote")</td></tr>"
      done
      echo "</table>"
    fi
  else
    echo "<p class=\"status-info\">Not detected — no Designed by / Created by / Powered by pattern in sampled homepage HTML. Credit may be omitted, loaded via JavaScript, or present on pages not sampled.</p>"
  fi

  echo "<h3>Discovered URLs <span style=\"color:var(--muted);font-weight:400\">(${MISC_URL_COUNT} total · ${MISC_PROBE_URL_COUNT} probe · ${MISC_INTERNAL_URL_COUNT} internal)</span></h3>"

  html_emit_misc_url_bucket "probe" "Discovered Security Probe URLs" "$MISC_PROBE_URL_COUNT" "$CONFIG_MISC_SHOW_PROBE_URLS" "$CONFIG_MISC_MAX_PROBE_URLS"
  html_emit_misc_url_bucket "internal" "Discovered Internal URLs" "$MISC_INTERNAL_URL_COUNT" "$CONFIG_MISC_SHOW_INTERNAL_URLS" "$CONFIG_MISC_MAX_INTERNAL_URLS"

  echo "<h3>Images on sampled pages <span style=\"color:var(--muted);font-weight:400\">(${MISC_IMAGE_COUNT} unique · ${MISC_PAGES_SCANNED} page(s) scanned)</span></h3>"
  if [[ $MISC_IMAGE_COUNT -eq 0 ]]; then
    echo "<p class=\"status-info\">No &lt;img&gt; tags found in the first ${MISC_HTML_IMG_MAX} bytes of sampled pages (JS-rendered images not detected).</p>"
  else
    echo "<details open><summary>Click to expand/collapse image list</summary>"
    echo "<ul class=\"misc-list\">"
    idx=0
    for entry in "${MISC_IMAGES[@]}"; do
      idx=$((idx + 1))
      [[ $idx -gt $max ]] && break
      src="${entry%%|*}"; page="${entry#*|}"
      echo "<li><a href=\"$(html_escape "$src")\" target=\"_blank\" rel=\"noopener\">$(html_escape "$src")</a> <span style=\"color:var(--muted)\">on $(html_escape "$page")</span></li>"
    done
    echo "</ul>"
    [[ $MISC_IMAGE_COUNT -gt $max ]] && echo "<p style=\"color:var(--muted)\">Showing first ${max} of ${MISC_IMAGE_COUNT} images.</p>"
    echo "</details>"
  fi
}

# ── Write Logs ────────────────────────────────────────────────────

html_designer_meta_row() {
  local src_note="$DESIGNER_SOURCE"
  [[ -n "$DESIGNER_DISCOVERED_PATH" ]] && src_note="${DESIGNER_SOURCE} at ${DESIGNER_DISCOVERED_PATH}"
  echo "    <dt>Designer / Creator</dt><dd>"
  if [[ -n "$DESIGNER_NAME" ]]; then
    echo -n "      <strong>$(html_escape "$DESIGNER_NAME")</strong>"
    case "$DESIGNER_HEADER_STATUS" in
      found_proper)
        echo " <span class=\"status-ok\">— proper credit ($(html_escape "$src_note"))</span>" ;;
      found_mixed)
        echo " <span class=\"status-ok\">— proper credit ($(html_escape "$src_note"))</span>"
        echo " <span class=\"status-warn\">· also flagged in risky placement (see Action items)</span>" ;;
      found_risky)
        echo " <span class=\"status-warn\">— risky placement only ($(html_escape "$src_note")); see Action items</span>" ;;
      *)
        echo " <span style=\"color:var(--muted)\">($(html_escape "$src_note") — verify in Miscellaneous)</span>" ;;
    esac
  else
    echo -n "      <span style=\"color:var(--muted)\">Not detected</span>"
    echo " <span style=\"color:var(--muted);font-size:0.92em\">— no credit pattern on homepage or probed open paths</span>"
  fi
  echo ""
  echo "    </dd>"
}

write_html_report() {
  local framework="$1"
  local now=$("$DATE")
  local total=${#R_PATH[@]}
  local ok=0 check hygiene_color exposure_color i cls path_label

  compute_scores
  hygiene_color=$(score_color_for "$SCORE_HYGIENE")
  exposure_color=$(score_color_for "$SCORE_EXPOSURE")

  for check in "${SEC_CHECKS[@]}"; do
    parse_check "$check"
    case "$PC_STATUS" in OK|PROTECTED*|REJECTED|SUPPORTED|PRESENT|SECURE|OFF|NONE_FOUND|EXPECTED) ok=$((ok+1)) ;; esac
  done

  {
    cat <<'HTMLHEAD'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Website Security Audit Report</title>
<style>
  :root { --bg:#0f172a; --card:#1e293b; --text:#e2e8f0; --muted:#94a3b8; --border:#334155; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg); color:var(--text); line-height:1.6; padding:24px; }
  .container { max-width:960px; margin:0 auto; }
  h1 { font-size:1.75rem; margin-bottom:8px; }
  h2 { font-size:1.25rem; margin:32px 0 16px; border-bottom:1px solid var(--border); padding-bottom:8px; }
  h3 { font-size:1rem; margin:20px 0 10px; }
  .subtitle { color:var(--muted); margin-bottom:24px; }
  .disclaimer { background:#1e3a5f; border:1px solid #334155; border-radius:10px; padding:14px 18px; margin:16px 0; font-size:0.9rem; color:#93c5fd; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:12px; margin:20px 0; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:16px; text-align:center; }
  .card .num { font-size:2rem; font-weight:700; }
  .card .lbl { font-size:0.75rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.05em; }
  .score-ring { font-size:2.2rem; font-weight:800; }
  .meta { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:20px; margin:16px 0; }
  .meta dt { color:var(--muted); font-size:0.85rem; }
  .meta dd { margin:0 0 12px; font-weight:500; }
  .finding { background:var(--card); border-left:4px solid var(--border); border-radius:0 8px 8px 0; padding:16px; margin:12px 0; }
  .finding .title { font-weight:600; margin-bottom:4px; }
  .finding .detail { color:var(--muted); font-size:0.9rem; margin-bottom:8px; }
  .finding .fix { background:#0f172a; border-radius:6px; padding:10px 14px; font-size:0.9rem; }
  .fix-label { color:#60a5fa; font-weight:600; font-size:0.8rem; text-transform:uppercase; margin-bottom:4px; }
  .badge { display:inline-block; padding:2px 10px; border-radius:99px; font-size:0.75rem; font-weight:700; text-transform:uppercase; }
  .sev-CRITICAL { background:#7f1d1d; color:#fca5a5; }
  .sev-HIGH     { background:#7c2d12; color:#fdba74; }
  .sev-MEDIUM   { background:#713f12; color:#fde047; }
  .sev-LOW      { background:#1e3a5f; color:#93c5fd; }
  .sev-INFO     { background:#1e293b; color:#94a3b8; }
  .sev-OK       { background:#14532d; color:#86efac; }
  .sev-ACTION   { background:#7c2d12; color:#fdba74; }
  .sev-VERIFY   { background:#1e3a5f; color:#93c5fd; }
  .sev-EXPECTED { background:#14532d; color:#86efac; }
  table { width:100%; border-collapse:collapse; font-size:0.85rem; margin:12px 0; }
  th { background:var(--card); color:var(--muted); text-align:left; padding:8px 10px; border-bottom:1px solid var(--border); }
  td { padding:7px 10px; border-bottom:1px solid var(--border); word-break:break-all; }
  tr:hover td { background:rgba(255,255,255,0.03); }
  .status-open { color:#f87171; font-weight:600; }
  .status-ok   { color:#86efac; }
  .status-warn { color:#fde047; }
  .status-info { color:#94a3b8; }
  .legend { display:flex; flex-wrap:wrap; gap:12px; margin:16px 0; font-size:0.85rem; color:var(--muted); }
  .toolbar { display:flex; flex-wrap:wrap; align-items:center; gap:12px; margin:16px 0 24px; padding:12px 16px; background:var(--card); border:1px solid var(--border); border-radius:10px; }
  .toolbar button { background:#2563eb; color:#fff; border:none; border-radius:8px; padding:10px 18px; font-size:0.9rem; font-weight:600; cursor:pointer; }
  .toolbar button:hover { background:#1d4ed8; }
  .toolbar-hint { color:var(--muted); font-size:0.85rem; }
  .artifact-block { background:#0f172a; border:1px solid var(--border); border-radius:8px; padding:14px; overflow-x:auto; font-size:0.8rem; line-height:1.5; white-space:pre-wrap; word-break:break-word; margin:8px 0 16px; }
  details { margin:12px 0; }
  summary { cursor:pointer; color:#93c5fd; font-weight:600; margin-bottom:8px; }
  footer { margin-top:40px; padding-top:16px; border-top:1px solid var(--border); color:var(--muted); font-size:0.8rem; }
  .misc-list { max-height:420px; overflow-y:auto; margin:12px 0; padding-left:20px; font-size:0.85rem; }
  .misc-list li { margin:6px 0; word-break:break-all; }
  .misc-list a { color:#93c5fd; }
  @media print {
    * { -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }
    body { background:var(--bg) !important; color:var(--text) !important; padding:12px; }
    .container { max-width:100%; }
    .no-print { display:none !important; }
    .card, .meta, .finding, .toolbar, details { break-inside:avoid; }
    tr:hover td { background:transparent !important; }
  }
</style>
</head>
<body>
<div class="container">
HTMLHEAD

    echo "  <div class=\"toolbar no-print\">"
    echo "    <button type=\"button\" onclick=\"window.print()\">Save as PDF</button>"
    echo "    <span class=\"toolbar-hint\">Opens the print dialog — choose &quot;Save as PDF&quot;. Enable <strong>Background graphics</strong> so the dark theme and colors print correctly.</span>"
    echo "  </div>"
    echo "  <h1>Website Security Audit Report</h1>"
    echo "  <p class=\"subtitle\">Passive scan — headers, paths, cookies, TLS. Does not test authenticated flows or CDN dashboard rules.</p>"
    echo "  <div class=\"disclaimer\"><strong>How to read this report:</strong> Only <strong>ACTION</strong> items (scored) affect the Hygiene score. <strong>VERIFY</strong> means check your CDN/server config. <strong>EXPECTED</strong> is normal framework behavior (e.g. admin login page, Django csrftoken).</div>"
    echo ""
    echo "  <div class=\"cards\">"
    echo "    <div class=\"card\"><div class=\"score-ring\" style=\"color:${hygiene_color}\">${SCORE_HYGIENE}</div><div class=\"lbl\">Hygiene / 100</div></div>"
    echo "    <div class=\"card\"><div class=\"score-ring\" style=\"color:${exposure_color}\">${SCORE_EXPOSURE}</div><div class=\"lbl\">Exposure / 100</div></div>"
    echo "    <div class=\"card\"><div class=\"num\" style=\"color:#ef4444\">${SCORE_ACTION_CRIT}</div><div class=\"lbl\">Critical</div></div>"
    echo "    <div class=\"card\"><div class=\"num\" style=\"color:#f97316\">${SCORE_ACTION_HIGH}</div><div class=\"lbl\">High Action</div></div>"
    echo "    <div class=\"card\"><div class=\"num\" style=\"color:#eab308\">${SCORE_ACTION_MED}</div><div class=\"lbl\">Medium</div></div>"
    echo "    <div class=\"card\"><div class=\"num\" style=\"color:#60a5fa\">${SCORE_VERIFY}</div><div class=\"lbl\">Verify</div></div>"
    echo "    <div class=\"card\"><div class=\"num\" style=\"color:#86efac\">${SCORE_EXPECTED}</div><div class=\"lbl\">Expected</div></div>"
    echo "    <div class=\"card\"><div class=\"num\" style=\"color:#f87171\">${SCORE_SENSITIVE}</div><div class=\"lbl\">Sensitive Leaks</div></div>"
    echo "  </div>"
    echo ""
    echo "  <dl class=\"meta\">"
    echo "    <dt>Website</dt><dd><a href=\"$(html_escape "$TARGET_URL")\" target=\"_blank\" rel=\"noopener\">$(html_escape "$TARGET_URL")</a></dd>"
    html_designer_meta_row
    echo "    <dt>Scan Date</dt><dd>$(html_escape "$now")</dd>"
    echo "    <dt>Report Schema</dt><dd>2.5</dd>"
    echo "    <dt>Platform Detected</dt><dd>$(html_escape "$framework") (${FRAMEWORK_CONFIDENCE} confidence)</dd>"
    echo "    <dt>Technology</dt><dd>$(html_escape "$LANGUAGE_DETECTED")</dd>"
    echo "    <dt>CDN / Protection</dt><dd>$(html_escape "$CDN_DETECTED")</dd>"
    echo "    <dt>Server</dt><dd>$(html_escape "$SERVER_HEADER")</dd>"
    echo "    <dt>Audit Machine</dt><dd>$(html_escape "$SYS_HOST") ($(html_escape "$SYS_ARCH"))</dd>"
    echo "    <dt>Operating System</dt><dd>$(html_escape "$SYS_OS_FULL")</dd>"
    echo "    <dt>Shell</dt><dd>$(html_escape "$SYS_SHELL")</dd>"
    echo "    <dt>Session</dt><dd>$(html_escape "$RUN_SESSION_DIR")</dd>"
    echo "    <dt>Report Files</dt><dd>$(html_escape "$(basename "$LOG_HTML")")</dd>"
    echo "  </dl>"
    echo ""
    echo "  <div class=\"legend\">"
    echo "    <span><strong>ACTION</strong> — fix or harden (affects Hygiene score)</span>"
    echo "    <span><strong>VERIFY</strong> — may be OK at CDN; confirm manually</span>"
    echo "    <span><strong>EXPECTED</strong> — normal public behavior</span>"
    echo "    <span><strong>INFO</strong> — optional improvement</span>"
    echo "  </div>"

    html_emit_findings_for_class "ACTION" "Action Required" "#f97316"
    html_emit_findings_for_class "VERIFY" "Verify Manually" "#60a5fa"
    html_emit_findings_for_class "EXPECTED" "Expected Behavior" "#86efac"
    html_emit_findings_for_class "INFO" "Informational" "#94a3b8"

    html_emit_artifacts_section
    html_emit_misc_section

    echo "<h2>Sensitive Path Leaks</h2>"
    echo "<p style=\"color:var(--muted);margin-bottom:12px\">Sensitive files that returned a publicly accessible response (critical if any).</p>"
    echo "<table><tr><th>Path</th><th>Classification</th><th>HTTP Code</th></tr>"
    local sensitive_rows=0
    for (( i=0; i<total; i++ )); do
      is_scored_exposure "${R_PATH[$i]}" "${R_NOTE[$i]}" || continue
      sensitive_rows=$((sensitive_rows+1))
      echo "<tr><td>$(html_escape "${R_PATH[$i]}")</td><td class=\"status-open\">Sensitive leak</td><td>${R_FINAL[$i]}</td></tr>"
    done
    [[ $sensitive_rows -eq 0 ]] && echo "<tr><td colspan=\"3\" class=\"status-ok\">None detected</td></tr>"
    echo "</table>"

    echo "<h2>Other Open Paths</h2>"
    echo "<p style=\"color:var(--muted);margin-bottom:12px\">Public endpoints that are usually intentional (login surfaces, robots.txt) or need manual review.</p>"
    echo "<table><tr><th>Path</th><th>Classification</th><th>HTTP Code</th></tr>"
    local other_rows=0
    for (( i=0; i<total; i++ )); do
      [[ "${R_NOTE[$i]}" == "OPEN" ]] || continue
      is_scored_exposure "${R_PATH[$i]}" "${R_NOTE[$i]}" && continue
      other_rows=$((other_rows+1))
      if is_login_surface "${R_PATH[$i]}"; then path_label="Login surface (expected)"
      elif is_app_surface "${R_PATH[$i]}"; then path_label="App surface (config)"
      elif is_public_by_design "${R_PATH[$i]}"; then path_label="Public by design"
      else path_label="Review manually"; fi
      cls="status-info"
      is_login_surface "${R_PATH[$i]}" || is_public_by_design "${R_PATH[$i]}" && cls="status-ok"
      echo "<tr><td>$(html_escape "${R_PATH[$i]}")</td><td class=\"${cls}\">${path_label}</td><td>${R_FINAL[$i]}</td></tr>"
    done
    [[ $other_rows -eq 0 ]] && echo "<tr><td colspan=\"3\" class=\"status-ok\">None</td></tr>"
    echo "</table>"

    echo "<h2>All Path Probes</h2>"
    echo "<table><tr><th>Path</th><th>Result</th><th>Raw</th><th>Final</th></tr>"
    for (( i=0; i<total; i++ )); do
      cls="status-ok"
      if is_scored_exposure "${R_PATH[$i]}" "${R_NOTE[$i]}"; then cls="status-open"
      elif [[ "${R_NOTE[$i]}" == "OPEN" ]] && ! is_expected_open "${R_PATH[$i]}"; then cls="status-warn"
      elif [[ "${R_NOTE[$i]}" == REDIRECT ]]; then cls="status-warn"
      fi
      echo "<tr><td>$(html_escape "${R_PATH[$i]}")</td><td class=\"${cls}\">${R_NOTE[$i]}</td><td>${R_RAW[$i]}</td><td>${R_FINAL[$i]}</td></tr>"
    done
    echo "</table>"

    if [[ ${#VERSIONS_FOUND[@]} -gt 0 ]]; then
      echo "<h2>Software Versions Detected</h2><ul>"
      for v in "${VERSIONS_FOUND[@]}"; do
        echo "<li>$(html_escape "$v")</li>"
      done
      echo "</ul>"
    fi

    echo "<h2>Passed Checks (${ok})</h2>"
    echo "<table><tr><th>Category</th><th>Check</th><th>Result</th><th>Class</th></tr>"
    for check in "${SEC_CHECKS[@]}"; do
      parse_check "$check"
      case "$PC_STATUS" in OK|PROTECTED*|REJECTED|SUPPORTED|PRESENT|SECURE|OFF|NONE_FOUND|EXPECTED)
        echo "<tr><td>$(html_escape "$PC_CAT")</td><td>$(html_escape "$PC_ITEM")</td><td class=\"status-ok\">$(html_escape "$PC_STATUS")</td><td>$(html_escape "$PC_CLASS")</td></tr>"
      ;; esac
    done
    echo "</table>"

    echo "  <footer>"
    echo "    Created by <a href=\"$(html_escape "$BRAND_APP")\" target=\"_blank\" rel=\"noopener\">muzar.io</a>"
    echo "    &mdash; Web Security Audit Tool v${TOOL_VERSION} &mdash; $(html_escape "$now")<br>"
    echo "    Host: $(html_escape "$SYS_HOST") | Arch: $(html_escape "$SYS_ARCH") | Shell: $(html_escape "$SYS_SHELL")<br>"
    echo "    Passive scan only. Does not replace authenticated testing or CDN/WAF dashboard review."
    echo "  </footer>"
    echo "</div>"
    echo "</body>"
    echo "</html>"

  } > "$LOG_HTML"
}

write_logs() {
  local framework="$1"
  local now=$("$DATE")
  local now_utc=$("$DATE" -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || "$DATE" +"%Y-%m-%dT%H:%M:%SZ")
  local total=${#R_PATH[@]} sc_total=${#SEC_CHECKS[@]}

  {
    echo "========================================"
    echo " Web Security Audit Report v${TOOL_VERSION} — ${BRAND_VENDOR}"
    echo "========================================"
    echo " Target      : $TARGET_URL"; echo " Framework   : $framework ($FRAMEWORK_CONFIDENCE)"
    echo " Language    : $LANGUAGE_DETECTED"; echo " CDN         : $CDN_DETECTED"
    echo " Server      : $SERVER_HEADER"; echo " UA Used     : $EFFECTIVE_UA"
    echo " Date        : $now"
    echo " URL Slug    : $URL_SLUG"
    echo " Log Dir     : $URL_LOG_DIR"
    echo "----------------------------------------"
    system_info_txt
    echo "========================================"
    echo ""
    printf "%-45s | %-8s | %-8s | %s\n" "PATH" "RAW" "FINAL" "STATUS"
    echo "──────────────────────────────────────────────────────────────────"
    for (( i=0; i<total; i++ )); do
      printf "%-45s | %-8s | %-8s | %s\n" "${R_PATH[$i]}" "${R_RAW[$i]}" "${R_FINAL[$i]}" "${R_NOTE[$i]}"
    done
    echo ""
    echo "── Security Checks ─────────────────────────────────────────────"
    printf "%-20s | %-36s | %-8s | %-8s | %-8s | %s\n" "CATEGORY" "ITEM" "STATUS" "SEV" "CLASS" "DETAIL"
    echo "──────────────────────────────────────────────────────────────────────────"
    for check in "${SEC_CHECKS[@]}"; do
      parse_check "$check"
      printf "%-20s | %-36s | %-8s | %-8s | %-8s | %s\n" "$PC_CAT" "${PC_ITEM:0:36}" "$PC_STATUS" "$PC_SEV" "$PC_CLASS" "$PC_DETAIL"
    done
    echo ""
    echo "── Versions ────────────────────────────────────────────────────"
    [[ ${#VERSIONS_FOUND[@]} -gt 0 ]] && { for v in "${VERSIONS_FOUND[@]}"; do echo "  $v"; done; } || echo "  None detected"
    echo ""
    echo "── Miscellaneous ───────────────────────────────────────────────"
    echo "  URLs total        : ${MISC_URL_COUNT} (${MISC_PROBE_URL_COUNT} probe · ${MISC_INTERNAL_URL_COUNT} internal)"
    echo "  Images (unique) : ${MISC_IMAGE_COUNT} on ${MISC_PAGES_SCANNED} page(s)"
    [[ -n "$DESIGNER_NAME" ]] && echo "  Designer        : ${DESIGNER_NAME} (${DESIGNER_SOURCE}; proper=${DESIGNER_HAS_PROPER}; risk=${DESIGNER_HAS_RISK})" \
      || echo "  Designer        : Not detected (no credit pattern in homepage sample)"
    report_attribution_txt "$now"
  } > "$LOG_TXT"

  {
    echo "{"
    echo "  \"target\": \"$TARGET_URL\","
    echo "  \"url_slug\": \"$URL_SLUG\","
    echo "  \"log_dir\": \"$URL_LOG_DIR\","
    echo "  \"report_base\": \"audit_${URL_SLUG}_${RUN_DATE}_${RUN_TIMESTAMP}\","
    echo "  \"framework\": \"$framework\","
    echo "  \"framework_confidence\": \"$FRAMEWORK_CONFIDENCE\","
    echo "  \"language\": \"$LANGUAGE_DETECTED\","
    echo "  \"cdn\": \"$CDN_DETECTED\","
    echo "  \"server\": \"$SERVER_HEADER\","
    echo "  \"ua_used\": \"$EFFECTIVE_UA\","
    echo "  \"timestamp\": \"$now_utc\","
    echo "  \"run_date\": \"$RUN_DATE\","
    echo "  \"run_timestamp\": \"$RUN_TIMESTAMP\","
    echo "  \"report_schema\": \"2.5\","
    [[ -n "$TARGET_AUDIT_CONFIG" ]] && echo "  \"audit_config\": \"$(json_escape_str "$TARGET_AUDIT_CONFIG")\","
    echo "  \"session_dir\": \"$RUN_SESSION_DIR\","
    compute_scores
    echo "  \"scores\": {"
    echo "    \"hygiene\": ${SCORE_HYGIENE},"
    echo "    \"exposure\": ${SCORE_EXPOSURE},"
    echo "    \"action_critical\": ${SCORE_ACTION_CRIT},"
    echo "    \"action_high\": ${SCORE_ACTION_HIGH},"
    echo "    \"action_medium\": ${SCORE_ACTION_MED},"
    echo "    \"verify\": ${SCORE_VERIFY},"
    echo "    \"expected\": ${SCORE_EXPECTED},"
    echo "    \"sensitive_leaks\": ${SCORE_SENSITIVE}"
    echo "  },"
    echo "  \"audit_host\": {"
    echo "    \"hostname\": \"$(json_escape_str "$SYS_HOST")\","
    echo "    \"architecture\": \"$(json_escape_str "$SYS_ARCH")\","
    echo "    \"os\": \"$(json_escape_str "$SYS_OS")\","
    echo "    \"os_full\": \"$(json_escape_str "$SYS_OS_FULL")\","
    echo "    \"kernel\": \"$(json_escape_str "$SYS_KERNEL")\","
    echo "    \"shell\": \"$(json_escape_str "$SYS_SHELL")\","
    echo "    \"uname\": \"$(json_escape_str "$SYS_UNAME")\""
    echo "  },"
    echo "  \"path_results\": ["
    for (( i=0; i<total; i++ )); do
      local comma=","; [[ $i -eq $((total - 1)) ]] && comma=""
      echo "    {\"path\":\"${R_PATH[$i]}\",\"raw\":\"${R_RAW[$i]}\",\"final\":\"${R_FINAL[$i]}\",\"status\":\"${R_NOTE[$i]}\"}${comma}"
    done
    echo "  ],"
    echo "  \"security_checks\": ["
    for (( i=0; i<sc_total; i++ )); do
      local comma=","; [[ $i -eq $((sc_total - 1)) ]] && comma=""
      parse_check "${SEC_CHECKS[$i]}"
      local dt="${PC_DETAIL//\"/\\\"}"
      echo "    {\"category\":\"$PC_CAT\",\"item\":\"${PC_ITEM}\",\"status\":\"$PC_STATUS\",\"severity\":\"$PC_SEV\",\"class\":\"$PC_CLASS\",\"scored\":\"$PC_SCORED\",\"detail\":\"${dt}\"}${comma}"
    done
    echo "  ],"
    echo "  \"artifacts\": {"
    echo "    \"redirect_chain\": \"$(json_escape_str "$ARTIFACT_REDIRECT_CHAIN")\","
    echo "    \"hsts_detail\": \"$(json_escape_str "$ARTIFACT_HSTS_DETAIL")\","
    echo "    \"csp_detail\": \"$(json_escape_str "${ARTIFACT_CSP_DETAIL:0:800}")\","
    echo "    \"robots_txt\": \"$(json_escape_str "${ARTIFACT_ROBOTS_RAW:0:4000}")\","
    echo "    \"robots_disallow\": ["
    local rd=${#ARTIFACT_ROBOTS_DISALLOW[@]} ri
    for (( ri=0; ri<rd; ri++ )); do
      local comma=","; [[ $ri -eq $((rd - 1)) ]] && comma=""
      echo "      \"$(json_escape_str "${ARTIFACT_ROBOTS_DISALLOW[$ri]}")\"${comma}"
    done
    echo "    ],"
    echo "    \"robots_sitemaps\": ["
    rd=${#ARTIFACT_ROBOTS_SITEMAPS[@]}
    for (( ri=0; ri<rd; ri++ )); do
      local comma=","; [[ $ri -eq $((rd - 1)) ]] && comma=""
      echo "      \"$(json_escape_str "${ARTIFACT_ROBOTS_SITEMAPS[$ri]}")\"${comma}"
    done
    echo "    ],"
    echo "    \"security_txt_parsed\": \"$(json_escape_str "$ARTIFACT_SECURITY_TXT")\","
    echo "    \"sitemap_sample\": ["
    rd=${#ARTIFACT_SITEMAP_LOCS[@]}
    for (( ri=0; ri<rd; ri++ )); do
      local comma=","; [[ $ri -eq $((rd - 1)) ]] && comma=""
      echo "      \"$(json_escape_str "${ARTIFACT_SITEMAP_LOCS[$ri]}")\"${comma}"
    done
    echo "    ],"
    echo "    \"cors_notes\": ["
    rd=${#ARTIFACT_CORS_NOTES[@]}
    for (( ri=0; ri<rd; ri++ )); do
      local comma=","; [[ $ri -eq $((rd - 1)) ]] && comma=""
      echo "      \"$(json_escape_str "${ARTIFACT_CORS_NOTES[$ri]}")\"${comma}"
    done
    echo "    ]"
    echo "  },"
    echo "  \"miscellaneous\": {"
    echo "    \"designer\": {"
    echo "      \"name\": \"$(json_escape_str "$DESIGNER_NAME")\","
    echo "      \"source\": \"$(json_escape_str "$DESIGNER_SOURCE")\","
    echo "      \"discovered_path\": \"$(json_escape_str "$DESIGNER_DISCOVERED_PATH")\","
    echo "      \"credit_link\": \"$(json_escape_str "$DESIGNER_LINK")\","
    echo "      \"credible\": ${DESIGNER_CREDIBLE:-0},"
    echo "      \"has_proper\": ${DESIGNER_HAS_PROPER:-0},"
    echo "      \"has_risk\": ${DESIGNER_HAS_RISK:-0},"
    echo "      \"header_status\": \"$(json_escape_str "${DESIGNER_HEADER_STATUS:-not_found}")\","
    echo "      \"summary\": \"$(json_escape_str "$ARTIFACT_DESIGNER_SUMMARY")\","
    echo "      \"trace\": ["
    rd=${#DESIGNER_TRACE[@]}
    for (( ri=0; ri<rd; ri++ )); do
      local comma=","; [[ $ri -eq $((rd - 1)) ]] && comma=""
      local tr="${DESIGNER_TRACE[$ri]}"
      local tr_path="${tr%%|*}"; local tr_r="${tr#*|}"
      local tr_place="${tr_r%%|*}"; tr_r="${tr_r#*|}"
      local tr_impact="${tr_r%%|*}"; local tr_note="${tr_r#*|}"
      echo "        {\"path\":\"$(json_escape_str "$tr_path")\",\"placement\":\"$(json_escape_str "$tr_place")\",\"seo_impact\":\"$(json_escape_str "$tr_impact")\",\"note\":\"$(json_escape_str "$tr_note")\"}${comma}"
    done
    echo "      ]"
    echo "    },"
    echo "    \"urls\": {"
    echo "      \"total\": ${MISC_URL_COUNT},"
    echo "      \"probe_total\": ${MISC_PROBE_URL_COUNT},"
    echo "      \"internal_total\": ${MISC_INTERNAL_URL_COUNT},"
    echo "      \"security_probes\": {"
    echo "        \"total\": ${MISC_PROBE_URL_COUNT},"
    echo "        \"items\": ["
    local probe_idx=0 probe_total=0
    rd=${#MISC_URLS[@]}
    for (( ri=0; ri<rd; ri++ )); do
      local mu="${MISC_URLS[$ri]}"
      local mu_url="${mu%%|*}"; local mu_src="${mu#*|}"
      misc_source_is_probe "$mu_src" || continue
      probe_total=$((probe_total + 1))
      local comma=","; [[ $probe_total -eq $MISC_PROBE_URL_COUNT ]] && comma=""
      echo "          {\"url\":\"$(json_escape_str "$mu_url")\",\"source\":\"$(json_escape_str "$mu_src")\"}${comma}"
    done
    echo "        ]"
    echo "      },"
    echo "      \"internal\": {"
    echo "        \"total\": ${MISC_INTERNAL_URL_COUNT},"
    echo "        \"items\": ["
    local internal_idx=0 internal_total=0
    for (( ri=0; ri<rd; ri++ )); do
      local mu="${MISC_URLS[$ri]}"
      local mu_url="${mu%%|*}"; local mu_src="${mu#*|}"
      misc_source_is_probe "$mu_src" && continue
      internal_total=$((internal_total + 1))
      local comma=","; [[ $internal_total -eq $MISC_INTERNAL_URL_COUNT ]] && comma=""
      echo "          {\"url\":\"$(json_escape_str "$mu_url")\",\"source\":\"$(json_escape_str "$mu_src")\"}${comma}"
    done
    echo "        ]"
    echo "      },"
    echo "      \"items\": ["
    rd=${#MISC_URLS[@]}
    for (( ri=0; ri<rd; ri++ )); do
      local comma=","; [[ $ri -eq $((rd - 1)) ]] && comma=""
      local mu="${MISC_URLS[$ri]}"
      local mu_url="${mu%%|*}"; local mu_src="${mu#*|}"
      echo "        {\"url\":\"$(json_escape_str "$mu_url")\",\"source\":\"$(json_escape_str "$mu_src")\"}${comma}"
    done
    echo "      ]"
    echo "    },"
    echo "    \"images\": {"
    echo "      \"total\": ${MISC_IMAGE_COUNT},"
    echo "      \"pages_scanned\": ${MISC_PAGES_SCANNED},"
    echo "      \"items\": ["
    rd=${#MISC_IMAGES[@]}
    for (( ri=0; ri<rd; ri++ )); do
      local comma=","; [[ $ri -eq $((rd - 1)) ]] && comma=""
      local mi="${MISC_IMAGES[$ri]}"
      local mi_url="${mi%%|*}"; local mi_page="${mi#*|}"
      echo "        {\"url\":\"$(json_escape_str "$mi_url")\",\"page\":\"$(json_escape_str "$mi_page")\"}${comma}"
    done
    echo "      ]"
    echo "    }"
    echo "  },"
    if [[ -n "$COMPARE_BASELINE_LABEL" ]]; then
      echo "  \"compare\": {"
      echo "    \"baseline\": \"$(json_escape_str "$COMPARE_BASELINE_LABEL")\","
      echo "    \"prev_hygiene\": ${COMPARE_PREV_HYGIENE:-0},"
      echo "    \"prev_exposure\": ${COMPARE_PREV_EXPOSURE:-0},"
      echo "    \"hygiene_delta\": ${COMPARE_HYGIENE_DELTA},"
      echo "    \"exposure_delta\": ${COMPARE_EXPOSURE_DELTA},"
      echo "    \"new_actions\": ["
      rd=${#COMPARE_NEW_ACTIONS[@]}
      for (( ri=0; ri<rd; ri++ )); do
        local comma=","; [[ $ri -eq $((rd - 1)) ]] && comma=""
        echo "      \"$(json_escape_str "${COMPARE_NEW_ACTIONS[$ri]}")\"${comma}"
      done
      echo "    ]"
      echo "  },"
    fi
    echo "  \"versions_found\": ["
    local vt=${#VERSIONS_FOUND[@]}
    for (( i=0; i<vt; i++ )); do
      local comma=","; [[ $i -eq $((vt - 1)) ]] && comma=""
      echo "    \"${VERSIONS_FOUND[$i]}\"${comma}"
    done
    echo "  ],"
    json_generator_block
    echo "}"
  } > "$LOG_JSON"

  write_html_report "$framework"
}

# ── Single-target audit ───────────────────────────────────────────
run_single_audit() {
  local target="$1"
  TARGET_URL="$target"
  reset_audit_state
  setup_url_logs "$TARGET_URL"

  log_msg ""
  log_msg "╔══════════════════════════════════════════════════════"
  log_msg "║  Auditing: ${URL_SLUG}"              
  log_msg "╚══════════════════════════════════════════════════════"
  log_msg "  URL     : $TARGET_URL"
  log_msg "  Log dir : $URL_LOG_DIR"
  log_msg "────────────────────────────────────────"

  if [[ "${DRY_RUN:-0}" -eq 1 ]]; then
    if [[ -n "$FORCE_FRAMEWORK" && "$FORCE_FRAMEWORK" != "auto" ]]; then
      FRAMEWORK="$FORCE_FRAMEWORK"; FRAMEWORK_CONFIDENCE="forced (dry-run)"
    else
      FRAMEWORK="unknown"; FRAMEWORK_CONFIDENCE="dry-run (use --framework to pin stack)"
    fi
    log_msg "Framework: ${FRAMEWORK} (${FRAMEWORK_CONFIDENCE})"
  elif [[ -n "$FORCE_FRAMEWORK" && "$FORCE_FRAMEWORK" != "auto" ]]; then
    FRAMEWORK="$FORCE_FRAMEWORK"; FRAMEWORK_CONFIDENCE="forced"; FRAMEWORK_SIGNALS="user-specified"
    log_msg "Framework: ${CYN}${FRAMEWORK}${RST} (forced)"
    detect_framework "$TARGET_URL"; FRAMEWORK="$FORCE_FRAMEWORK"
  else
    log_msg "Detecting framework..."
    detect_framework "$TARGET_URL"
    log_msg ""
    log_msg "  Framework  : ${CYN}${FRAMEWORK}${RST}"
    log_msg "  Confidence : ${CYN}${FRAMEWORK_CONFIDENCE}${RST}"
    log_msg "  Signals    : ${FRAMEWORK_SIGNALS}"
    log_msg "  Language   : ${CYN}${LANGUAGE_DETECTED}${RST}"
    log_msg "  CDN        : ${CYN}${CDN_DETECTED}${RST}"
    log_msg "  UA Used    : ${CYN}${EFFECTIVE_UA}${RST}"
    [[ -n "$SERVER_HEADER" ]] && log_msg "  Server     : $SERVER_HEADER"
    [[ -n "$POWERED_BY"    ]] && log_msg "  Powered-by : $POWERED_BY"
  fi

  log_msg ""; log_msg "────────────────────────────────────────"

  local -a PROBE_PATHS UNIQUE_PATHS
  local -A SEEN_PATHS
  PROBE_PATHS=("${PATHS_COMMON[@]}")
  case "$FRAMEWORK" in
    django)      PROBE_PATHS+=("${PATHS_DJANGO[@]}") ;;
    wordpress)   PROBE_PATHS+=("${PATHS_WORDPRESS[@]}") ;;
    laravel)     PROBE_PATHS+=("${PATHS_LARAVEL[@]}") ;;
    rails)       PROBE_PATHS+=("${PATHS_RAILS[@]}") ;;
    php_generic) PROBE_PATHS+=("${PATHS_GENERIC[@]}") ;;
    blocked)
      log_msg "Site blocking all curl requests — results may be unreliable."
      PROBE_PATHS+=("${PATHS_DJANGO[@]}" "${PATHS_WORDPRESS[@]}" "${PATHS_LARAVEL[@]}" "${PATHS_RAILS[@]}" "${PATHS_GENERIC[@]}") ;;
    *)
      log_msg "Framework unknown — running all probes."
      PROBE_PATHS+=("${PATHS_DJANGO[@]}" "${PATHS_WORDPRESS[@]}" "${PATHS_LARAVEL[@]}" "${PATHS_RAILS[@]}" "${PATHS_GENERIC[@]}") ;;
  esac

  UNIQUE_PATHS=()
  for p in "${PROBE_PATHS[@]}" "${CONFIG_EXTRA_PATHS[@]}"; do [[ -n "${SEEN_PATHS[$p]:-}" ]] && continue; UNIQUE_PATHS+=("$p"); SEEN_PATHS[$p]=1; done

  if [[ "${DRY_RUN:-0}" -eq 1 ]]; then
    print_dry_run_plan "${UNIQUE_PATHS[@]}"
    log_msg "Dry run complete — no reports written."
    return 0
  fi

  log_msg ""; log_msg "Probing ${#UNIQUE_PATHS[@]} paths..."; log_msg ""
  printf "  %-42s [raw: %-${PROBE_STATUS_WIDTH}s]    [final: %-${PROBE_STATUS_WIDTH}s]\n" \
    "PATH" "status" "status"
  log_msg "  ────────────────────────────────────────────────────────────────────────"
  for url_path in "${UNIQUE_PATHS[@]}"; do probe_path "$url_path"; done

  export GREP SED HEAD MKTEMP CURL
  export PATH="${AUDIT_PATH}:${PATH}"

  log_msg ""; log_msg "────────────────────────────────────────"
  log_msg "Running security checks..."; log_msg "────────────────────────────────────────"

  check_headers
  check_policy_parse
  check_tls
  check_cookies
  check_rate_limiting
  check_dir_listing
  check_version_disclosure
  check_api_content
  check_open_redirect
  check_plugin_versions
  check_framework_specifics
  check_redirect_chain
  check_artifacts
  check_site_miscellaneous
  check_cors
  check_http_methods

  log_msg ""; log_msg "── Security Check Results ───────────────────────────────────"
  print_check_section "HEADERS"        "HTTP Security Headers"
  print_check_section "POLICY"         "Policy Parse (HSTS/CSP)"
  print_check_section "TLS"            "TLS Version Support"
  print_check_section "COOKIES"        "Cookie Security Flags"
  print_check_section "RATE_LIMIT"     "Rate Limiting"
  print_check_section "DIR_LISTING"    "Directory Listing"
  print_check_section "VERSION"        "Version Disclosure"
  print_check_section "API_CONTENT"    "API / Content Exposure"
  print_check_section "OPEN_REDIRECT"  "Open Redirect"
  print_check_section "PLUGIN_VERSION" "Plugin Versions"
  print_check_section "TRANSPORT"      "Transport / Redirects"
  print_check_section "ARTIFACTS"      "Artifacts (robots/security/sitemap)"
  print_check_section "MISC"           "Miscellaneous (URLs, images)"
  print_check_section "ATTRIBUTION"    "Designer / Creator Attribution"
  print_check_section "CORS"           "CORS"
  print_check_section "METHODS"        "HTTP Methods"
  case "$FRAMEWORK" in
    wordpress) print_check_section "WORDPRESS" "WordPress Specific" ;;
    django)    print_check_section "DJANGO"    "Django Specific"    ;;
    laravel)   print_check_section "LARAVEL"   "Laravel Specific"   ;;
    rails)     print_check_section "RAILS"     "Rails Specific"     ;;
  esac
  print_check_section "GENERAL" "General"
  [[ -n "$COMPARE_BASELINE" ]] && print_check_section "COMPARE" "Baseline Comparison"

  [[ -n "$COMPARE_BASELINE" ]] && compare_with_baseline "$COMPARE_BASELINE"

  write_logs "$FRAMEWORK"
  LAST_JSON_PATH="$LOG_JSON"

  log_msg ""; log_msg "────────────────────────────────────────"
  log_msg "── Path Summary ─────────────────────────"
  log_msg "  Target    : $TARGET_URL"
  log_msg "  Framework : $FRAMEWORK (confidence: $FRAMEWORK_CONFIDENCE)"
  log_msg "  CDN       : $CDN_DETECTED"; log_msg ""

  local open_count=0 expected_count=0 sensitive_count=0 i path_label
  for (( i=0; i<${#R_PATH[@]}; i++ )); do
    if [[ "${R_NOTE[$i]}" == "OPEN" || "${R_NOTE[$i]}" == SERVER_ERROR* ]]; then
      if is_scored_exposure "${R_PATH[$i]}" "${R_NOTE[$i]}"; then
        color_echo "  ${RED}*** SENSITIVE LEAK${RST}: ${R_PATH[$i]}  raw:${R_RAW[$i]} → final:${R_FINAL[$i]}"
        sensitive_count=$((sensitive_count + 1))
      elif is_expected_open "${R_PATH[$i]}"; then
        if is_login_surface "${R_PATH[$i]}"; then path_label="login surface"
        elif is_app_surface "${R_PATH[$i]}"; then path_label="app surface (config)"
        elif is_public_by_design "${R_PATH[$i]}"; then path_label="public by design"
        else path_label="expected (config)"; fi
        color_echo "  ${CYN}(${path_label})${RST}: ${R_PATH[$i]}  final:${R_FINAL[$i]}"
        expected_count=$((expected_count + 1))
      else
        color_echo "  ${YLW}*** REVIEW${RST}: ${R_PATH[$i]}  raw:${R_RAW[$i]} → final:${R_FINAL[$i]}"
        open_count=$((open_count + 1))
      fi
    fi
  done
  [[ $sensitive_count -eq 0 ]] && color_echo "  ${GRN}No sensitive path leaks.${RST}"
  [[ $open_count -eq 0 && $sensitive_count -eq 0 ]] && [[ $expected_count -gt 0 ]] && color_echo "  ${GRN}Open paths are expected (login, robots, etc.).${RST}"

  compute_scores
  log_msg ""
  log_msg "  Scores: Hygiene=${SCORE_HYGIENE}/100  Exposure=${SCORE_EXPOSURE}/100  (v${TOOL_VERSION} — ACTION items only affect Hygiene)"

  print_security_summary

  log_msg ""; log_msg "Reports saved for ${URL_SLUG}:"
  log_msg "  Dir  : $URL_LOG_DIR"
  log_msg "  TXT  : $LOG_TXT"
  log_msg "  JSON : $LOG_JSON"
  log_msg "  HTML : $LOG_HTML"
  log_msg ""

  SESSION_AUDIT_RECORDS+=("${TARGET_URL}|${URL_SLUG}|${LOG_TXT}|${LOG_JSON}|${LOG_HTML}")
  SESSION_SCORES+=("${TARGET_URL}|${SCORE_HYGIENE}|${SCORE_EXPOSURE}|${LOG_JSON}")

  if [[ -n "$FAIL_UNDER_HYGIENE" && "$SCORE_HYGIENE" -lt "$FAIL_UNDER_HYGIENE" ]]; then
    log_err "FAIL: Hygiene ${SCORE_HYGIENE} < threshold ${FAIL_UNDER_HYGIENE} (${TARGET_URL})"
    SESSION_EXIT=1
  fi
  if [[ -n "$FAIL_UNDER_EXPOSURE" && "$SCORE_EXPOSURE" -lt "$FAIL_UNDER_EXPOSURE" ]]; then
    log_err "FAIL: Exposure ${SCORE_EXPOSURE} < threshold ${FAIL_UNDER_EXPOSURE} (${TARGET_URL})"
    SESSION_EXIT=1
  fi
}

write_session_index() {
  local now=$("$DATE")
  local now_utc=$("$DATE" -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || "$DATE" +"%Y-%m-%dT%H:%M:%SZ")
  local rec url slug

  {
    echo "========================================"
    echo " Audit Session Index — ${BRAND_VENDOR}"
    echo "========================================"
    system_info_txt
    echo " Targets Audited : ${#SESSION_AUDIT_RECORDS[@]}"
    echo " Completed       : $now"
    echo "========================================"
    echo ""
    for rec in "${SESSION_AUDIT_RECORDS[@]}"; do
      url="${rec%%|*}"; rec="${rec#*|}"
      slug="${rec%%|*}"; rec="${rec#*|}"
      echo "Target : $url"
      echo "  Slug : $slug"
      echo "  TXT  : ${rec%%|*}"; rec="${rec#*|}"
      echo "  JSON : ${rec%%|*}"; rec="${rec#*|}"
      echo "  HTML : $rec"
      echo ""
    done
    report_attribution_txt "$now"
  } > "${RUN_SESSION_DIR}/session_${RUN_DATE}_${RUN_TIMESTAMP}.txt"

  {
    echo "{"
    echo "  \"session_dir\": \"$RUN_SESSION_DIR\","
    echo "  \"run_date\": \"$RUN_DATE\","
    echo "  \"run_time\": \"$RUN_TIME\","
    echo "  \"run_timestamp\": \"$RUN_TIMESTAMP\","
    echo "  \"completed_at\": \"$now_utc\","
    echo "  \"audit_host\": {"
    echo "    \"hostname\": \"$(json_escape_str "$SYS_HOST")\","
    echo "    \"architecture\": \"$(json_escape_str "$SYS_ARCH")\","
    echo "    \"os\": \"$(json_escape_str "$SYS_OS")\","
    echo "    \"os_full\": \"$(json_escape_str "$SYS_OS_FULL")\","
    echo "    \"kernel\": \"$(json_escape_str "$SYS_KERNEL")\","
    echo "    \"shell\": \"$(json_escape_str "$SYS_SHELL")\","
    echo "    \"uname\": \"$(json_escape_str "$SYS_UNAME")\""
    echo "  },"
    echo "  \"targets\": ["
    local i total=${#SESSION_AUDIT_RECORDS[@]}
    for (( i=0; i<total; i++ )); do
      local comma=","; [[ $i -eq $((total - 1)) ]] && comma=""
      rec="${SESSION_AUDIT_RECORDS[$i]}"
      url="${rec%%|*}"; rec="${rec#*|}"
      slug="${rec%%|*}"; rec="${rec#*|}"
      local txt="${rec%%|*}"; rec="${rec#*|}"
      local json="${rec%%|*}"; local html="$rec"
      echo "    {\"url\":\"$url\",\"slug\":\"$slug\",\"txt\":\"$txt\",\"json\":\"$json\",\"html\":\"$html\"}${comma}"
    done
    echo "  ],"
    json_generator_block
    echo "}"
  } > "${RUN_SESSION_DIR}/session_${RUN_DATE}_${RUN_TIMESTAMP}.json"
}

# ── Open results in browser (new window per item) ─────────────────

path_to_file_url() {
  local f="$1" abs
  abs=$(cd "$(dirname "$f")" 2>/dev/null && pwd)/$(basename "$f")
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve().as_uri())" "$abs"
  else
    printf 'file://%s' "${abs// /%20}"
  fi
}

open_browser_new_window() {
  local target="$1"
  local opened=0

  # Linux — Chromium / Chrome new window
  for browser in google-chrome google-chrome-stable chromium chromium-browser brave-browser microsoft-edge; do
    if command -v "$browser" >/dev/null 2>&1; then
      "$browser" --new-window "$target" >/dev/null 2>&1 &
      opened=1
      break
    fi
  done
  [[ $opened -eq 1 ]] && return 0

  # macOS — Chrome / Brave / Edge new window
  if [[ "$SYS_OS" == "Darwin" ]]; then
    for app in "Google Chrome" "Brave Browser" "Microsoft Edge" "Firefox"; do
      if open -Ra "$app" 2>/dev/null; then
        if [[ "$app" == "Firefox" ]]; then
          open -a Firefox -n --args -new-window "$target" 2>/dev/null &
        else
          open -na "$app" --args --new-window "$target" 2>/dev/null &
        fi
        opened=1
        break
      fi
    done
    [[ $opened -eq 1 ]] && return 0
    open -n "$target" 2>/dev/null &
    return 0
  fi

  # Generic fallback
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$target" >/dev/null 2>&1 &
  elif command -v open >/dev/null 2>&1; then
    open -n "$target" 2>/dev/null &
  else
    echo "  (could not open browser — no supported opener found for: $target)" >&2
    return 1
  fi
}

open_session_in_browser() {
  [[ "${OPEN_BROWSER:-1}" == "0" ]] && { echo "Browser open skipped (OPEN_BROWSER=0)."; return; }

  local rec url slug html file_url count=0
  echo ""
  echo "Opening reports and live sites in separate browser windows..."

  for rec in "${SESSION_AUDIT_RECORDS[@]}"; do
    url="${rec%%|*}"; rec="${rec#*|}"
    slug="${rec%%|*}"; rec="${rec#*|}"
    rec="${rec#*|}"; rec="${rec#*|}"   # skip txt, json
    html="$rec"

    if [[ -f "$html" ]]; then
      file_url=$(path_to_file_url "$html")
      echo "  → Report: $(basename "$html")"
      open_browser_new_window "$file_url"
      count=$((count + 1))
      sleep 0.4
    fi

    echo "  → Site:   $url"
    open_browser_new_window "$url"
    count=$((count + 1))
    sleep 0.4
  done

  [[ $count -gt 0 ]] && echo "Opened ${count} window(s). Arrange them side-by-side in your browser."
}

# ── Main ──────────────────────────────────────────────────────────

target_idx=0
for TARGET_URL in "${TARGET_URLS[@]}"; do
  target_idx=$((target_idx + 1))
  [[ ${#TARGET_URLS[@]} -gt 1 ]] && echo "" && echo "========== Target ${target_idx}/${#TARGET_URLS[@]} =========="
  resolve_config_for_target "$TARGET_URL"
  run_single_audit "$TARGET_URL"
done

write_session_index

echo "════════════════════════════════════════"
echo "Session complete — all reports in:"
echo "  ${RUN_SESSION_DIR}/"
echo ""
echo "Session index:"
echo "  ${RUN_SESSION_DIR}/session_${RUN_DATE}_${RUN_TIMESTAMP}.txt"
echo "  ${RUN_SESSION_DIR}/session_${RUN_DATE}_${RUN_TIMESTAMP}.json"

open_session_in_browser

[[ "$JSON_STDOUT" -eq 1 && -n "$LAST_JSON_PATH" ]] && echo "$LAST_JSON_PATH"

if [[ "$SESSION_EXIT" -ne 0 ]]; then
  log_err "Session finished with threshold failure(s)."
else
  log_msg "Session finished successfully."
fi

exit "$SESSION_EXIT"