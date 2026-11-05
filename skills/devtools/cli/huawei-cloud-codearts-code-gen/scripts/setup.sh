#!/bin/bash
# CodeArts CLI environment check and setup script (non-interactive)
# Designed for automated Agent execution
#
# Exit codes:
#   0  - Environment ready, can execute code generation
#   2  - Invalid arguments (missing / empty AK, SK or lock timeout)
#   10 - AK/SK configuration required
#   20 - User consent required for permission configuration
#   30 - CLI installation failed (auto-resolution attempted)
#   40 - Network connection failed (auto-resolution attempted)
#   50 - Authentication failed (invalid AK/SK)
#
# Output convention:
#   stdout carries exactly ONE JSON object and nothing else.
#   Every log line goes to stderr.
#
# Usage:
#   ./setup.sh                          # Check environment
#   ./setup.sh --save-aksk <AK> <SK>    # Save AK/SK to ~/.bashrc and continue
#   ./setup.sh --ak <AK> --sk <SK>      # Use AK/SK temporarily (without saving)
#   ./setup.sh --clear-aksk             # Remove AK/SK lines from ~/.bashrc
#
# Portability notes:
#   * bash 3.2 (macOS) compatible: no mapfile / no ${var,,} / no associative arrays.
#   * Never edits files in place with an in-place sed flag (BSD/macOS and GNU sed
#     disagree about its argument, so it is unusable on macOS); ~/.bashrc is rewritten
#     with "filter to temp file + atomic rename" and guarded by a mkdir directory lock.
#   * Optional env hooks for tests: CODEARTS_SETUP_MAX_RETRY, CODEARTS_SETUP_RETRY_DELAY,
#     CODEARTS_SETUP_LOCK_RETRY, CODEARTS_SETUP_LOCK_SLEEP, CODEARTS_SETUP_LOCK_STALE.
#     The lock waits up to CODEARTS_SETUP_LOCK_RETRY x CODEARTS_SETUP_LOCK_SLEEP
#     (default 10 x 0.2s = 2s) before failing with lock_timeout; a lock directory
#     older than CODEARTS_SETUP_LOCK_STALE (default 30s) is reclaimed as stale.

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration (env overrides exist only to keep automated tests fast)
MAX_RETRY="${CODEARTS_SETUP_MAX_RETRY:-3}"
RETRY_DELAY="${CODEARTS_SETUP_RETRY_DELAY:-5}"
LOCK_MAX_RETRY="${CODEARTS_SETUP_LOCK_RETRY:-10}"
LOCK_RETRY_SLEEP="${CODEARTS_SETUP_LOCK_SLEEP:-0.2}"
LOCK_STALE_SECONDS="${CODEARTS_SETUP_LOCK_STALE:-30}"
CLI_PATH="$HOME/.codeartsdoer/installers/codearts"
INSTALL_URL="https://cnnorth4-cloudide-marketplace.obs.cn-north-4.myhuaweicloud.com/codearts/cli_tui/install_script/install.sh"
CONFIG_FILE="$HOME/.bashrc"
LOCK_DIR="$CONFIG_FILE.lock"
PERMISSION_FILE="$HOME/.codeartsdoer/cli-data/storage/permission/global.json"

# Shared error signature used by verify_connection (#113-3 / #113-8):
# a CLI may exit 0 (or exit non-zero) while still reporting an auth problem,
# so the exit code alone must never be trusted.
AUTH_ERROR_PATTERN='unauthorized|authentication|invalid.*key|unexpected error|ak/sk|access key|forbidden|expired'

# Output functions (stderr only)
log_info() { echo -e "${GREEN}[INFO]${NC} $1" >&2; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" >&2; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# ============================================
# JSON helpers
# ============================================
json_escape() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\t'/\\t}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    printf '%s' "$s"
}

