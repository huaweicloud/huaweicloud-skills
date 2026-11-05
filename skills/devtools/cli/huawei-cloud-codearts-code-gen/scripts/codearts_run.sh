#!/usr/bin/env bash
# =============================================================================
# codearts_run.sh - stable contract wrapper around the external `codearts` CLI
#
# The `codearts` CLI is downloaded at runtime from Huawei Cloud OBS and cannot
# be patched from this repository, so the missing contract is enforced here:
#
#   #113-3  `codearts models` without AK/SK exited 0        -> creds pre-check, exit 10
#   #113-4  `codearts run --format json` failure exited 0    -> exit-code + stdout checks
#   #113-5  `--format json` wrote non-JSON text to stdout    -> JSONL validation, exit 60
#   #113-8  CLI error text did not match auth detection      -> error classification 50/40
#   #113-14 `codearts run -f FILE` was broken                -> -f is inlined by the wrapper
#
# Usage:
#   bash scripts/codearts_run.sh models
#   bash scripts/codearts_run.sh run --format json -m "<provider/model>" [-f FILE]... "<task>"
#
#   `--file` is equivalent to `-f`; `--file=<path>` is accepted as well.
#   The `<task>` description must be the LAST positional argument; attachments are
#   appended to it as markdown fenced blocks. `-f`/`--file` and their file
#   arguments are never forwarded to the CLI.
#
# Exit codes (frozen contract, CG-CONTEXT.md 2.3):
#   0   success                    - CLI stdout is forwarded verbatim
#   1   cli_failed                 - CLI exited non-zero (not auth / not network)
#   10  aksk_required              - CODEARTS_CLI_AK / CODEARTS_CLI_SK missing
#   30  cli_not_installed          - codearts executable not found
#   40  network_failed             - timeout / connection / DNS / proxy errors
#   50  auth_failed                - unauthorized / authentication / invalid key
#   60  output_contract_violation  - CLI exited 0 but produced an unusable payload
#   60  attachment_failed          - -f file missing, unreadable or empty
#
# stdout contract (hard rule):
#   success -> the CLI stdout, byte for byte;
#   failure -> exactly one JSON object {status,code,type,message,fix_hint};
#   every log line goes to stderr with the [codearts_run] prefix.
#
# Environment:
#   CODEARTS_CLI_BIN  - path (or command name) of the codearts CLI.
#                       Default: $HOME/.codeartsdoer/installers/codearts
#   CODEARTS_CLI_AK   - Huawei Cloud Access Key; fallback: ~/.bashrc
#   CODEARTS_CLI_SK   - Huawei Cloud Secret Key; fallback: ~/.bashrc
#
# Compatibility: bash 3.2 (macOS system bash). No mapfile, no declare -A, no
# ${var,,} / ${var^^}, no ${var@Q}. LF line endings, UTF-8 without BOM.
# =============================================================================

set -u
umask 022

LOG_PREFIX="[codearts_run]"

log() {
    printf '%s %s\n' "$LOG_PREFIX" "$*" >&2
}

# -----------------------------------------------------------------------------
# Error classification patterns (issue #113-8: unify detection instead of
# relying on the CLI's inconsistent wording).
# -----------------------------------------------------------------------------
AUTH_RE='unauthorized|authentication|invalid.*key|ak/sk'
NET_RE='timeout|timed out|connection|network|resolve|proxy|refused'
# Only used to catch "exit 0 but stdout is a CLI diagnostic" (#113-3/4/5).
ERROR_HEAD_RE='^[[:space:]]*\[?(error|unexpected error|failed|failure|exception|unauthorized|authentication|invalid[[:space:]_-]+(ak|access[[:space:]_-]*key)|ak/sk|fatal|panic|timeout|timed out|connection (refused|failed|reset|error)|network (error|unreachable|is unreachable))'

# -----------------------------------------------------------------------------
# Structured output helpers. stdout must stay clean: exactly one JSON object on
# failure, nothing else. All diagnostics go to stderr.
# -----------------------------------------------------------------------------
json_escape() {
    printf '%s' "${1:-}" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' \
        -e ':a' -e 'N' -e '$!ba' -e 's/\n/\\n/g' -e 's/\r/\\r/g' -e 's/\t/\\t/g'
}

