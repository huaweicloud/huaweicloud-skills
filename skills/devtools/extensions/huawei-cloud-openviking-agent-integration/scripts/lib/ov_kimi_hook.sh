#!/usr/bin/env bash
set -uo pipefail   # ROB-1: catch unset vars + pipe failures (omit -e: hook is error-tolerant by design)
# ov-kimi-hook.sh — KimiCode OpenViking hook dispatcher (v3)
# Usage: ov-kimi-hook.sh <event>   (reads JSON from stdin)
# Events: session-start | user-prompt | stop | session-end | pre-compact | pre-tool-use | subagent-start | subagent-stop
#
# v3 (aligned with the official @openviking/opencode-plugin / dsh-memory-plugin):
#   - P0-1: incremental idempotent wire.jsonl capture via byte-offset cursor
#           (fixes "last user + last-5 assistant" loss; no re-upload, no dropped turns)
#   - P0-2: commit gate driven by server pending_tokens (GET /sessions/{sid}),
#           with keep_recent_count; turn/chars as local fallback
#   - P1-3: durable pending queue (~/.openviking/pending, 0700/0600, sha256 dedup,
#           .processing rename, 3 retries / 7d TTL, replay on session-start + stop)
#   - P1-4: Bash no longer blocked by the PreToolUse viking:// URI guard
#   - P2-5: signal filter drops ack / slash / punctuation / too-short text
#   - P2-6: session-start injects <session-archive> from GET context archive overview
#   - P2-7: recall adds purpose:"coding" + dedup_turns (+ optional peer_scope),
#           400/422/404/405/5xx → /api/v1/search/recall fallback
#   - P2-8: config-file values now actually read (openviking-config.json),
#           env > config > default precedence
# Preserved: redaction, sanitize, git peer-id, bypass env, per-session flock,
#            subagent isolation, crash-recovery sweep.

OV_ENDPOINT="${OV_ENDPOINT:-http://127.0.0.1:1933}"
OV_HOME="${OV_HOME:-${HOME:-/root}}"
OV_RUNTIME_DIR="${OV_RUNTIME_DIR:-${OV_HOME}/runtime}"
OV_STATE_DIR="${OV_STATE_DIR:-/tmp/ov-kimi-hooks}"
# KIMI_CODE_HOME is set by the job-env start.sh (e.g. /root/runtime/kimicode/data),
# which is the correct parent of the sessions/ dir — prefer it over $OV_HOME/runtime.
KC_DATA_DIR="${KC_DATA_DIR:-${KIMI_CODE_HOME:-${OV_RUNTIME_DIR}/kimicode/data}}"
OV_PY3="${OV_PY3:-$(command -v python3.12 2>/dev/null || command -v python3.11 2>/dev/null || command -v python3.10 2>/dev/null || command -v python3 2>/dev/null || echo python3)}"
OV_PY="${OV_PY:-$OV_PY3}"
OV_PY_DIR="${OV_PY_DIR:-$(dirname "$(readlink -f "$0")")/../py}"
OV_CURL_BIN="${OV_CURL_BIN:-$(command -v curl 2>/dev/null || echo curl)}"
OV_PENDING_DIR="${OV_PENDING_DIR:-${OV_HOME}/.openviking/pending}"
OV_PENDING_MAX_RETRIES="${OV_PENDING_MAX_RETRIES:-3}"
OV_PENDING_TTL_DAYS="${OV_PENDING_TTL_DAYS:-7}"
OV_PENDING_REPLAY_LIMIT="${OV_PENDING_REPLAY_LIMIT:-50}"
OV_MAX_ATTEMPTS="${OV_MAX_ATTEMPTS:-3}"
OV_COMMIT_TURN_THRESHOLD="${OV_COMMIT_TURN_THRESHOLD:-5}"
OV_COMMIT_CHAR_THRESHOLD="${OV_COMMIT_CHAR_THRESHOLD:-20000}"
OV_RECALL_DEDUP_TURNS="${OV_RECALL_DEDUP_TURNS:-5}"
OV_RECALL_PEER_SCOPE="${OV_RECALL_PEER_SCOPE:-}"
OV_CAPTURE_USER_MAX_CHARS="${OV_CAPTURE_USER_MAX_CHARS:-8000}"
OV_CAPTURE_ASSISTANT_MAX_CHARS="${OV_CAPTURE_ASSISTANT_MAX_CHARS:-32000}"