# Structured error: the ONLY thing written to stdout, then exit with that code.
# A human-readable companion line goes to stderr (#113-6: "friendly message when the
# SK is missing"), so an interactive reader is not left staring at raw JSON.
output_error() {
    local error_code="$1"
    local error_type="$2"
    local error_msg="$3"
    local fix_hint="$4"

    log_error "$error_msg [$error_type]. $fix_hint"

    printf '{"status":"error","code":%s,"type":"%s","message":"%s","fix_hint":"%s","options":[{"id":1,"label":"Continue fixing","description":"Try to fix the issue manually"},{"id":2,"label":"Write code directly","description":"Abandon CodeArts, agent writes code directly"}]}\n' \
        "$error_code" \
        "$(json_escape "$error_type")" \
        "$(json_escape "$error_msg")" \
        "$(json_escape "$fix_hint")"
    exit "$error_code"
}

# ============================================
# Detect operating system
# ============================================
detect_os() {
    case "$(uname -s)" in
        Linux*)     echo "Linux";;
        Darwin*)    echo "macOS";;
        CYGWIN*|MINGW*|MSYS*)    echo "Windows";;
        *)          echo "Unknown";;
    esac
}

OS=$(detect_os)
ARCH=$(uname -m)

# ============================================
# File metadata helpers (GNU stat / BSD stat)
# ============================================
path_mode() {
    local m
    m=$(stat -c %a "$1" 2>/dev/null) || m=""
    if [ -z "$m" ]; then
        m=$(stat -f %Lp "$1" 2>/dev/null) || m=""
    fi
    printf '%s' "$m"
}

path_mtime() {
    local t
    t=$(stat -c %Y "$1" 2>/dev/null) || t=""
    if [ -z "$t" ]; then
        t=$(stat -f %m "$1" 2>/dev/null) || t=""
    fi
    printf '%s' "$t"
}

# ============================================
# Directory lock around ~/.bashrc (#113-10)
#   mkdir is atomic on every filesystem (macOS has no flock by default).
# ============================================
LOCK_HELD=false
TMP_FILES=""

release_lock() {
    if [ "$LOCK_HELD" = true ]; then
        LOCK_HELD=false
        rmdir "$LOCK_DIR" 2>/dev/null || true
    fi
    if [ -n "$TMP_FILES" ]; then
        local f
        for f in $TMP_FILES; do
            if [ -n "$f" ]; then
                rm -f "$f" 2>/dev/null || true
            fi
        done
        TMP_FILES=""
    fi
}

acquire_lock() {
    local attempt=0 mtime now age

    # Phase 1: bounded normal wait for the current owner to finish.
    while [ "$attempt" -lt "$LOCK_MAX_RETRY" ]; do
        if mkdir "$LOCK_DIR" 2>/dev/null; then
            LOCK_HELD=true
            trap 'release_lock' EXIT INT TERM HUP
            return 0
        fi
        attempt=$((attempt + 1))
        sleep "$LOCK_RETRY_SLEEP"
    done

    # Phase 2: the lock outlived the whole budget, so its owner is gone or wedged.
    # It is reclaimed only when it is genuinely older than LOCK_STALE_SECONDS, which
    # also guarantees this process can never steal a lock it is itself contending for.
    mtime=$(path_mtime "$LOCK_DIR")
    if [ -n "$mtime" ]; then
        now=$(date +%s)
        age=$((now - mtime))
        if [ "$age" -gt "$LOCK_STALE_SECONDS" ]; then
            log_warn "Removing stale lock directory $LOCK_DIR (age ${age}s)"
            rmdir "$LOCK_DIR" 2>/dev/null || rm -rf "$LOCK_DIR" 2>/dev/null || true
            if mkdir "$LOCK_DIR" 2>/dev/null; then
                LOCK_HELD=true
                trap 'release_lock' EXIT INT TERM HUP
                return 0
            fi
        fi
    fi

    return 1
}

