#!/usr/bin/env bash
# utils.sh — Shared utility functions for Huawei Cloud Skill Tester
set -uo pipefail

_CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
[ -z "${PHASE_COUNT:-}" ] && source "$_CONFIG_DIR/config.sh"

# Export config values as env vars for child Python/subprocess use
export HUAWEI_REGION HUAWEI_SDK_VERSION SDK_VERSION_OVERRIDES
export CLI_ERROR_PATTERNS PARAM_ERROR_KEYWORDS AUTH_ERROR_KEYWORDS
export SKILL_INSTALL_DIR SKILL_PATH_HERMES SKILL_PATH_HCLOUD SKILL_INSTALL_CMD
export HCLOUD_PROFILE_MODE SKILL_DEV_PATH

# Force UTF-8 mode for Python (fixes GBK encoding issues on Windows)
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1
export TIMEOUT_CLI TIMEOUT_SDK TIMEOUT_RESEARCH
export OUTPUT_TRUNC_CLI OUTPUT_TRUNC_SDK OUTPUT_TRUNC_ERR

# === Colors ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# === Logging ===
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
pass()  { echo -e "${GREEN}[PASS]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }
step()  { echo -e "${BLUE}[STEP]${NC}  $*"; }
header(){ echo -e "\n${BLUE}══════════════════════════════════════════${NC}"; echo -e "${BLUE}  $*${NC}"; echo -e "${BLUE}══════════════════════════════════════════${NC}"; }

# === Timestamp ===
timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# === JSON helpers ===
write_json() {
  local file="$1"
  local content="$2"
  mkdir -p "$(dirname "$file")"
  echo "$content" | python3 -m json.tool > "$file" 2>/dev/null || echo "$content" > "$file"
  info "已写入: $file"
}

read_json_field() {
  local file="$1"
  local field="$2"
  python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
for key in sys.argv[2].replace('][', '][').strip('[]').split(']['):
    key = key.strip(\"'\" + '\"')
    d = d[int(key)] if isinstance(d, list) else d[key]
print(d)
" "$file" "$field" 2>/dev/null || echo ""
}

read_json_verdict() {
  local file="$1"
  read_json_field "$file" "['summary']['verdict']"
}

# === Directory helpers ===
find_skill_path() {
  local skill_name="$1"
  # If it's already a full path, check directly
  if [ -d "$skill_name" ] && [ -f "$skill_name/SKILL.md" ]; then
    echo "$skill_name"
    return 0
  fi
  # Search order:
  #   1. If SKILL_PATH is set, only search there (user explicit override).
  #   2. Otherwise, prefer SKILL_DEV_PATH (workspace source) FIRST, then fall
  #      back to the install target. This avoids the trap where a stale
  #      installed copy shadows the workspace source and breaks phase-0
  #      reinstall (uninstall deletes the "source" before reinstall reads it).
  local search_dirs=()
  if [ -n "${SKILL_PATH:-}" ]; then
    search_dirs=("$SKILL_PATH")
  else
    search_dirs=(
      "${SKILL_DEV_PATH:-./skills}"
      "${SKILL_INSTALL_DIR}/huawei-cloud"
      "${SKILL_INSTALL_DIR}"
    )
  fi
  for dir in "${search_dirs[@]}"; do
    local candidate="$dir/$skill_name"
    if [ -d "$candidate" ] && [ -f "$candidate/SKILL.md" ]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

count_skills() {
  local skills_list="$1"
  [ -z "$skills_list" ] && echo 0 && return
  echo "$skills_list" | tr ',' '\n' | wc -l | tr -d ' '
}

ensure_jq() {
  if ! command -v jq &>/dev/null; then
    fail "jq 未安装。请先安装: apt install jq 或 brew install jq"
    exit 1
  fi
}

# === Test artifact paths ===
# All test artifacts go to a sibling directory of the skill, named
# "<skill-name>-test-files". This keeps the skill source dir clean.
# Layout:
#   <skill_parent>/<skill_name>-test-files/
#   ├── phases/
#   │   ├── phase-0-summary.json
#   │   ├── phase-1-summary.json
#   │   └── ...
#   └── reports/
#       └── report-<test_id>/
#           ├── test-report.json
#           └── test-report.md

# Compute the test-files root for a given skill directory.
# Args: <skill_dir>
# Echoes: absolute path to <skill_dir>/../<skill_name>-test-files
test_files_dir() {
  local skill_dir="$1"
  local skill_name; skill_name=$(basename "$skill_dir")
  local parent_dir; parent_dir=$(dirname "$skill_dir")
  echo "$parent_dir/${skill_name}-test-files"
}

# Compute the phases subdir.
# Args: <skill_dir>
# Echoes: <test_files_dir>/phases
phases_dir() {
  echo "$(test_files_dir "$1")/phases"
}

# Compute the reports subdir.
# Args: <skill_dir>
# Echoes: <test_files_dir>/reports
reports_dir() {
  echo "$(test_files_dir "$1")/reports"
}

# === Phase summary file path ===
# Args: <skill_dir> <phase_num>
# Echoes: <test_files_dir>/phases/phase-<phase_num>-summary.json
phase_file() {
  local skill_dir="$1"
  local phase_num="$2"
  echo "$(phases_dir "$skill_dir")/phase-${phase_num}-summary.json"
}

# Ensure the test-files directory tree exists (creates phases/ and reports/).
# Args: <skill_dir>
# Echoes: <test_files_dir>
ensure_test_files_dir() {
  local tfd; tfd=$(test_files_dir "$1")
  mkdir -p "$tfd/phases" "$tfd/reports"
  echo "$tfd"
}

# === Sibling skill discovery ===
# Used by Phase 5/6 to auto-discover other huawei-cloud-* skills in the same
# parent directory for orchestration / multi-skill E2E testing.
#
# Default behavior: scan siblings. (用户要求"从被测试的 skill 的所在目录
# 寻找其他 skill 做编排组合测试"。)
#
# Opt-out:
#   - --no-siblings flag (handled by caller translating to WITHOUT_SIBLINGS=1)
#   - WITHOUT_SIBLINGS=1 env var
#   - SIBLING_LIMIT=0 env var (also disables scan)
#
# Configurable limits:
#   SIBLING_LIMIT=N  — max siblings to include (default 5; 0 = disable)
#
# Exclusion rules (always applied):
#   - The target skill itself
#   - Directories whose name starts with "huawei-cloud-" but are test artifacts:
#     *-test-files           (test report directories)
#   - Test/meta skills that should not participate in orchestration:
#     huawei-cloud-skill-tester, huawei-cloud-skill-creator, huawei-cloud-new-tester
#   - Any sibling missing SKILL.md
#
# Args: <target_skill_dir> [<existing_skill_paths>...]
# Echoes: newline-separated list of discovered sibling SKILL PATHS (excluding target).
#         If scan is disabled or no eligible siblings, echoes nothing.
discover_siblings() {
  local target_dir="$1"; shift

  # Opt-out checks
  if [ "${WITHOUT_SIBLINGS:-0}" = "1" ]; then
    return 0
  fi
  local limit="${SIBLING_LIMIT:-5}"
  if [ "$limit" = "0" ]; then
    return 0
  fi

  local target_name parent_dir
  target_name=$(basename "$target_dir")
  parent_dir=$(dirname "$target_dir")

  # Existing skill paths to dedupe against (the caller already collected some)
  local existing_set=" $target_dir "
  for p in "$@"; do
    existing_set+="$p "
  done

  local found=()
  for sibling in "$parent_dir"/huawei-cloud-*; do
    [ -d "$sibling" ] || continue

    local sname
    sname=$(basename "$sibling")

    # Exclude self
    [ "$sname" = "$target_name" ] && continue

    # Exclude test artifacts and meta skills
    case "$sname" in
      *-test-files|huawei-cloud-skill-tester|huawei-cloud-skill-creator|huawei-cloud-new-tester)
        continue
        ;;
    esac

    # Must have SKILL.md
    [ -f "$sibling/SKILL.md" ] || continue

    # Dedup: skip if already in the caller's list
    case " $existing_set " in
      *" $sibling "*|*" ${sibling%/} "*|*" $parent_dir/$sname "*)
        continue
        ;;
    esac

    found+=("$sibling")
    if [ "${#found[@]}" -ge "$limit" ]; then
      break
    fi
  done

  for s in "${found[@]}"; do
    echo "$s"
  done
}

# === AK/SK Credential Check ===
# Two-tier resolution. NO interactive prompt is ever used (not even in TTY):
#   1. Environment variables (HUAWEI*/HW*/HWC* prefixed AK/SK pairs)
#   2. hcloud CLI config (~/.hcloud/config.json profile)
# If neither source yields credentials, the framework prints the env-var
# setup template to stderr and exits 77. The Agent's job is to OUTPUT that
# template to the user — NEVER read, type, ask for, or echo back the literal
# AK/SK value in chat. The user fills in the values out-of-band (in their
# shell profile / .zshrc / PowerShell $PROFILE) and re-runs the failing phase.
#
# Exit codes (used by phase-4 / phase-6 / run-test-pipeline / calling agents):
#   0  — credentials obtained (env or hcloud config)
#   77 — credentials required; env-var template has been emitted to stderr
#   1  — other error (bad input, etc.)
#
# Agent protocol (when running non-interactively, e.g. via an AI agent):
#   - On exit 77, the script has emitted the HUAWEI_CREDENTIALS_REQUIRED
#     sentinel + the env-var template to stderr. The agent should:
#     1) OUTPUT the template to the user (verbatim) — do NOT ask the user to
#        paste AK/SK into chat, do NOT read credential files
#     2) Tell the user to fill in their AK/SK in their shell and re-run
#     3) Re-run with HUAWEI_ACCESS_KEY and HUAWEI_SECRET_KEY set
#   - The agent MUST NOT silently skip Phase 4/6 — that defeats the test.
#   - If the user declines to provide credentials, the agent may abort the
#     pipeline (preferred) or skip live phases at the agent's discretion,
#     but should NOT mark the run as "pass" without live API verification.

# Sentinel emitted to stderr when credentials are required and cannot be obtained
CRED_REQUEST_SENTINEL="__HUAWEI_SKILL_TESTER_CRED_REQUEST_v1__"

# Helper: scan env for HUAWEI*/HW*/HWC* prefixed AK/SK pairs
_scan_env_ak_sk() {
  local ak_var="" sk_var="" name value upper
  while IFS='=' read -r name value; do
    upper="${name^^}"
    [[ $upper != HUAWEI* && $upper != HW* && $upper != HWC* ]] && continue
    if [[ $upper == *_ACCESS_KEY || $upper == *_AK || $upper == _ACCESS_KEY || $upper == _AK ]]; then
      [ -n "$value" ] && ak_var="$value"
    fi
    if [[ $upper == *_SECRET_KEY || $upper == *_SK || $upper == _SECRET_KEY || $upper == _SK ]]; then
      [ -n "$value" ] && sk_var="$value"
    fi
  done < <(env)
  [ -n "$ak_var" ] && export HUAWEI_ACCESS_KEY="$ak_var"
  [ -n "$sk_var" ] && export HUAWEI_SECRET_KEY="$sk_var"
  [ -n "$ak_var" ] && [ -n "$sk_var" ]
}

# Read AK/SK from hcloud CLI config (returns 0 if both found, exports them)
# 兼容实际 hcloud 配置格式: mode=AKSK, 字段 accessKeyId/secretAccessKey
# (也兼容旧格式 mode=devcloud + ak/sk)
_read_hcloud_config_ak_sk() {
  local hcloud_config="${HCLOUD_CONFIG:-$HOME/.hcloud/config.json}"
  [ -f "$hcloud_config" ] || return 1
  local cfg_ak cfg_sk
  cfg_ak=$(python3 -c "
import json, os, sys
try:
    d=json.load(open(sys.argv[1]))
    for p in d.get('profiles',[]):
        if p.get('mode','') in ('AKSK','devcloud','token'):
            v=p.get('accessKeyId') or p.get('ak') or ''
            if v:
                print(v)
                break
except Exception: pass
" "$hcloud_config" 2>/dev/null)
  cfg_sk=$(python3 -c "
import json, os, sys
try:
    d=json.load(open(sys.argv[1]))
    for p in d.get('profiles',[]):
        if p.get('mode','') in ('AKSK','devcloud','token'):
            v=p.get('secretAccessKey') or p.get('sk') or ''
            if v:
                print(v)
                break
except Exception: pass
" "$hcloud_config" 2>/dev/null)
  if [ -n "$cfg_ak" ] && [ -n "$cfg_sk" ]; then
    export HUAWEI_ACCESS_KEY="$cfg_ak"
    export HUAWEI_SECRET_KEY="$cfg_sk"
    return 0
  fi
  return 1
}

# Output the env-var setup template to stderr. Called when no credentials
# were found from any source. The function NEVER reads or echoes any literal
# AK/SK value. The user fills in <your-access-key-id> and <your-secret-access-key>
# out-of-band in their shell profile (Linux/macOS) or PowerShell $PROFILE (Windows),
# then re-runs the failing phase.
#
# This replaces the legacy interactive prompt (removed for security and
# consistency with the "no in-session secret entry" rule used elsewhere in
# the Huawei Cloud skill ecosystem). The function name `_emit_cred_request_sentinel`
# is preserved for backward compatibility with callers.
_emit_cred_request_sentinel() {
  {
    echo "$CRED_REQUEST_SENTINEL"
    echo "HUAWEI_CREDENTIALS_REQUIRED"
    echo ""
    echo "Phase 4 / Phase 6 requires live Huawei Cloud API access."
    echo "No HUAWEI*/HW*/HWC* prefixed AK/SK env vars were detected, and no"
    echo "active hcloud CLI profile was found."
    echo ""
    echo "Huawei Cloud Skill Tester NEVER accepts AK/SK via stdin, chat, or any"
    echo "interactive prompt. To unblock live tests, the user must set env vars"
    echo "out-of-band in their shell profile and re-run."
    echo ""
    echo "===== copy from here (do NOT echo or paste the values into chat) ====="
    echo ""
    echo "  # Linux / macOS"
    echo "  export HUAWEI_ACCESS_KEY=\"<your-access-key-id>\""
    echo "  export HUAWEI_SECRET_KEY=\"<your-secret-access-key>\""
    echo "  export HUAWEI_REGION=\"cn-north-4\""
    echo ""
    echo "  # Windows PowerShell"
    echo "  \$env:HUAWEI_ACCESS_KEY = \"<your-access-key-id>\""
    echo "  \$env:HUAWEI_SECRET_KEY = \"<your-secret-access-key>\""
    echo "  \$env:HUAWEI_REGION     = \"cn-north-4\""
    echo ""
    echo "===== copy ends ====="
    echo ""
    echo "  # any HUAWEI*/HW*/HWC* prefixed *_AK / *_SK / *_ACCESS_KEY / *_SECRET_KEY"
    echo "  # env pair is also accepted; HUAWEI_REGION can be any valid Huawei region."
    echo ""
    echo "Alternatively, set up an hcloud CLI profile (interactive, OUTSIDE this session):"
    echo "  hcloud configure    # prompts for AK/SK in the user's terminal only"
    echo ""
    echo "Then re-run the failing phase:"
    echo "  bash run-test-pipeline.sh --skills <name> --phase 4"
    echo ""
    echo "This script is now exiting with code 77 as a signal to the calling agent."
    echo "The agent should OUTPUT the template above and tell the user to re-run;"
    echo "it MUST NOT ask the user to type or paste AK/SK in chat."
  } >&2
}

# Backward-compatible alias. New code should call `_emit_cred_request_sentinel`
# directly. The legacy `_prompt_ak_sk_interactive` has been removed because
# interactive prompts are no longer part of the credential resolution path.
_output_env_var_template() {
  _emit_cred_request_sentinel
}

ensure_ak_sk() {
  # === 1. Env vars ===
  if _scan_env_ak_sk; then
    pass "AK/SK 从环境变量读取成功"
    return 0
  fi

  # === 2. hcloud config ===
  if _read_hcloud_config_ak_sk; then
    pass "AK/SK 从 hcloud 配置读取成功"
    return 0
  fi

  # === 3. No credentials — emit env-var template + exit 77 ===
  # The agent (or human caller) MUST:
  #   - Output the template below to the user (verbatim)
  #   - NEVER ask the user to type or paste AK/SK in chat
  #   - Wait for the user to set env vars out-of-band, then re-run
  _emit_cred_request_sentinel
  return 77
}

# === Output sanitization ===
# Redact AK/SK-like patterns from strings before emitting to reports.
# Reads JSON from stdin, redacts credential fields in printed output.
sanitize_and_print_changes() {
  python3 -c "
import json, sys, re

def redact_creds(s):
    pats = [
        (r'--cli-(secret|access)-key=\S+', r'--cli-\1-key=***REDACTED***'),
        (r'(HUAWEI_|HW_|HWC_)?(SECRET_KEY|ACCESS_KEY)=\S+', r'\1\2=***REDACTED***'),
    ]
    for pat, repl in pats:
        s = re.sub(pat, repl, s, flags=re.IGNORECASE)
    return s

d = json.load(sys.stdin)
for c in d:
    rid = c.get('resource_id', '') or 'unknown'
    print(f\"    [{c['change_type']}] {c['resource_type']}/{rid} (用例: {c['tc_id']})\")
    cm = c.get('cleanup_method', {})
    if cm.get('type'):
        cmd = redact_creds(cm.get('command', ''))
        print(f\"      清理方式: {cm['type']}: {cmd}\")
"
}

# === Cleanup after test ===
# What it does:
#   - KEEPS the test artifacts (phase JSONs in <skill>-test-files/phases/,
#     reports in <skill>-test-files/reports/). The user wants history.
#   - UNINSTALLS the test-installed copy of each skill from $SKILL_INSTALL_DIR
#     so the next run doesn't see a stale install.
#   - CHECKS Phase 4 results for cloud resource changes (real-API writes) and
#     prints cleanup instructions if any resources were created/modified.
#
# Usage: cleanup_after_test <skill_paths...>
cleanup_after_test() {
  local all_skill_paths=("$@")
  local has_issues=false

  header "最终清理 — 仅卸 skill 副本，不删测试产物"

  # 1. Print what we kept (so the user knows where the artifacts live)
  for sp in "${all_skill_paths[@]}"; do
    local tfd; tfd=$(test_files_dir "$sp")
    if [ -d "$tfd" ]; then
      info "  📁 测试产物保留在: $tfd"
    fi
  done

  # 2. Uninstall skill from $SKILL_INSTALL_DIR if installed during test
  for sp in "${all_skill_paths[@]}"; do
    local sn; sn=$(basename "$sp")
    local install_target="$SKILL_INSTALL_DIR/$sn"
    # 同路径防护: 技能源目录即安装目录时(测试前已安装, 非 Phase 0 复制的副本),
    # 跳过卸载, 避免 rm -rf 删除技能本身。
    local rp_sp rp_it
    rp_sp=$(realpath "$sp" 2>/dev/null || echo "$sp")
    rp_it=$(realpath "$install_target" 2>/dev/null || echo "$install_target")
    if [ "$rp_sp" = "$rp_it" ]; then
      info "  💡 ${sn} 源目录即安装目录，跳过卸载（避免删除技能本身）"
    elif [ -d "$install_target" ]; then
      step "卸载 ${sn} 从 ${SKILL_INSTALL_DIR}..."
      rm -rf "$install_target"
      pass "  ${SKILL_INSTALL_DIR}/${sn} 已卸载"
    fi
  done

  # 3. Check Phase 4 results for resource changes
  #    (Phase 4 JSON lives in the test-files dir now, not the skill dir)
  for sp in "${all_skill_paths[@]}"; do
    local p4_file
    p4_file="$(phase_file "$sp" 4)"
    if [ -f "$p4_file" ]; then
      local changes_json
      changes_json=$(python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    p4 = json.load(f)
results = p4.get('result', {}).get('execution_results', [])
changes = []
for r in results:
    for rc in r.get('resource_changes', []):
        changes.append({
            'tc_id': r.get('tc_id', ''),
            'resource_type': rc.get('resource_type', ''),
            'resource_id': rc.get('resource_id', ''),
            'change_type': rc.get('change_type', ''),
            'cleanup_method': rc.get('cleanup_method', {}),
        })
print(json.dumps(changes, indent=2))
" "$p4_file" 2>/dev/null) || changes_json="[]"

      local created_count; created_count=$(echo "$changes_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for c in d if c.get('change_type')=='created'))" 2>/dev/null || echo 0)
      local modified_count; modified_count=$(echo "$changes_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for c in d if c.get('change_type')=='modified'))" 2>/dev/null || echo 0)
      local deleted_count; deleted_count=$(echo "$changes_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for c in d if c.get('change_type')=='deleted'))" 2>/dev/null || echo 0)

      if [ "$created_count" -gt 0 ] || [ "$modified_count" -gt 0 ] || [ "$deleted_count" -gt 0 ]; then
        has_issues=true
        warn "检测到云资源变更:"
        [ "$created_count" -gt 0 ] && warn "  新增 ${created_count} 个资源 — 请登录华为云控制台确认并删除"
        [ "$modified_count" -gt 0 ] && warn "  修改 ${modified_count} 个资源 — 请登录华为云控制台确认状态"
        [ "$deleted_count" -gt 0 ] && warn "  删除 ${deleted_count} 个资源 — 请确认删除是否预期"
        echo "$changes_json" | sanitize_and_print_changes
      fi
    fi
  done

  if ! $has_issues; then
    pass "测试产物已保留在 <skill>-test-files/ 下，skill 副本已卸载"
  fi
  echo ""
}

# Check if AK/SK are available (without prompting). Returns 0 if set, 1 if not.
has_ak_sk() {
  _scan_env_ak_sk && return 0

  # Also check hcloud config
  local hcloud_config="${HCLOUD_CONFIG:-$HOME/.hcloud/config.json}"
  if [ -f "$hcloud_config" ]; then
    local cfg_ak
    cfg_ak=$(python3 -c "
import json, os, sys
try:
    d=json.load(open(sys.argv[1]))
    for p in d.get('profiles',[]):
        if p.get('mode','') in ('AKSK','devcloud','token'):
            v=p.get('accessKeyId') or p.get('ak') or ''
            if v:
                print(v)
                break
except Exception: pass
" "$hcloud_config" 2>/dev/null)
    [ -n "$cfg_ak" ] && return 0
  fi

  return 1
}