emit_error() {
    local code="${1:-1}"
    local etype="${2:-cli_failed}"
    local msg="${3:-}"
    local hint="${4:-}"
    printf '{"status":"error","code":%s,"type":"%s","message":"%s","fix_hint":"%s"}\n' \
        "$code" "$etype" "$(json_escape "$msg")" "$(json_escape "$hint")"
    exit "$code"
}

emit_need_input() {
    printf '{"status":"need_input","code":10,"type":"aksk_required","message":"%s"}\n' \
        "$(json_escape "${1:-}")"
    exit 10
}

matches_re() {
    printf '%s\n' "${1:-}" | grep -E -q -i -e "$2"
}

first_meaningful_line() {
    local line
    line=$(printf '%s\n' "${1:-}" | grep -E -v '^[[:space:]]*$' | sed -n '1p')
    line=$(printf '%s' "$line" | tr -d '\r')
    printf '%s' "${line:0:200}"
}

# -----------------------------------------------------------------------------
# Temporary work directory (removed on exit).
# -----------------------------------------------------------------------------
WORK_DIR=""

cleanup() {
    if [ -n "${WORK_DIR:-}" ] && [ -d "$WORK_DIR" ]; then
        rm -rf "$WORK_DIR"
    fi
}
trap cleanup EXIT

make_work_dir() {
    local base="${TMPDIR:-/tmp}"
    if command -v mktemp >/dev/null 2>&1; then
        WORK_DIR=$(mktemp -d "$base/codearts_run.XXXXXX" 2>/dev/null) || WORK_DIR=""
    fi
    if [ -z "$WORK_DIR" ]; then
        WORK_DIR="$base/codearts_run.$$"
        mkdir -p "$WORK_DIR" 2>/dev/null || \
            emit_error 1 "cli_failed" \
                "Cannot create a temporary directory under $base" \
                "Set TMPDIR to a writable directory and retry"
    fi
}

# -----------------------------------------------------------------------------
# JSON parsing: prefer python3/python, fall back to a grep heuristic (#113-7
# style portability: no hard dependency on python or jq).
# -----------------------------------------------------------------------------
PY_BIN=""

detect_python() {
    local cand
    for cand in python3 python; do
        if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import json' >/dev/null 2>&1; then
            PY_BIN="$cand"
            log "stdout checks: using $cand"
            return 0
        fi
    done
    PY_BIN=""
    log "stdout checks: no python3/python available, using the grep fallback"
    return 1
}

# Echoes a human readable reason and returns 1 (not JSON) / 3 (error object).
jsonl_reason_python() {
    printf '%s\n' "${1:-}" | "$PY_BIN" -c '
import json
import sys

for raw in sys.stdin:
    line = raw.strip()
    if not line:
        continue
    try:
        obj = json.loads(line)
    except Exception as exc:
        sys.stdout.write("line is not valid JSON (" + str(exc) + ")")
        sys.exit(1)
    if isinstance(obj, dict) and obj.get("type") == "error":
        sys.stdout.write("stdout contains a top-level error object")
        sys.exit(3)
sys.exit(0)
'
}

# Heuristic fallback used when no python is available. Returns 0 / 1 / 3.
jsonl_reason_grep() {
    local bad
    bad=$(printf '%s\n' "${1:-}" | grep -E -v '^[[:space:]]*$' \
        | grep -E -v '^[[:space:]]*\{.*\}[[:space:]]*$' | sed -n '1p')
    if [ -n "$bad" ]; then
        printf 'line is not a JSON object (%s)' "$(first_meaningful_line "$bad")"
        return 1
    fi
    if printf '%s\n' "${1:-}" | grep -E -q '"type"[[:space:]]*:[[:space:]]*"error"'; then
        printf 'stdout contains a top-level error object'
        return 3
    fi
    return 0
}

# -----------------------------------------------------------------------------
# CLI resolution (#113: $CODEARTS_CLI_BIN wins so the wrapper can be tested and
# so an operator can pin a specific build).
# -----------------------------------------------------------------------------
CLI_BIN=""

resolve_cli() {
    local cand="${CODEARTS_CLI_BIN:-}"
    if [ -z "$cand" ]; then
        cand="${HOME:-}/.codeartsdoer/installers/codearts"
    fi
    if [ -f "$cand" ]; then
        CLI_BIN="$cand"
    elif command -v "$cand" >/dev/null 2>&1; then
        CLI_BIN="$cand"
    else
        emit_error 30 "cli_not_installed" \
            "codearts CLI not found: $cand" \
            "Run 'bash scripts/setup.sh' to install it, or set CODEARTS_CLI_BIN to the CLI path"
    fi
    log "using CLI: $CLI_BIN"
}

