#!/usr/bin/env bash
# ============================================================================
# report-skill-created.sh — 通用 skill 上报 SDK 集成入口
#
# 在创建流程完成（Phase 6 全部通过、skill 创建成功）后调用，通过
# huawei-cloud-skill-reporter 的独立上报 CLI (report.mjs) 上报一条 creator
# 使用记录（用于统计 creator 使用次数）。
#
# 上报逻辑委托给 huawei-cloud-skill-reporter/report.mjs（IP 获取、上报地址、
# payload 构造、fire-and-forget 的单一来源），本脚本不重复实现 curl。
#
# 用法:
#   bash scripts/report-skill-created.sh <created-skill-name> [result]
#     <created-skill-name>  本次创建的 skill 名称（必填，huawei-cloud-* 前缀）
#     [result]              执行结果 / 创建的 skill 路径（可选）
#
# 环境变量:
#   HUAWEI_CLOUD_SKILL_REPORT_URL  覆盖上报地址（透传给 report.mjs）
#
# 退出码:
#   0 = 成功（上报失败或 SDK 缺失时也返回 0，不阻塞创建流程）
# ============================================================================
set -euo pipefail

CREATED_SKILL="${1:-}"
RESULT="${2:-}"

# 质量自动上报 hook (游客/用户双模式, fire-and-forget) — 上报 creator 自身使用
QUALITY_SKILL_NAME="huawei-cloud-skill-creator"
QUALITY_REPORT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/quality-report.sh" 2>/dev/null || true

if [[ -z "$CREATED_SKILL" ]]; then
  echo "[huawei-cloud-skill-creator] ERROR: created-skill-name is required (usage: bash scripts/report-skill-created.sh <created-skill-name> [result])" >&2
  QUALITY_STATUS="sys_fail"
  exit 1
fi

# 校验 created-skill-name 必须为 huawei-cloud-* 前缀（与脚本头部注释及
# report.mjs 的约定一致；非 huawei-cloud-* 名称会被记者 SDK 静默忽略）。
if [[ "$CREATED_SKILL" != huawei-cloud-* ]]; then
  echo "[huawei-cloud-skill-creator] ERROR: created-skill-name must start with 'huawei-cloud-' prefix (got: ${CREATED_SKILL})" >&2
  exit 1
fi

# 与 skill-auto-test-pr/run-pipeline.sh 保持一致的 SDK 发现方式：用通配符匹配
# 安装目录下的 reporter CLI，不在可执行代码中硬编码其他 skill 名称
# （华为云 Skill 检查规范 #22 Skill间直接调用 —— 注释/文档里保留说明，代码只做模式匹配）。
SKILLS_BASE_DIR="${HOME}/.agents/skills"
REPORTER_CLI="$(find "${SKILLS_BASE_DIR}" -maxdepth 2 -type f -path '*huawei-cloud-*reporter*/report.mjs' 2>/dev/null | head -n 1 || true)"

if [[ ! -f "$REPORTER_CLI" ]]; then
  echo "[huawei-cloud-skill-creator] WARNING: reporter CLI not found (searched: ${SKILLS_BASE_DIR}/**/huawei-cloud-*reporter*/report.mjs), skipping telemetry"
  exit 0
fi

# 上报的 skill 固定为 huawei-cloud-skill-creator（统计 creator 自身使用次数）。
# report.mjs 内部会吞掉网络错误（catch 后写入 "report failed" 但仍以 0 退出），
# 因此不能只依赖退出码，必须捕获其 stderr 输出并检测失败标记，
# 否则网络不可达时会完全静默（BUG-001，与 SKILL.md 声明的 WARNING 不符）。
REPORT_RC=0
REPORT_OUTPUT="$(node "$REPORTER_CLI" "huawei-cloud-skill-creator" "success" "created skill: ${CREATED_SKILL}" "${RESULT}" 2>&1)" || REPORT_RC=$?
if [[ "$REPORT_RC" -ne 0 ]] || printf '%s\n' "$REPORT_OUTPUT" | grep -q "report failed"; then
  echo "[huawei-cloud-skill-creator] WARNING: telemetry report failed (non-blocking)"
else
  echo "[huawei-cloud-skill-creator] Telemetry delegated to the common reporting SDK: skill=huawei-cloud-skill-creator created=${CREATED_SKILL}"
fi
exit 0
