#!/usr/bin/env bash
set -euo pipefail
# ============================================================================
# quality-report.sh — 质量上报自动 hook（兼容层）
# ============================================================================
# 历史: 原为 skill_quality_sdk.py 的 Bash 上报钩子; SDK 已由 in-skill 统一载体
# scripts/cli/cli_entry.py 取代, 本文件保留原 source 契约(注册 EXIT trap,
# 宿主脚本结束时自动上报一条质量记录), 上报逻辑委托统一 CLI, 兼容旧流程调用。
#
# 通道(由统一 CLI 自动判定): 有 AK/SK/Token 凭证 -> APIG 标准通道;
# 无凭证 -> 匿名通道(SKILL_QUALITY_GUEST_ENDPOINT)。
#
# 设计约束: fire-and-forget —— 载体缺失/网络失败/上报失败一律静默,
# 绝不影响宿主脚本的退出码与输出。
#
# 宿主脚本可配置(在 source 之前或之后设置均可, trap 执行时读取):
#   QUALITY_SKILL_NAME   上报的 skill 名称(建议在脚本内尽早设置)
#   QUALITY_STATUS       success|sys_fail|biz_fail|cancel (默认 success)
#   QUALITY_ERROR_MSG    失败时附加的错误信息(可选)
#   QUALITY_REPORT_DIR   .quality_report.json 查找起点(默认保持当前 cwd)
#   SKILL_QUALITY_DISABLE=1  完全禁用上报
# ============================================================================

QUALITY_HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || QUALITY_HOOK_DIR="."
QUALITY_STATUS="${QUALITY_STATUS:-success}"

_quality_do_report() {
  [ "${SKILL_QUALITY_DISABLE:-0}" = "1" ] && return 0
  [ -n "${QUALITY_SKILL_NAME:-}" ] || return 0

  local entry="$QUALITY_HOOK_DIR/cli/cli_entry.py"
  [ -f "$entry" ] || return 0

  local py="python3"
  command -v "$py" >/dev/null 2>&1 || py="python"
  command -v "$py" >/dev/null 2>&1 || return 0

  # .quality_report.json 查找起点(可选, 与 cli_entry.py 的向上查找语义一致)
  if [ -n "${QUALITY_REPORT_DIR:-}" ] && [ -d "$QUALITY_REPORT_DIR" ]; then
    cd "$QUALITY_REPORT_DIR" 2>/dev/null || true
  fi

  # fire-and-forget: 同步调用但 CLI 内置超时, 失败静默; VERBOSE=1 时打印便于排查
  if [ "${SKILL_QUALITY_VERBOSE:-0}" = "1" ]; then
    echo "[quality-report] skill=$QUALITY_SKILL_NAME status=$QUALITY_STATUS" >&2
    "$py" "$entry" --no-auto-upgrade report \
      --skill-name "$QUALITY_SKILL_NAME" \
      --status "$QUALITY_STATUS" \
      ${QUALITY_ERROR_MSG:+--error-msg "$QUALITY_ERROR_MSG"} || true
  else
    "$py" "$entry" --no-auto-upgrade report \
      --skill-name "$QUALITY_SKILL_NAME" \
      --status "$QUALITY_STATUS" \
      ${QUALITY_ERROR_MSG:+--error-msg "$QUALITY_ERROR_MSG"} >/dev/null 2>&1 || true
  fi
}

trap _quality_do_report EXIT