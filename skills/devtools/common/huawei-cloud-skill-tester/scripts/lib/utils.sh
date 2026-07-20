#!/usr/bin/env bash
# utils.sh — Shared utility functions for Huawei Cloud Skill Tester
set -uo pipefail

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
  local search_dirs=(
    "${SKILL_PATH:-$HOME/.hermes/skills/huawei-cloud}"
    "${SKILL_PATH:-$HOME/.hermes/skills}"
    "./skills/huawei-cloud"
    "./skills"
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
# Ensures HUAWEI_ACCESS_KEY and HUAWEI_SECRET_KEY are set.
# Reads from environment variables first; if missing, prompts user for input.
# Exports the values so child processes (python3, bash -c) inherit them.
# Returns 0 on success, 1 if credentials could not be obtained.
ensure_ak_sk() {
  local ak sk

  # 1. Try environment variables (multiple naming conventions)
  ak="${HUAWEI_ACCESS_KEY:-${HWC_AK:-}}"
  sk="${HUAWEI_SECRET_KEY:-${HWC_SK:-}}"

  if [ -n "$ak" ] && [ -n "$sk" ]; then
    export HUAWEI_ACCESS_KEY="$ak"
    export HUAWEI_SECRET_KEY="$sk"
    pass "AK/SK 从环境变量读取成功"
    return 0
  fi

  # 2. Try ~/.hcloud/config.json (hcloud CLI config)
  local hcloud_config="$HOME/.hcloud/config.json"
  if [ -f "$hcloud_config" ]; then
    local cfg_ak cfg_sk
    cfg_ak=$(python3 -c "
import json, sys
try:
    d=json.load(open(sys.argv[1]))
    for p in d.get('profiles',[]):
        if p.get('mode','')=='devcloud':
            print(p.get('ak',''))
            break
except Exception: pass
" "$hcloud_config" 2>/dev/null)
    cfg_sk=$(python3 -c "
import json, sys
try:
    d=json.load(open(sys.argv[1]))
    for p in d.get('profiles',[]):
        if p.get('mode','')=='devcloud':
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
  warn "未找到 AK/SK 环境变量 (HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY 或 HWC_AK / HWC_SK)"
  warn "也未找到 hcloud CLI 配置"
  echo ""
  step "请输入华为云 AK (Access Key): "
  if [ -t 0 ]; then
    read -r ak
  else
    # Non-interactive mode — cannot prompt
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

# Check if AK/SK are available (without prompting). Returns 0 if set, 1 if not.
has_ak_sk() {
  local ak="${HUAWEI_ACCESS_KEY:-${HWC_AK:-}}"
  local sk="${HUAWEI_SECRET_KEY:-${HWC_SK:-}}"
  [ -n "$ak" ] && [ -n "$sk" ] && return 0

  # Also check hcloud config
  local hcloud_config="$HOME/.hcloud/config.json"
  if [ -f "$hcloud_config" ]; then
    local cfg_ak
    cfg_ak=$(python3 -c "
import json, sys
try:
    d=json.load(open(sys.argv[1]))
    for p in d.get('profiles',[]):
        if p.get('mode','')=='devcloud':
            print(p.get('ak',''))
            break
except Exception: pass
" "$hcloud_config" 2>/dev/null)
    [ -n "$cfg_ak" ] && return 0
  fi

  return 1
}
