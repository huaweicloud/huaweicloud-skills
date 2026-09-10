#!/usr/bin/env bash
# ============================================================================
# quality-report.sh — skill_quality_sdk.py 的 Bash 自动上报 hook
# ============================================================================
# 被 validate-skill.sh / test-cli-commands.sh / report-skill-created.sh source。
# source 时注册 EXIT trap, 宿主脚本结束时自动上报一条质量记录。
#
# 双模式(由 SDK 自动判定):
#   用户模式: 检测到 AK/SK/Token 凭证 -> 标准通道(APIG, IAM Token 鉴权)
#   游客模式: 无任何凭证 -> 匿名通道 SKILL_QUALITY_GUEST_ENDPOINT
#             (默认 https://skillsop.topxtopx.com/api/quality/guest-report)
#
# 设计约束: fire-and-forget —— SDK 缺失/网络失败/上报失败一律静默,
# 绝对不影响宿主脚本的退出码与输出。
#
# 宿主脚本可配置(在被 source 之前或之后设置均可, trap 执行时读取):
#   QUALITY_SKILL_NAME  上报的 skill 名称(建议在脚本内尽早设置)
#   QUALITY_STATUS      success|sys_fail|biz_fail|cancel (默认 success)
#   QUALITY_ERROR_MSG   失败时附加的错误信息(可选)
#   QUALITY_REPORT_DIR  指定 .quality_report.json 的查找起点(默认保持当前 cwd)
#   QUALITY_SDK         显式指定 skill_quality_sdk.py 路径(可选)
#   SKILL_QUALITY_DISABLE=1  完全禁用上报
# ============================================================================

QUALITY_HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || QUALITY_HOOK_DIR="."
QUALITY_STATUS="${QUALITY_STATUS:-success}"

# 定位 SDK: 显式 QUALITY_SDK > 同目录/向上6层 > HERMES 全局 skills 目录
# 注意: 本函数仅在 EXIT trap 回调中执行, 失败不影响宿主脚本。
_quality_find_sdk() {
  if [ -n "${QUALITY_SDK:-}" ] && [ -f "$QUALITY_SDK" ]; then
    printf '%s' "$QUALITY_SDK"; return 0
  fi
  local d="$QUALITY_HOOK_DIR" parent
  for _ in 1 2 3 4 5 6; do
    if [ -f "$d/skill_quality_sdk.py" ]; then
      printf '%s' "$d/skill_quality_sdk.py"; return 0
    fi
    parent="$(dirname "$d")"
    [ "$parent" = "$d" ] && break
    d="$parent"
  done
  local g
  for g in \
    "${HERMES_HOME:-}/skills/huawei-cloud-skill-creator/scripts/skill_quality_sdk.py" \
    "$HOME/AppData/Local/hermes/skills/huawei-cloud-skill-creator/scripts/skill_quality_sdk.py" \
    "$HOME/.hermes/skills/huawei-cloud-skill-creator/scripts/skill_quality_sdk.py"; do
    if [ -n "$g" ] && [ -f "$g" ]; then
      printf '%s' "$g"; return 0
    fi
  done
  return 1
}

_quality_do_report() {
  [ "${SKILL_QUALITY_DISABLE:-0}" = "1" ] && return 0
  [ -n "${QUALITY_SKILL_NAME:-}" ] || return 0

  local sdk="" py="python3"
  sdk="$(_quality_find_sdk)" || return 0
  [ -n "$sdk" ] || return 0

  # Windows/MSYS (git-bash): 转原生路径, 否则 python.exe 打不开 /c/... 路径
  if command -v cygpath >/dev/null 2>&1; then
    sdk="$(cygpath -w "$sdk" 2>/dev/null || printf '%s' "$sdk")"
  fi

  command -v python3 >/dev/null 2>&1 || py="python"
  command -v "$py" >/dev/null 2>&1 || return 0

  # .quality_report.json 查找起点(可选)
  if [ -n "${QUALITY_REPORT_DIR:-}" ] && [ -d "$QUALITY_REPORT_DIR" ]; then
    cd "$QUALITY_REPORT_DIR" 2>/dev/null || true
  fi

  # fire-and-forget: 同步调用但 SDK 内置 3s 超时, 失败静默; VERBOSE=1 时打印 trace_id 便于排查
  if [ "${SKILL_QUALITY_VERBOSE:-0}" = "1" ]; then
    echo "[quality-report] skill=$QUALITY_SKILL_NAME status=${QUALITY_STATUS:-success}" >&2
    "$py" "$sdk" report \
      --skill-name "$QUALITY_SKILL_NAME" \
      --status "${QUALITY_STATUS:-success}" \
      ${QUALITY_ERROR_MSG:+--error-msg "$QUALITY_ERROR_MSG"} || true
  else
    "$py" "$sdk" report \
      --skill-name "$QUALITY_SKILL_NAME" \
      --status "${QUALITY_STATUS:-success}" \
      ${QUALITY_ERROR_MSG:+--error-msg "$QUALITY_ERROR_MSG"} >/dev/null 2>&1 || true
  fi
}

trap _quality_do_report EXIT