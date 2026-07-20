#!/usr/bin/env bash
# run-test-pipeline.sh — Huawei Cloud Skill Tester Main Entry
# Three-tier, nine-phase testing pipeline for Huawei Cloud skills.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source libraries
source "$SCRIPT_DIR/lib/utils.sh"
source "$SCRIPT_DIR/lib/chain-verify.sh"
UTILS_LOADED=1

# === Defaults ===
SKILLS_LIST=""
SKILL_PATHS=()
FRESH=false
START_PHASE=""
OUTPUT_DIR="reports"
MODE="resume"  # resume | fresh | phase

# === Parse Args ===
usage() {
  echo "用法: run-test-pipeline.sh [选项]"
  echo ""
  echo "选项:"
  echo "  --skills <list>       逗号分隔的 skill 名（如 'bss-voucher-manage,ecs-manage'）"
  echo "  --all-installed       扫描所有已安装的 huawei-cloud-* skills"
  echo "  --fresh               删除所有已有 phase JSON，从头开始"
  echo "  --phase <N>           从指定 Phase (0-9) 开始"
  echo "  --phase resume        从最后一个缺失 Phase 恢复（默认）"
  echo "  --output <dir>        报告输出目录（默认: reports/）"
  echo "  --skill-path <dir>    skill 所在根目录（默认: ~/.hermes/skills/huawei-cloud/）"
  echo ""
  echo "示例:"
  echo "  run-test-pipeline.sh --skills bss-voucher-manage"
  echo "  run-test-pipeline.sh --skills 'bss-voucher-manage,ecs-manage'"
  echo "  run-test-pipeline.sh --all-installed --fresh"
  exit 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --skills) SKILLS_LIST="$2"; shift 2 ;;
    --all-installed) MODE="all_installed"; shift ;;
    --fresh) FRESH=true; shift ;;
    --phase)
      if [ "$2" = "resume" ]; then
        MODE="resume"
      else
        START_PHASE="$2"
        MODE="phase"
      fi
      shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --skill-path) export SKILL_PATH="$2"; shift 2 ;;
    --help|-h) usage ;;
    *) fail "未知参数: $1"; usage ;;
  esac
done

ensure_jq

# === Resolve Skill List ===
resolve_skills() {
  if [ "$MODE" = "all_installed" ]; then
    local base="${SKILL_PATH:-$HOME/.hermes/skills/huawei-cloud}"
    header "扫描已安装技能: $base"
    SKILLS_LIST=""
    for d in "$base"/huawei-cloud-*; do
      [ -d "$d" ] || continue
      local name; name=$(basename "$d")
      SKILLS_LIST="${SKILLS_LIST}${SKILLS_LIST:+,}${name}"
    done
    if [ -z "$SKILLS_LIST" ]; then
      fail "未找到任何 huawei-cloud-* 技能"
      exit 1
    fi
    info "发现技能: $SKILLS_LIST"
  elif [ -z "$SKILLS_LIST" ]; then
    fail "请指定 --skills 或 --all-installed"
    usage
  fi
}

resolve_skills

# Build skill paths
IFS=',' read -ra SKILL_NAMES <<< "$SKILLS_LIST"
for name in "${SKILL_NAMES[@]}"; do
  name=$(echo "$name" | xargs)  # trim
  path=$(find_skill_path "$name") || {
    fail "❌ 技能 '$name' 未找到"
    info "搜索目录: ${SKILL_PATH:-$HOME/.hermes/skills/}"
    ls "${SKILL_PATH:-$HOME/.hermes/skills/}" 2>/dev/null | grep huawei-cloud || true
    exit 1
  }
  SKILL_PATHS+=("$path")
  info "✅ 找到技能: $name → $path"
done

SKILL_COUNT=${#SKILL_PATHS[@]}

# === Fresh mode ===
if $FRESH; then
  for sp in "${SKILL_PATHS[@]}"; do
    cleanup_phase_files "$sp"
  done
  # Also clean tier2/tier3 phase files in first skill's dir (or a designated output dir)
  first_skill_dir="${SKILL_PATHS[0]}"
  [ -n "$first_skill_dir" ] && rm -f "${first_skill_dir}"/phase-6*.json "${first_skill_dir}"/phase-7*.json \
        "${first_skill_dir}"/phase-8*.json "${first_skill_dir}"/phase-9*.json
  info "🧹 已清理所有阶段文件"
  START_PHASE=0
  MODE="phase"
fi

# === Determine Start Phase ===
if [ "$MODE" = "resume" ]; then
  START_PHASE=$(find_first_missing_phase "${SKILL_PATHS[0]}")
  if [ "$START_PHASE" = "all_done" ]; then
    info "所有阶段已完成。使用 --fresh 重新执行"
    exit 0
  fi
  info "从 Phase $START_PHASE 恢复（缺失阶段）"
elif [ "$MODE" = "phase" ] && [ -n "$START_PHASE" ]; then
  info "从指定 Phase $START_PHASE 开始"
fi

# === Pipeline Execution ===
TOTAL_START=$(date +%s)

for ((p = START_PHASE; p <= 9; p++)); do
  header "Phase $p"
  case $p in
    0) bash "$SCRIPT_DIR/tier1/phase-0-install-check.sh" "${SKILL_PATHS[@]}" ;;
    1) bash "$SCRIPT_DIR/tier1/phase-1-skill-analysis.sh" "${SKILL_PATHS[@]}" ;;
    2) bash "$SCRIPT_DIR/tier1/phase-2-tech-research.sh" "${SKILL_PATHS[@]}" ;;
    3) bash "$SCRIPT_DIR/tier1/phase-3-gen-testcases.sh" "${SKILL_PATHS[@]}" ;;
    4) bash "$SCRIPT_DIR/tier1/phase-4-execute-tests.sh" "${SKILL_PATHS[@]}" ;;
    5) bash "$SCRIPT_DIR/tier1/phase-5-cleanup.sh" "${SKILL_PATHS[@]}" ;;
    6) bash "$SCRIPT_DIR/tier2/phase-6-orchestration.sh" --skills "$SKILLS_LIST" "${SKILL_PATHS[@]}" ;;
    7) bash "$SCRIPT_DIR/tier2/phase-7-full-flow.sh" --skills "$SKILLS_LIST" "${SKILL_PATHS[@]}" ;;
    8) bash "$SCRIPT_DIR/tier3/phase-8-compliance-check.sh" --skills "$SKILLS_LIST" "${SKILL_PATHS[@]}" ;;
    9) bash "$SCRIPT_DIR/tier3/phase-9-final-report.sh" --skills "$SKILLS_LIST" --output "$OUTPUT_DIR" "${SKILL_PATHS[@]}" ;;
  esac

  exit_code=$?
  if [ $exit_code -ne 0 ]; then
    fail "Phase $p 执行失败（exit code: $exit_code）"
    warn "修复问题后可通过 --phase $p 或 --resume 继续"
    exit $exit_code
  fi
done

TOTAL_END=$(date +%s)
TOTAL_DURATION=$((TOTAL_END - TOTAL_START))

header "🎉 全部 9 个 Phase 执行完成"
info "总耗时: ${TOTAL_DURATION}s"
info "技能列表: $SKILLS_LIST"
info "报告目录: $OUTPUT_DIR"
