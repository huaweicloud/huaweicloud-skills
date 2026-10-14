#!/usr/bin/env bash
# setup-env.sh — 设置 Git Bash 下所需环境变量（必须 source 执行）
#   source $SKILL_DIR/scripts/setup-env.sh

if [ -n "${BASH_SOURCE[0]:-}" ] && [ "${BASH_SOURCE[0]}" = "$0" ]; then
  echo "⚠️  请用 source 执行: source $0" && return 1 2>/dev/null || exit 1
fi

if [ -n "${MSYSTEM:-}${MSYS:-}" ] && [ "${MSYS_NO_PATHCONV:-0}" != "1" ]; then
  export MSYS_NO_PATHCONV=1
  echo "✅ MSYS_NO_PATHCONV=1"
fi