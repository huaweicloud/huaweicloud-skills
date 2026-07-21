#!/usr/bin/env bash
# utils.sh — Shared utility functions for Huawei Cloud Skill Tester
set -uo pipefail

_CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
[ -z "${PHASE_COUNT:-}" ] && source "$_CONFIG_DIR/config.sh"

# Export config values as env vars for child Python/subprocess use
export HUAWEI_REGION HUAWEI_SDK_VERSION SDK_VERSION_OVERRIDES
export CLI_ERROR_PATTERNS PARAM_ERROR_KEYWORDS AUTH_ERROR_KEYWORDS
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
  local search_dirs=(
    "${SKILL_PATH:-$SKILL_PATH_HCLOUD}"
    "${SKILL_PATH:-$SKILL_PATH_HERMES}"
    "${SKILL_DEV_PATH:-./skills}"
  )
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

# === Phase summary file path ===
phase_file() {
  local skill_dir="$1"
  local phase_num="$2"
  echo "${skill_dir}/phase-${phase_num}-summary.json"
}

# === AK/SK Credential Check ===
# Scans all environment variables starting with HUAWEI / HW / HWC prefixes
# to find access key and secret key pairs.
# Exports the values as HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY for child processes.
# Returns 0 on success, 1 if credentials could not be obtained.

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

ensure_ak_sk() {
  local ak sk

  # 1. Try environment variables — dynamic scan of HUAWEI*/HW*/HWC*
  _scan_env_ak_sk && {
    pass "AK/SK 从环境变量读取成功"
    return 0
  }

  # 2. Try hcloud CLI config
  local hcloud_config="${HCLOUD_CONFIG:-$HOME/.hcloud/config.json}"
  if [ -f "$hcloud_config" ]; then
    local cfg_ak cfg_sk
    cfg_ak=$(python3 -c "
import json, sys
try:
    d=json.load(open(sys.argv[1]))
    for p in d.get('profiles',[]):
        if p.get('mode','')==os.environ.get('HCLOUD_PROFILE_MODE','devcloud'):
            print(p.get('ak',''))
            break
except Exception: pass
" "$hcloud_config" 2>/dev/null)
    cfg_sk=$(python3 -c "
import json, os, sys
try:
    d=json.load(open(sys.argv[1]))
    for p in d.get('profiles',[]):
        if p.get('mode','')==os.environ.get('HCLOUD_PROFILE_MODE','devcloud'):
            print(p.get('sk',''))
            break
except Exception: pass
" "$hcloud_config" 2>/dev/null)
    if [ -n "$cfg_ak" ] && [ -n "$cfg_sk" ]; then
      export HUAWEI_ACCESS_KEY="$cfg_ak"
      export HUAWEI_SECRET_KEY="$cfg_sk"
      pass "AK/SK 从 hcloud 配置读取成功"
      return 0
    fi
  fi

  # 3. Prompt user for input
  warn "未找到 AK/SK 环境变量 (任意以 HUAWEI/HW/HWC 开头的 AK/SK 变量均可)"
  warn "也未找到 hcloud CLI 配置"
  echo ""
  step "请输入华为云 AK (Access Key): "
  if [ -t 0 ]; then
    read -r ak
  else
    fail "非交互模式，无法提示输入 AK/SK。请设置环境变量后重试："
    fail "  export HUAWEI_ACCESS_KEY=your_ak"
    fail "  export HUAWEI_SECRET_KEY=your_sk"
    return 1
  fi

  if [ -z "$ak" ]; then
    fail "AK 不能为空"
    return 1
  fi

  step "请输入华为云 SK (Secret Key): "
  read -r sk

  if [ -z "$sk" ]; then
    fail "SK 不能为空"
    return 1
  fi

  export HUAWEI_ACCESS_KEY="$ak"
  export HUAWEI_SECRET_KEY="$sk"
  pass "AK/SK 已设置"
  return 0
}

# === Cleanup after test ===
# Removes phase JSON files, reports, and handles resource changes.
# Usage: cleanup_after_test <skill_paths...>
cleanup_after_test() {
  local all_skill_paths=("$@")
  local has_issues=false

  header "最终清理 — 还原测试环境"

  # 1. Delete phase-*.json from all tested skills
  for sp in "${all_skill_paths[@]}"; do
    local sn; sn=$(basename "$sp")
    local phase_files; phase_files=$(ls "$sp"/phase-*.json 2>/dev/null)
    if [ -n "$phase_files" ]; then
      step "删除 ${sn} 中的阶段文件..."
      rm -f "$sp"/phase-*.json
      pass "  phase-*.json 已删除"
    fi
  done

  # 2. Delete reports directory
  local reports_dir="${OUTPUT_DIR:-reports}"
  if [ -d "$reports_dir" ]; then
    step "删除测试报告目录..."
    rm -rf "$reports_dir"
    pass "  ${reports_dir}/ 已删除"
  fi

  # 3. Uninstall skill from ~/.hermes/skills/ if installed during test
  for sp in "${all_skill_paths[@]}"; do
    local sn; sn=$(basename "$sp")
    local hermes_target="$SKILL_PATH_HERMES/$sn"
    if [ -d "$hermes_target" ]; then
      step "卸载 ${sn} 从 ~/.hermes/skills/..."
      rm -rf "$hermes_target"
      pass "  ~/.hermes/skills/${sn} 已卸载"
    fi
  done

  # 4. Check Phase 4 results for resource changes
  for sp in "${all_skill_paths[@]}"; do
    local p4_file="$sp/phase-4-summary.json"
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
        echo "$changes_json" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for c in d:
    rid = c.get('resource_id', '') or 'unknown'
    print(f\"    [{c['change_type']}] {c['resource_type']}/{rid} (用例: {c['tc_id']})\")
    if c.get('cleanup_method', {}).get('type'):
        print(f\"      清理方式: {c['cleanup_method']['type']}: {c['cleanup_method'].get('command', '')}\")
"
      fi
    fi
  done

  # 5. Verify skill directory is clean
  for sp in "${all_skill_paths[@]}"; do
    local sn; sn=$(basename "$sp")
    local stray; stray=$(ls "$sp"/phase-*.json 2>/dev/null)
    if [ -n "$stray" ]; then
      warn "${sn} 中仍有残留 phase 文件"
      has_issues=true
    fi
  done

  if ! $has_issues; then
    pass "测试环境已完全还原，无云资源遗留"
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
        if p.get('mode','')==os.environ.get('HCLOUD_PROFILE_MODE','devcloud'):
            print(p.get('ak',''))
            break
except Exception: pass
" "$hcloud_config" 2>/dev/null)
    [ -n "$cfg_ak" ] && return 0
  fi

  return 1
}