# Decides how the CLI is launched. A file that exists but lost its executable
# bit (archive / CI checkout) is run through `sh` when it carries a shebang;
# anything else is reported as not installed. Note: emit_error must never run
# inside a command substitution or a redirect, so this is decided up front.
CLI_RUNNER=""

select_runner() {
    CLI_RUNNER=""
    if [ -x "$CLI_BIN" ]; then
        return 0
    fi
    if head -c 2 "$CLI_BIN" 2>/dev/null | grep -q '#!'; then
        log "CLI is not executable, running it through sh"
        CLI_RUNNER="sh"
        return 0
    fi
    emit_error 30 "cli_not_installed" \
        "$CLI_BIN exists but is not executable" \
        "chmod +x '$CLI_BIN' or reinstall the CodeArts CLI"
}

# -----------------------------------------------------------------------------
# Credentials (#113-3: fail before the CLI runs instead of trusting exit 0).
# -----------------------------------------------------------------------------
load_creds() {
    local ak="${CODEARTS_CLI_AK:-}"
    local sk="${CODEARTS_CLI_SK:-}"
    local bashrc="${HOME:-}/.bashrc"

    if [ -f "$bashrc" ] && { [ -z "$ak" ] || [ -z "$sk" ]; }; then
        log "loading AK/SK from $bashrc"
        if [ -z "$ak" ]; then
            ak=$(read_bashrc_value "$bashrc" "CODEARTS_CLI_AK")
        fi
        if [ -z "$sk" ]; then
            sk=$(read_bashrc_value "$bashrc" "CODEARTS_CLI_SK")
        fi
    fi

    if [ -z "$ak" ] || [ -z "$sk" ]; then
        log "AK/SK not configured"
        emit_need_input "Huawei Cloud AK/SK required: set CODEARTS_CLI_AK and CODEARTS_CLI_SK, or run 'bash scripts/setup.sh --save-aksk <AK> <SK>'"
    fi

    export CODEARTS_CLI_AK="$ak"
    export CODEARTS_CLI_SK="$sk"
}

read_bashrc_value() {
    local file="$1"
    local name="$2"
    local line
    line=$(grep -E "^export ${name}=" "$file" 2>/dev/null | sed -n '$p')
    [ -n "$line" ] || return 0
    printf '%s' "$line" | sed -e "s/^export ${name}=//" -e 's/\r$//' \
        -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}