# ============================================
# Portable ~/.bashrc rewrite (#100-1)
#   grep -vE filter -> temp file in the SAME directory -> atomic mv.
#   In-place sed editing is banned: BSD/macOS sed and GNU sed disagree on how the
#   in-place flag takes its argument, so the same command cannot work on both.
# ============================================
NEW_TMP=""
filter_config_to_tmp() {
    # $1 = "trim" : drop trailing blank lines (used by save, so repeated saves are stable)
    #      "keep" : byte-faithful deletion (used by clear, which must touch nothing else)
    # Sets NEW_TMP (no subshell, so the cleanup list stays valid in the caller).
    local mode="${1:-keep}" tmp trimmed
    NEW_TMP=""
    tmp=$(mktemp "${CONFIG_FILE}.tmp.XXXXXX") || return 1
    TMP_FILES="$TMP_FILES $tmp"

    if [ -f "$CONFIG_FILE" ]; then
        grep -vE '^export CODEARTS_CLI_(AK|SK)=' "$CONFIG_FILE" > "$tmp" 2>/dev/null || : > "$tmp"
    else
        : > "$tmp"
    fi

    # Trailing blank lines are removed only for save; the file always keeps exactly
    # one final newline so a plain append can never run into the previous line.
    if [ "$mode" = "trim" ] && [ -s "$tmp" ]; then
        trimmed=$(cat "$tmp")
        if [ -n "$trimmed" ]; then
            printf '%s\n' "$trimmed" > "$tmp"
        else
            : > "$tmp"
        fi
    fi

    NEW_TMP="$tmp"
    return 0
}

commit_config_tmp() {
    local tmp="$1" mode
    mode=$(path_mode "$CONFIG_FILE")
    if [ -n "$mode" ]; then
        chmod "$mode" "$tmp" 2>/dev/null || true
    else
        # Newly created credential file: keep it private.
        chmod 600 "$tmp" 2>/dev/null || true
    fi
    mv "$tmp" "$CONFIG_FILE"
}

# ============================================
# Save AK/SK to ~/.bashrc
# ============================================
save_aksk() {
    local ak="$1"
    local sk="$2"
    local tmp

    log_info "Saving AK/SK to ~/.bashrc"

    if ! acquire_lock; then
        output_error 2 "lock_timeout" \
            "Could not acquire the lock $LOCK_DIR after $LOCK_MAX_RETRY attempts" \
            "Remove the stale lock directory manually: rmdir '$LOCK_DIR'"
    fi

    if ! filter_config_to_tmp trim; then
        output_error 2 "config_write_failed" \
            "Could not create a temporary file next to $CONFIG_FILE" \
            "Check that $HOME is writable"
    fi
    tmp="$NEW_TMP"

    # The block is appended directly after the last kept line (no separator blank
    # line): that keeps repeated saves stable AND makes save followed by clear a
    # byte-exact round trip of the original file.
    if ! printf 'export CODEARTS_CLI_AK="%s"\nexport CODEARTS_CLI_SK="%s"\n' "$ak" "$sk" >> "$tmp"; then
        output_error 2 "config_write_failed" \
            "Could not write AK/SK into the temporary configuration file" \
            "Check free disk space and permissions of $HOME"
    fi

    if ! commit_config_tmp "$tmp"; then
        output_error 2 "config_write_failed" \
            "Could not replace $CONFIG_FILE atomically" \
            "Check write permission on $HOME"
    fi

    log_info "AK/SK saved to ~/.bashrc"
    release_lock
    return 0
}

