#!/bin/bash
# precheck.sh — Bash 版本的统一环境检查脚本
# 用法: skill action=exec, command ["bash", "skill://scripts/precheck.sh"]
# 退出码: 0=全部通过, 1=有检查未通过

# 严格错误处理：
# -e : 任何命令失败立即退出
# -u : 使用未定义变量报错
# -o pipefail : 管道命令中任何一段失败，整体视为失败
# 已失败调用通过 `|| true` 显式兜底（不视为错误）
set -euo pipefail

# --- 配置 ---
HLOUD_CMD="hcloud"
REGION="${HUAWEI_CLOUD_REGION:-}"
OUTPUT_MODE="${CHECK_OUTPUT_MODE:-summary}"  # summary | detail

# --- 工具函数 ---
info()  { echo "[INFO]  $*" >&2; }
pass()  { echo "[PASS]  $*" >&2; }
fail()  { echo "[FAIL]  $*" >&2; }
ok()    { [[ "$OUTPUT_MODE" == "detail" ]] && echo "[OK]    $*" >&2 || true; }
err()   { echo "[ERR]   $*" >&2; }

# --- WSL bash 启动器陷阱检测 ---
# 在 Windows 上 Git Bash / WSL 启动器（位于 WindowsApps）会被翻译，precheck 表现异常；
# 仅打印警告，不阻塞流程。
detect_wsl_bash_stub() {
  local bash_path
  bash_path=$(command -v bash 2>/dev/null) || return 0
  if command -v cygpath &>/dev/null; then
    local win_path
    win_path=$(cygpath -w "$bash_path" 2>/dev/null) || return 0
    if echo "$win_path" | grep -qi "WindowsApps"; then
      info "${YELLOW}⚠️  检测到 WSL bash 启动器（位于 $win_path）；precheck 在此 shell 中可能行为异常，建议显式调用真正的 bash 路径（如 C:/Program Files/Git/bin/bash.exe 或 WSL 里的 bash）${RESET}"
    fi
  fi
}
if [[ -t 1 ]] && command -v tput &>/dev/null; then
  RED=$(tput setaf 1 2>/dev/null)
  GREEN=$(tput setaf 2 2>/dev/null)
  YELLOW=$(tput setaf 3 2>/dev/null)
  RESET=$(tput sgr0 2>/dev/null)
fi
RED=${RED:-""} GREEN=${GREEN:-""} YELLOW=${YELLOW:-""} RESET=${RESET:-""}

# --- 全局状态 ---
FAILED=0
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_SKIPPED=0

# --- 单项检查函数 ---
check_command() {
  local name="$1"
  local cmd="$2"
  local expected_pattern="${3:-}"

  if ! command -v "$cmd" &>/dev/null; then
    fail "${RED}hcloud 未安装或不在 PATH 中${RESET}"
    FAILED=1; ((CHECKS_FAILED+=1)); return 1
  fi

  ok "${GREEN}hcloud 命令存在${RESET}"
  ((CHECKS_PASSED+=1))
  return 0
}

check_hcloud_version() {
  local name="$1"

  # 尝试获取版本，支持首次运行的交互式提示
  local version_output
  version_output=$("$HLOUD_CMD" version 2>&1) || true

  if echo "$version_output" | grep -qiE "(error|exception|command not found|no permission)"; then
    fail "${RED}hcloud version 执行失败: $version_output${RESET}"
    FAILED=1; ((CHECKS_FAILED+=1)); return 1
  fi

  local version_line
  version_line=$(echo "$version_output" | grep -iE "版本|version|koocli" | head -1)
  if [[ -n "$version_line" ]]; then
    ok "${GREEN}$version_line${RESET}"
  else
    ok "${GREEN}hcloud 可正常执行${RESET}"
  fi
  ((CHECKS_PASSED+=1))
  return 0
}

check_hcloud_configure() {
  local name="$1"

  local cfg_output
  cfg_output=$("$HLOUD_CMD" configure list 2>&1) || true

  if echo "$cfg_output" | grep -qiE "(error|exception|not configure|未配置|not found)"; then
    fail "${RED}凭证未配置或配置不可用: $(echo $cfg_output | head -c 120)${RESET}"
    FAILED=1; ((CHECKS_FAILED+=1)); return 1
  fi

  ok "${GREEN}凭证已配置${RESET}"
  ((CHECKS_PASSED+=1))
  return 0
}