mkdir -p "$OV_STATE_DIR" && chmod 700 "$OV_STATE_DIR" 2>/dev/null || true
EVENT="$1"; INPUT=$(cat)

# ── Python CLI dispatch ──
_ov_kimi_hook(){ "$OV_PY" "$OV_PY_DIR/ov_kimi_hook.py" "$@"; }

# ── Helpers ──
_jf(){ echo "$INPUT"|_ov_kimi_hook json-field "$1" 2>/dev/null;}
_sid(){ echo -n "$1"|md5sum|cut -c1-16;}
_ov_out(){ _ov_kimi_hook hook-output "$1" 2>/dev/null;}
_ov_deny(){ _ov_kimi_hook hook-deny "$1" 2>/dev/null;}
_ov_log(){ echo "[ov-hook:$EVENT] $*" >&2;}
_json_str(){ _ov_kimi_hook json-encode "$1" 2>/dev/null;}

# Shared response buffer + cleanup (one hook process per event; $$ is unique)
_OV_RESP="${OV_STATE_DIR}/ov-resp-$$"
trap 'rm -f "$_OV_RESP" 2>/dev/null' EXIT

# ── Status-aware POST with bounded retry ──
# Echoes nothing on stdout; stores the HTTP code in _OV_CODE and the response
# body in $_OV_RESP.  Retries transient failures (408/429/5xx/409-retryable/000)
# up to OV_MAX_ATTEMPTS, then gives up (callers enqueue to the pending queue).
_ov_send(){
  local path="$1" body="$2" i code
  i=0; code=""
  while [ "$i" -lt "$OV_MAX_ATTEMPTS" ]; do
    i=$((i+1))
    code=$("$OV_CURL_BIN" -s -o "$_OV_RESP" -w "%{http_code}" --connect-timeout 3 --max-time 12 -X POST "${OV_ENDPOINT}${path}" -H 'Content-Type: application/json' -H 'X-OpenViking-Agent: kimicode' -d "$body" 2>/dev/null)
    case "$code" in
      2*) break ;;
      409) grep -q '"retryable"[[:space:]]*:[[:space:]]*true' "$_OV_RESP" 2>/dev/null || break ;;
      408|429|5[0-9][0-9]) : ;;
      *) break ;;
    esac
    [ "$i" -eq "$OV_MAX_ATTEMPTS" ] && break
    sleep 1
  done
  _OV_CODE="$code"
}

# ── Retryability test (P1-3) ──
_ov_retryable(){
  case "$1" in
    408|429|5[0-9][0-9]) return 0 ;;
  esac
  if [ "$1" = "409" ] && [ -n "$2" ]; then
    echo "$2" | grep -q '"retryable"[[:space:]]*:[[:space:]]*true' && return 0
  fi
  return 1
}

# ── Pending queue ──
_ov_queue_add(){ # $1=kind $2=path $3=body
  mkdir -p "$OV_PENDING_DIR" && chmod 700 "$OV_PENDING_DIR" 2>/dev/null || true
  _ov_kimi_hook pending-enqueue "$OV_PENDING_DIR" "$1" "$2" "$3" 2>/dev/null
}

_ov_post(){ # $1=path $2=body $3=kind(default:message); enqueues on retryable failure
  local path="$1" body="$2" kind="${3:-message}"
  _ov_send "$path" "$body"
  if [ "${_OV_CODE:-000}" = "000" ] || _ov_retryable "${_OV_CODE:-000}" "$(cat "$_OV_RESP" 2>/dev/null)"; then
    _ov_queue_add "$kind" "$path" "$body"
    _ov_log "queue+ http=${_OV_CODE} ${path}"
    return 1
  fi
  return 0
}