# ============================================
# Clear AK/SK from ~/.bashrc (new --clear-aksk contract)
# ============================================
clear_aksk() {
    local tmp

    log_info "Clearing AK/SK from ~/.bashrc"

    if ! acquire_lock; then
        output_error 2 "lock_timeout" \
            "Could not acquire the lock $LOCK_DIR after $LOCK_MAX_RETRY attempts" \
            "Remove the stale lock directory manually: rmdir '$LOCK_DIR'"
    fi

    if [ ! -f "$CONFIG_FILE" ]; then
        log_info "No $CONFIG_FILE found, nothing to clear"
    else
        if ! filter_config_to_tmp keep; then
            output_error 2 "config_write_failed" \
                "Could not create a temporary file next to $CONFIG_FILE" \
                "Check that $HOME is writable"
        fi
        tmp="$NEW_TMP"

        if ! commit_config_tmp "$tmp"; then
            output_error 2 "config_write_failed" \
                "Could not replace $CONFIG_FILE atomically" \
                "Check write permission on $HOME"
        fi
        log_info "AK/SK lines removed from ~/.bashrc"
    fi

    release_lock
    printf '{"status":"cleared","code":0,"message":"AK/SK removed from ~/.bashrc"}\n'
    exit 0
}

# ============================================
# Load AK/SK (priority: args > env vars > ~/.bashrc)
# ============================================
load_aksk() {
    # Priority 1: command line args
    if [ -n "$PARSE_ARGS_AK" ] && [ -n "$PARSE_ARGS_SK" ]; then
        export CODEARTS_CLI_AK="$PARSE_ARGS_AK"
        export CODEARTS_CLI_SK="$PARSE_ARGS_SK"

        if [ "$SAVE_AKSK" = true ]; then
            save_aksk "$PARSE_ARGS_AK" "$PARSE_ARGS_SK"
        fi
        return 0
    fi

    # Priority 2: environment variables
    if [ -n "$CODEARTS_CLI_AK" ] && [ -n "$CODEARTS_CLI_SK" ]; then
        return 0
    fi

    # Priority 3: extract from ~/.bashrc (grep+eval avoids interactive guard)
    if [ -f "$CONFIG_FILE" ]; then
        local lines rc
        rc=0
        lines=$(grep -E '^export CODEARTS_CLI_(AK|SK)=' "$CONFIG_FILE" 2>/dev/null) || rc=$?
        if [ "$rc" -eq 0 ] && [ -n "$lines" ]; then
            log_info "Loading AK/SK from ~/.bashrc"
            eval "$lines"
        fi
        if [ -n "$CODEARTS_CLI_AK" ] && [ -n "$CODEARTS_CLI_SK" ]; then
            return 0
        fi
    fi

    return 1
}

# ============================================
# Download with retry
# ============================================
download_with_retry() {
    local url="$1"
    local attempt=1

    while [ "$attempt" -le "$MAX_RETRY" ]; do
        log_info "Download attempt $attempt/$MAX_RETRY..."

        if command -v curl >/dev/null 2>&1; then
            if curl -fsSL --connect-timeout 30 "$url"; then
                return 0
            fi
        elif command -v wget >/dev/null 2>&1; then
            if wget -qO- --timeout=30 "$url"; then
                return 0
            fi
        fi

        if [ "$attempt" -lt "$MAX_RETRY" ]; then
            log_warn "Download failed, retrying in ${RETRY_DELAY}s..."
            sleep "$RETRY_DELAY"
        fi

        attempt=$((attempt + 1))
    done

    return 1
}