get_configured_region() {
  # 用 --cli-query="region" 直接拿字符串（KooCLI JMESPath 过滤）。
  # KooCLI 版本过旧（如 7.2.12.1）会在 stdout 输出 ANSI 颜色码包住的
  # "可执行 hcloud update`更新KooCLI至最新版本X.Y.Z`" 升级提示；如果直接用 `tr -d`
  # 删除 ANSI 颜色码之外的字符，整段升级提示会被当 region 值返回，导致
  # `hcloud --cli-region=...` 命令报「参数 update\`...\`` 的格式错误」。
  #  先用 `sed` 删 ANSI 颜色码（`\x1b\[...m`），再用 `grep -oE` 精确匹配
  # `cn-XXX-N` 格式（如 `cn-north-7`），最后 `head -1` 取首个匹配。
  "$HLOUD_CMD" configure show --cli-query="region" 2>/dev/null | \
    sed 's/\x1b\[[0-9;]*m//g' | \
    grep -oE 'cn-[a-z]+-[0-9]+' | \
    head -1 || true
}

check_region() {
  local name="$1"
  local region=$(get_configured_region)
  if [[ -z "$region" ]]; then
    fail "${RED}未检测到 region，请通过 'hcloud configure init' 配置或设置 HUAWEI_CLOUD_REGION 环境变量${RESET}"
    FAILED=1; ((CHECKS_FAILED+=1)); return 1
  fi

  ok "${GREEN}region=$region${RESET}"
  ((CHECKS_PASSED+=1))
  return 0
}

check_optverse_connectivity() {
  local name="$1"
  local region=$(get_configured_region)

  if [[ -z "$region" ]]; then
    ((CHECKS_SKIPPED+=1))
    info "跳过连通性检查（region 未确定）"
    return 0
  fi

  local conn_output
  conn_output=$("$HLOUD_CMD" OptVerse ListBuckets --cli-region=$region --cli-output=json 2>&1) || true
  if echo "$conn_output" | grep -qiE "(error|exception|unauthorized|forbidden|认证失败)"; then
    fail "${RED}OptVerse 连通性检查失败: $(echo $conn_output | head -c 200)${RESET}"
    FAILED=1; ((CHECKS_FAILED+=1)); return 1
  fi

  ok "${GREEN}OptVerse API 连通性正常${RESET}"
  ((CHECKS_PASSED+=1))
  return 0
}

# --- 汇总输出 ---
print_summary() {
  echo "" >&2
  if [[ "$FAILED" == "0" ]]; then
    echo "${GREEN}✅ 环境检查通过 ($CHECKS_PASSED/$((CHECKS_PASSED + CHECKS_SKIPPED)) 项通过)${RESET}" >&2
  else
    echo "${YELLOW}⚠️  环境检查未全部通过 ($CHECKS_FAILED 项失败, $CHECKS_PASSED 项通过)${RESET}" >&2
    echo "${YELLOW}  请修复上述 [FAIL] 项后重新执行${RESET}" >&2
  fi
  echo "" >&2
}

# --- 主流程 ---
main() {
  # 如果有 region，先从配置中读取
  if [[ -z "$REGION" ]]; then
    REGION=$(hcloud configure show 2>/dev/null | grep -i region | awk '{print $NF}' | head -1) || REGION=""
  fi

  echo "🔍 开始环境检查..." >&2
  echo "   region=$REGION" >&2
  echo "" >&2

  detect_wsl_bash_stub

  # 自动 extend PATH（Git Bash 不继承 PowerShell PATH，找不到 hcloud）
  if ! command -v "$HLOUD_CMD" &>/dev/null; then
    _user_home="${HOME:-/c/Users/$(whoami)}"
    for _candidate in \
      "$_user_home/.huawei/bin" \
      "/c/Users/$(whoami)/.huawei/bin" \
      "/c/Program Files/KooCLI/bin" \
      "/c/Program Files/Huawei/hcloud/bin"; do
      if [[ -x "$_candidate/${HLOUD_CMD}.exe" ]]; then
        export PATH="$_candidate:$PATH"
        info "${YELLOW}自动 extend PATH: $_candidate (Git Bash 不继承 PowerShell PATH)${RESET}"
        break
      fi
    done
    unset _user_home _candidate
  fi

  check_command "hcloud 命令" "hcloud"
  check_hcloud_version "hcloud version"
  check_hcloud_configure "hcloud configure list"
  check_region "region 配置"
  check_optverse_connectivity "OptVerse 连通性"

  print_summary

  exit $FAILED
}

main "$@"