_ov_replay(){ # claim + deliver pending items (idempotent; bounded)
  [ -d "$OV_PENDING_DIR" ] || return 0
  local i=0 file claimed path body code resp
  for file in "$OV_PENDING_DIR"/*.json; do
    [ -e "$file" ] || continue
    [ "$i" -ge "$OV_PENDING_REPLAY_LIMIT" ] && break
    i=$((i+1))
    claimed="${file}.processing"
    mv "$file" "$claimed" 2>/dev/null || continue
    if [ "$(_ov_kimi_hook pending-should-send "$claimed" "$OV_PENDING_MAX_RETRIES" "$OV_PENDING_TTL_DAYS" 2>/dev/null)" != "SEND" ]; then
      rm -f "$claimed" 2>/dev/null; continue
    fi
    path=$(_ov_kimi_hook pending-get "$claimed" path 2>/dev/null)
    body=$(_ov_kimi_hook pending-body "$claimed" 2>/dev/null)
    [ -z "$path" ] && { rm -f "$claimed" 2>/dev/null; continue; }
    _ov_send "$path" "$body"
    code="${_OV_CODE:-000}"; resp=$(cat "$_OV_RESP" 2>/dev/null)
    if [ "$code" = "000" ] || _ov_retryable "$code" "$resp"; then
      _ov_kimi_hook pending-bump "$claimed" 2>/dev/null
      mv "$claimed" "$file" 2>/dev/null
      _ov_log "replay retryable http=${code}: ${path}"
    else
      rm -f "$claimed" 2>/dev/null
      _ov_log "replay settled http=${code}: ${path}"
    fi
  done
}

_ov_pending_tokens(){ # GET /sessions/{sid} → pending_tokens int (0 on failure)
  local R
  R=$("$OV_CURL_BIN" -s --connect-timeout 3 --max-time 8 -H 'Accept: application/json' "${OV_ENDPOINT}/api/v1/sessions/$1" 2>/dev/null)
  echo "$R" | _ov_kimi_hook pending-tokens 2>/dev/null
}

_ov_signal_filter(){ _ov_kimi_hook filter-signal "$1" 2>/dev/null; }

# ── Config-file resolution (P2-8): env > openviking-config.json > default ──
OV_CONFIG_FILE="${OV_CONFIG_FILE:-${OV_HOME}/.config/opencode/openviking-config.json}"
_ov_conf(){
  local key="$1" def="${2:-}" v
  if [ -n "$OV_CONFIG_FILE" ] && [ -f "$OV_CONFIG_FILE" ]; then
    v=$(_ov_kimi_hook config-get "$OV_CONFIG_FILE" "$key" 2>/dev/null)
    [ -n "$v" ] && { printf '%s' "$v"; return; }
  fi
  printf '%s' "$def"
}
OV_COMMIT_TOKEN_THRESHOLD="${OV_COMMIT_TOKEN_THRESHOLD:-$(_ov_conf commitTokenThreshold 20000)}"
OV_COMMIT_KEEP_RECENT_COUNT="${OV_COMMIT_KEEP_RECENT_COUNT:-$(_ov_conf commitKeepRecentCount 10)}"
OV_RESUME_CONTEXT_BUDGET="${OV_RESUME_CONTEXT_BUDGET:-$(_ov_conf resumeContextBudget 32000)}"
OV_RECALL_LIMIT="${OV_RECALL_LIMIT:-$(_ov_conf recallLimit 6)}"
OV_RECALL_SCORE_THRESHOLD="${OV_RECALL_SCORE_THRESHOLD:-$(_ov_conf autoRecall.scoreThreshold 0.35)}"
OV_RECALL_MAX_CHARS="${OV_RECALL_MAX_CHARS:-$(_ov_conf recallMaxContentChars 4000)}"

KC_SID=$(_jf session_id);CWD=$(_jf cwd)
if [ -n "$KC_SID" ];then SID="kimi-$(_sid "$KC_SID")";else SID="kimi-$(_sid "$CWD")";fi
STFILE="${OV_STATE_DIR}/ws-$(_sid "${CWD:-default}").state"
LOCKFILE="${OV_STATE_DIR}/ws-$(_sid "${CWD:-default}").lock"

# ── Bypass check ──
_ov_bypass(){
  [ "${OPENVIKING_BYPASS_SESSION:-}" = "1" ] && return 0
  if [ -n "${OPENVIKING_BYPASS_SESSION_PATTERNS:-}" ] && [ -n "$CWD" ]; then
    echo "$OPENVIKING_BYPASS_SESSION_PATTERNS" | tr ',' '\n' | while read -r pat; do
      [ -n "$pat" ] && echo "$CWD" | grep -q "$pat" && return 0
    done && return 0
  fi
  return 1
}

# ── Git-based peer derivation ──
_ov_peer_id(){
  local dir="${1:-$CWD}"
  _ov_kimi_hook peer-id "$dir" 2>/dev/null
}

# ── Locking (flock-based, kernel-level advisory lock — no TOCTOU) ──
_ov_lock(){
  exec 9>"${LOCKFILE}"
  flock -w 2 9
}
_ov_unlock(){ flock -u 9 2>/dev/null || true; }

# ── Memory pollution prevention: strip injected tags ──
_ov_sanitize(){
  _ov_kimi_hook sanitize "$1" 2>/dev/null
}

# ── PII/Secret redaction before transmission to OpenViking ──
_ov_redact(){
  if [ "${OV_REDACT_SECRETS:-true}" != "true" ]; then printf '%s' "$1"; return; fi
  local _tmp; _tmp=$(mktemp 2>/dev/null) || { printf '%s' "$1"; return; }
  printf '%s' "$1" > "$_tmp"
  "$OV_PY" "$OV_PY_DIR/ov_redact.py" redact "$_tmp" 2>/dev/null || printf '%s' "$1"
  rm -f "$_tmp" 2>/dev/null
}

# ── Extract user/assistant text from wire.jsonl (incremental, idempotent) ──
_ov_extract_wire(){
  local kc_sid="$1" cursor="$2" sd wf
  [ -z "$kc_sid" ] && return
  sd=$(find "$KC_DATA_DIR/sessions" -maxdepth 2 -type d \( -name "$kc_sid" -o -name "session_${kc_sid}" \) 2>/dev/null | head -1)
  [ -z "$sd" ] && return
  wf="$sd/agents/main/wire.jsonl"
  [ ! -f "$wf" ] && return
  _ov_kimi_hook extract-wire "$wf" "$cursor" "$OV_CAPTURE_USER_MAX_CHARS" "$OV_CAPTURE_ASSISTANT_MAX_CHARS" 2>/dev/null
}

# ── Recall search and format (P2-7) ──
_ov_recall(){
  local query="$1" session_id="$2" code fb body
  body="{\"query\":$(_json_str "$query"),\"mode\":\"context\",\"purpose\":\"coding\",\"session_id\":\"${session_id}\",\"limit\":${OV_RECALL_LIMIT},\"score_threshold\":${OV_RECALL_SCORE_THRESHOLD},\"dedup_turns\":${OV_RECALL_DEDUP_TURNS}"
  [ -n "$OV_RECALL_PEER_SCOPE" ] && body="${body},\"peer_scope\":$(_json_str "$OV_RECALL_PEER_SCOPE")"
  body="${body}}"
  _ov_send "/api/v1/search/search" "$body"
  code="${_OV_CODE:-000}"
  case "$code" in
    400|422|404|405|5[0-9][0-9])
      _ov_log "context search http=${code} → recall fallback"
      fb="{\"query\":$(_json_str "$query"),\"session_id\":\"${session_id}\",\"score_threshold\":${OV_RECALL_SCORE_THRESHOLD},\"dedup_turns\":${OV_RECALL_DEDUP_TURNS},\"max_chars\":${OV_RECALL_MAX_CHARS}}"
      _ov_send "/api/v1/search/recall" "$fb"
      ;;
  esac
  cat "$_OV_RESP" 2>/dev/null | _ov_kimi_hook recall-format "${OV_RECALL_MAX_CHARS}" "${OV_RECALL_SCORE_THRESHOLD}" 2>/dev/null
}

# ── Commit session (P0-2: keep_recent_count) ──
_ov_commit(){
  local session_id="$1" reason="$2"
  _ov_post "/api/v1/sessions/${session_id}/commit" "{\"reason\":\"${reason:-auto}\",\"keep_recent_count\":${OV_COMMIT_KEEP_RECENT_COUNT}}" "commit"
}

# ── Update state file ──
_ov_state_update(){
  _ov_kimi_hook state-update "$1" "$2" "$STFILE" 2>/dev/null
}

# ── Early bypass exit ──
if _ov_bypass; then _ov_out ""; exit 0; fi

# ── Main event dispatch ──
case "$EVENT" in
  session-start)
    SOURCE=$(_jf source)
    PEER_ID=$(_ov_peer_id)
    echo "{\"sid\":\"${SID}\",\"kc_sid\":\"${KC_SID}\",\"cwd\":\"${CWD}\",\"peer_id\":\"${PEER_ID}\",\"started\":$(date +%s),\"turn_count\":0,\"accumulated_chars\":0,\"needs_commit\":false,\"last_recall_hash\":\"\"}">"$STFILE"
    _ov_log "sid=${SID} source=${SOURCE} peer=${PEER_ID}"

    # Crash recovery: scan for orphaned sessions with needs_commit=true
    for sf in "$OV_STATE_DIR"/ws-*.state; do
      [ -f "$sf" ] || continue
      [ "$sf" = "$STFILE" ] && continue
      ORPHAN_SID=$(_ov_kimi_hook state-orphan-check "$sf" 2>/dev/null)
      if [ -n "$ORPHAN_SID" ]; then
        _ov_log "crash recovery: committing orphan session ${ORPHAN_SID}"
        _ov_commit "$ORPHAN_SID" "crash-recovery"
        _ov_kimi_hook state-mark-crash-recovered "$sf" 2>/dev/null
      fi
    done

    # Replay pending items left by a previous run (P1-3)
    _ov_replay

    # P2-6: inject <session-archive> overview + workspace recall context
    ARCHIVE=$("$OV_CURL_BIN" -s --connect-timeout 3 --max-time 8 -H 'Accept: application/json' "${OV_ENDPOINT}/api/v1/sessions/${SID}/context?token_budget=${OV_RESUME_CONTEXT_BUDGET}" 2>/dev/null | _ov_kimi_hook archive-overview 2>/dev/null)
    RECALL=$(_ov_recall "workspace context: ${CWD##*/}" "$SID")
    INJECT=$(printf '%s' "$RECALL" | _ov_kimi_hook session-inject "${SID}" "$ARCHIVE" 2>/dev/null)
    if [ -n "$INJECT" ]; then
      _ov_out "$INJECT"
    else
      _ov_out ""
    fi;;

  user-prompt)
    PROMPT=$(_jf prompt)
    [ -f "$STFILE" ]&&_ov_kimi_hook state-set-prompt "$STFILE" "$PROMPT" "$(date +%s)" 2>/dev/null

    # Recall with dedup
    QUERY_HASH=$(echo -n "$PROMPT" | md5sum | cut -c1-8)
    LAST_HASH=""; [ -f "$STFILE" ]&&LAST_HASH=$(_ov_kimi_hook state-get "$STFILE" last_recall_hash 2>/dev/null)

    if [ "$QUERY_HASH" != "$LAST_HASH" ]; then
      RECALL=$(_ov_recall "$(_ov_redact "$PROMPT")" "$SID")
      if [ -n "$RECALL" ]; then
        _ov_state_update "last_recall_hash" "$QUERY_HASH"
        echo "$RECALL" > "${OV_STATE_DIR}/recall-$(_sid "${CWD:-default}").md"
        chmod 600 "${OV_STATE_DIR}/recall-$(_sid "${CWD:-default}").md" 2>/dev/null || true
        _ov_out "$RECALL"
      else
        _ov_out ""
      fi
    else
      _ov_out ""
    fi;;

  pre-tool-use)
    TOOL_NAME=$(_jf tool_name)
    TOOL_INPUT=$(_jf tool_input)
    case "$TOOL_NAME" in
      Read|Glob|Grep|Write|Edit)
        echo "$TOOL_INPUT" | _ov_kimi_hook check-viking-uri 2>/dev/null | grep -q "BLOCK" && {
          _ov_deny "viking:// URIs are virtual paths managed by OpenViking. Use MCP tools instead: openviking_read, openviking_search, openviking_glob, openviking_grep, openviking_list."
          exit 0
        }
        ;;
    esac
    _ov_out "";;

  stop)
    _ov_log "sid=${SID} kc_sid=${KC_SID}"

    if ! _ov_lock; then _ov_log "could not acquire lock, skipping"; _ov_out ""; exit 0; fi
    date +%s > "${LOCKFILE}.ts" 2>/dev/null

    # Flush queued items first (P1-3)
    _ov_replay

    # P0-1: incremental capture (cursor advanced atomically by extract-wire)
    CURSOR_FILE="${OV_STATE_DIR}/wire-${SID}.cursor"
    WD=$(_ov_extract_wire "$KC_SID" "$CURSOR_FILE"); UT=""; AT=""
    if [ -n "$WD" ];then
      UT=$(echo "$WD"|_ov_kimi_hook json-stdin-get user 2>/dev/null)
      AT=$(echo "$WD"|_ov_kimi_hook json-stdin-get assistant 2>/dev/null)
    fi
    if [ -z "$UT" ]&&[ -f "$STFILE" ];then UT=$(_ov_kimi_hook state-get "$STFILE" last_prompt 2>/dev/null);fi

    # Sanitize + redact + signal filter (P2-5)
    UT=$(_ov_sanitize "$UT")
    AT=$(_ov_sanitize "$AT")
    UT=$(_ov_redact "$UT")
    AT=$(_ov_redact "$AT")
    UT=$(_ov_signal_filter "$UT")
    AT=$(_ov_signal_filter "$AT")

    _ov_log "user_len=${#UT} assistant_len=${#AT}"

    if [ -n "$UT" ];then
      ESC=$(_json_str "$UT")
      _ov_post "/api/v1/sessions/${SID}/messages" "{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":${ESC}}]}" "message"
    fi
    if [ -n "$AT" ];then
      EA=$(_json_str "$AT")
      _ov_post "/api/v1/sessions/${SID}/messages" "{\"role\":\"assistant\",\"parts\":[{\"type\":\"text\",\"text\":${EA}}]}" "message"
    else
      _ov_post "/api/v1/sessions/${SID}/messages" "{\"role\":\"assistant\",\"parts\":[{\"type\":\"text\",\"text\":\"Turn completed.\"}]}" "message"
    fi

    # Update state with accumulated stats
    TURN_COUNT=0; ACCUM_CHARS=0
    [ -f "$STFILE" ]&&TURN_COUNT=$(_ov_kimi_hook state-get "$STFILE" turn_count 0 2>/dev/null)
    [ -f "$STFILE" ]&&ACCUM_CHARS=$(_ov_kimi_hook state-get "$STFILE" accumulated_chars 0 2>/dev/null)
    TURN_COUNT=$((TURN_COUNT + 1))
    ACCUM_CHARS=$((ACCUM_CHARS + ${#UT} + ${#AT}))

    # P0-2: commit gate — server pending_tokens primary, turn/chars fallback
    PT=$(_ov_pending_tokens "$SID")
    COMMITTED=false
    if [ -n "$PT" ] && [ "$PT" -ge "$OV_COMMIT_TOKEN_THRESHOLD" ] 2>/dev/null; then
      _ov_commit "$SID" "threshold-pending-${PT}"
      TURN_COUNT=0; ACCUM_CHARS=0; COMMITTED=true
      _ov_log "commit via pending_tokens=${PT}"
    elif [ "$TURN_COUNT" -ge "$OV_COMMIT_TURN_THRESHOLD" ] || [ "$ACCUM_CHARS" -ge "$OV_COMMIT_CHAR_THRESHOLD" ]; then
      _ov_commit "$SID" "threshold-turn-${TURN_COUNT}"
      TURN_COUNT=0; ACCUM_CHARS=0; COMMITTED=true
      _ov_log "commit via fallback threshold (turn/chars)"
    fi
    if [ "$COMMITTED" = true ]; then NEEDS_COMMIT=false; else NEEDS_COMMIT=true; fi

    _ov_kimi_hook state-update-stop "$STFILE" "$NEEDS_COMMIT" "$TURN_COUNT" "$ACCUM_CHARS" 2>/dev/null

    _ov_unlock
    _ov_out "";;

  session-end|pre-compact)
    REASON=$(_jf reason);TRIGGER=$(_jf trigger)
    _ov_log "sid=${SID} reason=${REASON:-${TRIGGER:-compact}}"

    # Flush queued items first (P1-3)
    _ov_replay

    NC=false;[ -f "$STFILE" ]&&NC=$(_ov_kimi_hook state-get-bool "$STFILE" needs_commit 2>/dev/null)
    TC=0;[ -f "$STFILE" ]&&TC=$(_ov_kimi_hook state-get "$STFILE" turn_count 0 2>/dev/null)

    if [ "$NC" = "true" ] || [ "$TC" -gt 0 ]; then
      if [ "$EVENT" = "session-end" ]; then
        # Detached worker to avoid timeout
        (
          _ov_commit "$SID" "session-end"
          [ -f "$STFILE" ]&&_ov_kimi_hook state-mark-committed "$STFILE" 2>/dev/null
        ) & disown 2>/dev/null || true
        _ov_out "OpenViking session committed. Memory extraction in progress."
      else
        # PreCompact: synchronous
        _ov_commit "$SID" "pre-compact"
        [ -f "$STFILE" ]&&_ov_kimi_hook state-mark-committed "$STFILE" 2>/dev/null
        _ov_out ""
      fi
    else
      _ov_out ""
    fi;;



  subagent-start)
    # SubagentStart: create isolated OV session for this subagent
    AGENT_NAME=$(_jf agent_name)
    SUBAGENT_PROMPT=$(_jf prompt)
    [ -z "$AGENT_NAME" ] && AGENT_NAME="unknown"

    # Derive isolated subagent session ID
    SUBAGENT_SID="${SID}__subagent-${AGENT_NAME}-$(date +%s)"
    SUBAGENT_STATE="${OV_STATE_DIR}/subagent-${SID}-${AGENT_NAME}.state"

    PEER_ID=$(_ov_peer_id)
    # Save state (use Python for safe JSON writing)
    _ov_kimi_hook subagent-state-save "$SUBAGENT_STATE" "$SID" "$SUBAGENT_SID" "$AGENT_NAME" "$PEER_ID" "$(date +%s)" 2>/dev/null

    _ov_log "subagent-start: agent=${AGENT_NAME} subagent_sid=${SUBAGENT_SID}"
    _ov_out "";;

  subagent-stop)
    # SubagentStop: capture subagent work to isolated session, then commit
    AGENT_NAME=$(_jf agent_name)
    SUBAGENT_RESPONSE=$(_jf response)
    [ -z "$AGENT_NAME" ] && AGENT_NAME="unknown"

    SUBAGENT_STATE="${OV_STATE_DIR}/subagent-${SID}-${AGENT_NAME}.state"

    # Load subagent state
    SUBAGENT_SID=""
    if [ -f "$SUBAGENT_STATE" ]; then
      SUBAGENT_SID=$(_ov_kimi_hook state-get "$SUBAGENT_STATE" subagent_sid 2>/dev/null)
    fi
    # Fallback: derive session ID if state file missing
    if [ -z "$SUBAGENT_SID" ]; then
      SUBAGENT_SID="${SID}__subagent-${AGENT_NAME}-orphan"
    fi

    _ov_log "subagent-stop: agent=${AGENT_NAME} subagent_sid=${SUBAGENT_SID}"

    # Try to extract full transcript from subagent wire.jsonl (best-effort, opt-in)
    SUBAGENT_FULL=""
    if [ -n "$KC_SID" ] && [ "${OV_CAPTURE_SUBAGENT:-false}" = "true" ]; then
      SUBAGENT_FULL=$(_ov_kimi_hook extract-subagent-transcript "$KC_SID" "$KC_DATA_DIR" 2>/dev/null)
    fi

    # Use full transcript if available, otherwise fall back to hook payload
    if [ -n "$SUBAGENT_FULL" ]; then
      CAPTURE_TEXT="$SUBAGENT_FULL"
    elif [ -n "$SUBAGENT_RESPONSE" ]; then
      CAPTURE_TEXT="$SUBAGENT_RESPONSE"
    else
      CAPTURE_TEXT=""
    fi

    # Sanitize + redact
    CAPTURE_TEXT=$(_ov_sanitize "$CAPTURE_TEXT")
    CAPTURE_TEXT=$(_ov_redact "$CAPTURE_TEXT")

    # Push subagent work to isolated session
    if [ -n "$CAPTURE_TEXT" ]; then
      ESC=$(_json_str "$CAPTURE_TEXT")
      _ov_post "/api/v1/sessions/${SUBAGENT_SID}/messages" "{\"role\":\"assistant\",\"parts\":[{\"type\":\"text\",\"text\":${ESC}}]}" "message"
    fi

    # Commit the subagent session immediately (detached to avoid timeout)
    (
      _ov_commit "$SUBAGENT_SID" "subagent-stop"
    ) & disown 2>/dev/null || true

    # Clean up state
    rm -f "$SUBAGENT_STATE" 2>/dev/null
    _ov_out "";;


  *) _ov_out "";;
esac