# ============================================
# Step 1: CLI check and install
# ============================================
check_and_install_cli() {
    log_info "Step 1: Checking CLI..."

    if [ -f "$CLI_PATH" ]; then
        log_info "CLI installed: $CLI_PATH"
        return 0
    fi

    log_info "CLI not installed, auto-installing..."
    log_info "System: $OS ($ARCH)"

    case "$OS" in
        Linux|macOS)
            if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
                output_error 30 "dependency_missing" \
                    "curl or wget is required to download the install script" \
                    "Install curl: apt install curl or yum install curl"
            fi

            # `if ! VAR=$(...)` instead of `VAR=$(...)` + `$?`: under `set -e`
            # the latter form killed the script before the retry result was read.
            if ! INSTALL_SCRIPT=$(download_with_retry "$INSTALL_URL"); then
                output_error 30 "download_failed" \
                    "CLI install script download failed (retried $MAX_RETRY times)" \
                    "Check network, or manually download: $INSTALL_URL"
            fi

            # The installer writes to stdout by default; send it to stderr so
            # stdout keeps its "JSON only" contract.
            if ! printf '%s\n' "$INSTALL_SCRIPT" | sh 1>&2; then
                output_error 30 "install_failed" \
                    "CLI install script execution failed" \
                    "Check system permissions, or review install logs"
            fi
            ;;
        Windows)
            output_error 30 "unsupported_os" \
                "Windows systems should use PowerShell to install" \
                "irm https://cnnorth4-cloudide-marketplace.obs.cn-north-4.myhuaweicloud.com/codearts/cli_tui/install_script/install.ps1 | iex"
            ;;
        *)
            output_error 30 "unsupported_os" \
                "Unsupported system: $OS" \
                "Currently supported: Linux, macOS, Windows"
            ;;
    esac

    # Verify installation
    if [ -f "$CLI_PATH" ]; then
        log_info "CLI installation complete"
        return 0
    else
        output_error 30 "install_verify_failed" \
            "CLI executable not found after installation" \
            "Check ~/.codeartsdoer/installers/ directory"
    fi
}

# ============================================
# Step 2: AK/SK check
# ============================================
check_aksk() {
    log_info "Step 2: Checking AK/SK..."

    if ! load_aksk; then
        log_warn "AK/SK not configured"
        cat << 'EOF'
{"status":"need_input","code":10,"type":"aksk_required","message":"Huawei Cloud Access Key required","help":{"description":"Access Key is used to authenticate CodeArts CLI","tutorial_url":"https://support.huaweicloud.com/usermanual-iam/iam_02_0003.html","console_url":"https://console.huaweicloud.com/iam/?#/mine/accessKey","env_vars":[{"name":"CODEARTS_CLI_AK","label":"Access Key ID","description":"Huawei Cloud Access Key ID","required":true},{"name":"CODEARTS_CLI_SK","label":"Secret Access Key","description":"Huawei Cloud Secret Access Key","required":true,"secret":true}],"hint":"After providing AK/SK, the agent will save them. No need to re-enter. AK/SK are stored only in the local AI Shell environment variables and will NOT be uploaded to any external services, and you can either clear them manually or wait for them to be automatically released when the environment resources are reclaimed to delete them.","save_command":"setup.sh --save-aksk AK SK"}}
EOF
        exit 10
    fi

    log_info "AK/SK configured"
    return 0
}