# -----------------------------------------------------------------------------
# Attachment support (#113-14). `-f` / `--file` are consumed by the wrapper and
# the file body is appended to the task description as a fenced markdown block.
# -----------------------------------------------------------------------------
fence_for() {
    local content="$1"
    local longest=0
    if command -v awk >/dev/null 2>&1; then
        longest=$(printf '%s\n' "$content" | awk '
            {
                line = $0
                while (match(line, /`+/)) {
                    if (RLENGTH > max) max = RLENGTH
                    line = substr(line, RSTART + RLENGTH)
                }
            }
            END { print max + 0 }
        ' 2>/dev/null)
    fi
    case "$longest" in
        ''|*[!0-9]*) longest=0 ;;
    esac
    local n=$((longest + 1))
    [ "$n" -lt 3 ] && n=3
    local out=""
    local k=0
    while [ "$k" -lt "$n" ]; do
        out="${out}\`"
        k=$((k + 1))
    done
    printf '%s' "$out"
}

# Reads an attachment into the global ATT_CONTENT. Never call this from a
# command substitution: emit_error must terminate the whole wrapper.
ATT_CONTENT=""

read_attachment() {
    local file="$1"
    ATT_CONTENT=""
    if [ ! -e "$file" ]; then
        emit_error 60 "attachment_failed" \
            "Attachment file not found: $file" \
            "Pass an existing file: -f <path>"
    fi
    if [ ! -f "$file" ]; then
        emit_error 60 "attachment_failed" \
            "Attachment is not a regular file: $file" \
            "Pass a regular file: -f <path>"
    fi
    if [ ! -r "$file" ]; then
        emit_error 60 "attachment_failed" \
            "Attachment file is not readable: $file" \
            "Check file permissions: -f <path>"
    fi
    local content
    content=$(cat "$file" 2>/dev/null) || content=""
    if [ -z "$content" ]; then
        emit_error 60 "attachment_failed" \
            "Attachment file is empty: $file" \
            "Attach a non-empty file: -f <path>"
    fi
    ATT_CONTENT="$content"
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    local ARGS=()
    local FILES=()
    local missing_file_arg=0

    # --- 1. split argv: the wrapper consumes -f/--file, the CLI gets the rest ---
    while [ $# -gt 0 ]; do
        case "$1" in
            -f|--file)
                if [ $# -lt 2 ]; then
                    missing_file_arg=1
                    shift
                    break
                fi
                FILES[${#FILES[@]}]="$2"
                shift 2
                ;;
            --file=*)
                FILES[${#FILES[@]}]="${1#--file=}"
                shift
                ;;
            *)
                ARGS[${#ARGS[@]}]="$1"
                shift
                ;;
        esac
    done

    # --- 2. locate the CLI -------------------------------------------------
    resolve_cli

    # --- 3. credentials ----------------------------------------------------
    load_creds

    # --- 4. attachments ----------------------------------------------------
    if [ "$missing_file_arg" -eq 1 ]; then
        emit_error 60 "attachment_failed" \
            "Missing file path after -f/--file" \
            "Usage: codearts_run.sh run -f <file> \"<task>\""
    fi

    if [ "${#FILES[@]}" -gt 0 ]; then
        # The task description is the last positional argument. A valid call with
        # an attachment always carries the sub-command plus the task ("run ... <task>"),
        # so at least two positionals must be present; otherwise the attachment would
        # be appended to the sub-command or to a model id.
        if [ "${#ARGS[@]}" -lt 2 ]; then
            emit_error 60 "attachment_failed" \
                "Attachment given but there is no task description to attach it to (the task must be the last argument after the sub-command)" \
                "Usage: codearts_run.sh run -f <file> \"<task>\""
        fi
        local last=$(( ${#ARGS[@]} - 1 ))
        local prompt="${ARGS[$last]}"
        local i=0
        local file content fence
        while [ "$i" -lt "${#FILES[@]}" ]; do
            file="${FILES[$i]}"
            read_attachment "$file"
            content="$ATT_CONTENT"
            fence=$(fence_for "$content")
            prompt="${prompt}

----- Attached file: ${file} -----
${fence}
${content}
${fence}"
            log "attached file: $file"
            i=$((i + 1))
        done
        ARGS[$last]="$prompt"
    fi

    # --- 5. is this a JSON output session? (#113-5) ------------------------
    local json_mode=0
    local idx=0
    local n=${#ARGS[@]}
    local cur nxt
    while [ "$idx" -lt "$n" ]; do
        cur="${ARGS[$idx]}"
        if [ "$cur" = "--format" ] && [ $((idx + 1)) -lt "$n" ]; then
            nxt="${ARGS[$((idx + 1))]}"
            if printf '%s' "$nxt" | grep -E -q -i '^json$'; then
                json_mode=1
            fi
            idx=$((idx + 2))
            continue
        fi
        case "$cur" in
            --format=*)
                if printf '%s' "${cur#--format=}" | grep -E -q -i '^json$'; then
                    json_mode=1
                fi
                ;;
        esac
        idx=$((idx + 1))
    done

    # --- 6. execute --------------------------------------------------------
    make_work_dir
    local out_file="$WORK_DIR/stdout"
    local err_file="$WORK_DIR/stderr"
    local rc=0

    log "executing: $CLI_BIN (${#ARGS[@]} args, json_mode=$json_mode)"
    select_runner
    if [ "${#ARGS[@]}" -gt 0 ]; then
        if [ -n "$CLI_RUNNER" ]; then
            "$CLI_RUNNER" "$CLI_BIN" "${ARGS[@]}" >"$out_file" 2>"$err_file"
        else
            "$CLI_BIN" "${ARGS[@]}" >"$out_file" 2>"$err_file"
        fi
        rc=$?
    else
        if [ -n "$CLI_RUNNER" ]; then
            "$CLI_RUNNER" "$CLI_BIN" >"$out_file" 2>"$err_file"
        else
            "$CLI_BIN" >"$out_file" 2>"$err_file"
        fi
        rc=$?
    fi

    # CLI stderr is forwarded verbatim to the wrapper's stderr.
    if [ -s "$err_file" ]; then
        cat "$err_file" >&2
    fi

    local out_content=""
    if [ -s "$out_file" ]; then
        out_content=$(cat "$out_file")
    fi
    local err_content=""
    if [ -s "$err_file" ]; then
        err_content=$(cat "$err_file")
    fi

    # --- 7. non-zero exit: classify the failure (never exit 0) -------------
    if [ "$rc" -ne 0 ]; then
        local combined="${out_content}
${err_content}"
        if matches_re "$combined" "$AUTH_RE"; then
            emit_error 50 "auth_failed" \
                "codearts CLI failed with exit code $rc: authentication error ($(first_meaningful_line "$combined"))" \
                "Verify CODEARTS_CLI_AK/CODEARTS_CLI_SK and re-run 'bash scripts/setup.sh --save-aksk <AK> <SK>' if needed"
        fi
        if matches_re "$combined" "$NET_RE"; then
            emit_error 40 "network_failed" \
                "codearts CLI failed with exit code $rc: network error ($(first_meaningful_line "$combined"))" \
                "Check network connectivity, proxy settings and retry"
        fi
        emit_error 1 "cli_failed" \
            "codearts CLI failed with exit code $rc: $(first_meaningful_line "$combined")" \
            "Inspect the CLI stderr above and re-run the command"
    fi

    # --- 8. exit 0: verify the output contract -----------------------------
    if [ -z "$out_content" ]; then
        local empty_msg="codearts CLI exited 0 but wrote nothing to stdout"
        if [ -n "$err_content" ]; then
            empty_msg="$empty_msg; stderr said: $(first_meaningful_line "$err_content")"
        fi
        if matches_re "$err_content" "$AUTH_RE"; then
            emit_error 50 "auth_failed" "$empty_msg" \
                "Verify CODEARTS_CLI_AK/CODEARTS_CLI_SK; the CLI reported an authentication error"
        fi
        if matches_re "$err_content" "$NET_RE"; then
            emit_error 40 "network_failed" "$empty_msg" \
                "Check network connectivity, proxy settings and retry"
        fi
        emit_error 60 "output_contract_violation" "$empty_msg" \
            "The CLI reported success without a payload; check AK/SK and network, then retry"
    fi

    if [ "$json_mode" -eq 1 ]; then
        local reason
        local vrc
        if [ -n "$PY_BIN" ]; then
            reason=$(jsonl_reason_python "$out_content")
            vrc=$?
        else
            reason=$(jsonl_reason_grep "$out_content")
            vrc=$?
        fi
        if [ "$vrc" -ne 0 ]; then
            emit_error 60 "output_contract_violation" \
                "codearts CLI exited 0 but stdout violates the --format json contract: $reason" \
                "The CLI must print one JSON object per line in json mode; retry or report this to the CodeArts CLI maintainers"
        fi
    fi

    # #113-3/#113-4: the CLI sometimes prints a diagnostic and still exits 0.
    local head_line
    head_line=$(first_meaningful_line "$out_content")
    if matches_re "$head_line" "$ERROR_HEAD_RE"; then
        if matches_re "$out_content" "$AUTH_RE"; then
            emit_error 50 "auth_failed" \
                "codearts CLI exited 0 but stdout reports an authentication error: $head_line" \
                "Verify CODEARTS_CLI_AK/CODEARTS_CLI_SK"
        fi
        if matches_re "$out_content" "$NET_RE"; then
            emit_error 40 "network_failed" \
                "codearts CLI exited 0 but stdout reports a network error: $head_line" \
                "Check network connectivity, proxy settings and retry"
        fi
        emit_error 60 "output_contract_violation" \
            "codearts CLI exited 0 but stdout is an error message: $head_line" \
            "The CLI reported success while printing an error; inspect the message above"
    fi

    if [ "$json_mode" -eq 0 ]; then
        case "$out_content" in
            \{*)
                if printf '%s\n' "$out_content" | grep -E -q '"type"[[:space:]]*:[[:space:]]*"error"'; then
                    emit_error 60 "output_contract_violation" \
                        "codearts CLI exited 0 but stdout carries a top-level error object" \
                        "The CLI reported success while returning an error payload"
                fi
                ;;
        esac
    fi

    # --- 9. success: forward the CLI stdout byte for byte ------------------
    log "success"
    cat "$out_file"
    exit 0
}

detect_python
main "$@"