# ============================================
# Step 3: Permission check (#113-7)
#   Real JSON parsing instead of `grep -A1`, so compact and pretty-printed
#   configurations are judged identically. python3/jq first, tr/awk fallback.
# ============================================
permission_json_ok_python() {
    # $1 = python interpreter. Prints "1" (configured) or "0" (not configured).
    # Prints nothing when the interpreter itself is unusable.
    "$1" -c '
import json, sys
try:
    with open(sys.argv[1], "r", encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    print("0")
    sys.exit(0)
if not isinstance(data, list):
    print("0")
    sys.exit(0)
def allowed(name):
    for entry in data:
        if isinstance(entry, dict) and entry.get("permission") == name and entry.get("action") == "allow":
            return True
    return False
print("1" if allowed("edit") and allowed("write") else "0")
' "$PERMISSION_FILE" 2>/dev/null
}

permission_json_ok_jq() {
    jq -r 'if type == "array" then (([.[] | select(.permission == "edit" and .action == "allow")] | length > 0) and ([.[] | select(.permission == "write" and .action == "allow")] | length > 0)) else false end | if . then "1" else "0" end' \
        "$PERMISSION_FILE" 2>/dev/null
}

permission_json_ok_fallback() {
    # Whitespace-stripped object matching: works for compact and pretty JSON
    # without any JSON library. Objects are split on "}".
    local flat recs
    [ -f "$PERMISSION_FILE" ] || return 1

    flat=$(tr -d ' \t\r\n' < "$PERMISSION_FILE" 2>/dev/null) || flat=""
    [ -n "$flat" ] || return 1

    recs=$(printf '%s' "$flat" | tr '}' '\n') || recs=""
    [ -n "$recs" ] || return 1

    printf '%s\n' "$recs" | grep -F '"permission":"edit"' | grep -F '"action":"allow"' >/dev/null 2>&1 || return 1
    printf '%s\n' "$recs" | grep -F '"permission":"write"' | grep -F '"action":"allow"' >/dev/null 2>&1 || return 1

    return 0
}

permission_configured() {
    local out parser

    [ -f "$PERMISSION_FILE" ] || return 1

    for parser in python3 python; do
        if command -v "$parser" >/dev/null 2>&1; then
            out=""
            out=$(permission_json_ok_python "$parser") || out=""
            if [ -n "$out" ]; then
                if [ "$out" = "1" ]; then
                    return 0
                else
                    return 1
                fi
            fi
        fi
    done

    if command -v jq >/dev/null 2>&1; then
        out=""
        out=$(permission_json_ok_jq) || out=""
        if [ -n "$out" ]; then
            if [ "$out" = "1" ]; then
                return 0
            else
                return 1
            fi
        fi
    fi

    permission_json_ok_fallback
}

need_permission_config() {
    if [ ! -f "$PERMISSION_FILE" ]; then
        return 0
    fi

    if permission_configured; then
        return 1
    fi

    return 0
}

check_permission() {
    log_info "Step 3: Checking permissions..."

    if need_permission_config; then
        log_warn "Permissions not configured or insufficient"
        printf '{"status":"need_consent","code":20,"type":"permission_required","message":"CodeArts CLI needs file read/write permission to generate code","consent":{"description":"After configuration, CLI can create and modify files in the specified directory","risk":"Recommend limiting to the workspace directory, avoid global permissions","workspace":"%s"}}\n' \
            "$(json_escape "$PWD")"
        exit 20
    fi

    log_info "Permissions configured"
    return 0
}

# ============================================
# Step 4: Verify connection (#113-3 / #113-8)
#   Exit code alone is not trusted: empty output and error signatures are
#   inspected too. Authentication failures -> 50, everything else -> 40.
# ============================================
verify_connection() {
    log_info "Step 4: Verifying connection..."

    local attempt=1 output rc

    if [ ! -f "$CLI_PATH" ]; then
        output_error 30 "cli_not_installed" \
            "CodeArts CLI not found at $CLI_PATH" \
            "Re-run setup.sh to install the CLI"
    fi

    while [ "$attempt" -le "$MAX_RETRY" ]; do
        output=""
        rc=0
        output=$("$CLI_PATH" models 2>&1) || rc=$?

        if [ "$rc" -eq 0 ] && [ -n "$output" ]; then
            if printf '%s' "$output" | grep -qiE "$AUTH_ERROR_PATTERN"; then
                log_warn "CLI exited 0 but the output looks like an authentication error"
            else
                log_info "Connection successful"
                return 0
            fi
        fi

        if printf '%s' "$output" | grep -qiE "$AUTH_ERROR_PATTERN"; then
            output_error 50 "auth_failed" \
                "Authentication failed, AK/SK is invalid" \
                "Please verify AK/SK is correct, or regenerate"
        fi

        if [ "$rc" -ne 0 ]; then
            log_warn "Connection check failed (exit $rc, attempt $attempt/$MAX_RETRY)"
        else
            log_warn "Connection check returned no output (attempt $attempt/$MAX_RETRY)"
        fi

        if [ "$attempt" -lt "$MAX_RETRY" ]; then
            log_warn "Connection failed, retrying in ${RETRY_DELAY}s..."
            sleep "$RETRY_DELAY"
        fi

        attempt=$((attempt + 1))
    done

    output_error 40 "network_failed" \
        "Network connection failed (retried $MAX_RETRY times)" \
        "Check network connection and proxy settings"
}

# ============================================
# Main
# ============================================
main() {
    log_info "=== CodeArts CLI Environment Check ==="
    log_info "System: $OS ($ARCH)"

    # Set PATH
    export PATH="$HOME/.codeartsdoer/installers:$PATH"

    check_and_install_cli
    check_aksk
    check_permission
    verify_connection

    # Environment ready
    log_info "Environment ready, can execute code generation"
    printf '{"status":"ready","code":0,"message":"Environment setup complete, ready for code generation"}\n'
    exit 0
}

# ============================================
# Parse command line arguments (#113-6 / #113-9)
#   Validation happens before any environment work so that a missing or empty
#   value can never crash (`shift` past the end under `set -e`) nor silently
#   fall back to the previously stored credentials.
# ============================================
PARSE_ARGS_AK=""
PARSE_ARGS_SK=""
SAVE_AKSK=false
CLEAR_AKSK=false
AK_GIVEN=false
SK_GIVEN=false

while [ $# -gt 0 ]; do
    case "$1" in
        --save-aksk)
            SAVE_AKSK=true
            if [ $# -lt 3 ]; then
                output_error 2 "invalid_arguments" \
                    "--save-aksk requires exactly 2 values: <AK> <SK> (got $(( $# - 1 )))" \
                    "Usage: setup.sh --save-aksk <AK> <SK>"
            fi
            PARSE_ARGS_AK="$2"
            PARSE_ARGS_SK="$3"
            shift 3
            ;;
        --ak)
            if [ $# -lt 2 ]; then
                output_error 2 "invalid_arguments" \
                    "--ak requires a value" \
                    "Usage: setup.sh --ak <AK>"
            fi
            AK_GIVEN=true
            PARSE_ARGS_AK="$2"
            shift 2
            ;;
        --sk)
            if [ $# -lt 2 ]; then
                output_error 2 "invalid_arguments" \
                    "--sk requires a value" \
                    "Usage: setup.sh --sk <SK>"
            fi
            SK_GIVEN=true
            PARSE_ARGS_SK="$2"
            shift 2
            ;;
        --clear-aksk)
            CLEAR_AKSK=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

validate_credential() {
    local name="$1" value="$2"
    case "$value" in
        *'"'*|*'\'*|*'$'*|*'`'*|*$'\n'*|*$'\r'*)
            output_error 2 "invalid_arguments" \
                "$name contains characters that cannot be stored safely (quote, backslash, dollar, backtick or newline)" \
                "Usage: setup.sh --save-aksk <AK> <SK>"
            ;;
    esac
    return 0
}

if [ "$CLEAR_AKSK" = true ]; then
    clear_aksk
fi

if [ "$SAVE_AKSK" = true ]; then
    if [ -z "$PARSE_ARGS_AK" ] || [ -z "$PARSE_ARGS_SK" ]; then
        output_error 2 "empty_credentials" \
            "AK and SK must not be empty" \
            "Usage: setup.sh --save-aksk <AK> <SK>"
    fi
    validate_credential "AK" "$PARSE_ARGS_AK"
    validate_credential "SK" "$PARSE_ARGS_SK"
fi

if [ "$AK_GIVEN" = true ] && [ -z "$PARSE_ARGS_AK" ]; then
    output_error 2 "empty_credentials" \
        "--ak value must not be empty" \
        "Usage: setup.sh --ak <AK>"
fi

if [ "$SK_GIVEN" = true ] && [ -z "$PARSE_ARGS_SK" ]; then
    output_error 2 "empty_credentials" \
        "--sk value must not be empty" \
        "Usage: setup.sh --sk <SK>"
fi

main
