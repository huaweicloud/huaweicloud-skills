#!/usr/bin/env bash
# run-test-pipeline.sh — Huawei Cloud Skill Tester Main Entry
# Three-track, multi-phase testing pipeline for Huawei Cloud skills.
# 实际跑 8 个 phase (Phase 0~7)，统一称为"三轨八节"（三轨 × 八 phase）。
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
OUTPUT_DIR=""
MODE="resume"  # resume | fresh | phase
REGION=""
WITHOUT_SIBLINGS=false  # opt-out: --no-siblings
SIBLING_LIMIT="${SIBLING_LIMIT:-5}"  # default 5; 0 = disable sibling scan

# === Parse Args ===
usage() {
  echo "用法: run-test-pipeline.sh [选项]"
  echo ""
  echo "选项:"
  echo "  --skills <list>       逗号分隔的 skill 名（如 'bss-voucher-manage,ecs-manage'）"
  echo "  --all-installed       扫描所有已安装的 huawei-cloud-* skills"
  echo "  --fresh               删除所有已有 phase JSON，从头开始"
  echo "  --phase <N>           从指定 Phase (0-7) 开始"
  echo "  --phase resume        从最后一个缺失 Phase 恢复（默认）"
  echo "  --region <region>     华为云区域（默认: cn-north-4，也通过 HUAWEI_REGION 环境变量设置）"
  echo "  --output <dir>        报告输出目录（默认: reports/）"
  echo "  --skill-path <dir>    skill 所在根目录（默认: ~/.agents/skills/huawei-cloud/，回退 ~/.hermes/skills/huawei-cloud/）"
  echo "  --no-siblings         关闭 Phase 5/6 同目录兄弟 skill 自动扫描（默认: 开启）"
  echo "  --sibling-limit <N>   兄弟 skill 数量上限（默认 5；0 = 等同 --no-siblings）"
  echo ""
  echo "环境变量（高级）:"
  echo "  SKILL_INSTALL_DIR      覆盖 skill 安装目录（默认自动检测 ~/.agents 或 ~/.hermes）"
  echo "  SKILL_INSTALL_CMD      覆盖远程 skill 的 install/uninstall 命令（默认: 'hermes skills'）"
  echo "  SIBLING_LIMIT          兄弟 skill 数量上限（默认 5）"
  echo "  WITHOUT_SIBLINGS=1     关闭兄弟 skill 扫描（等同 --no-siblings）"
  echo "  ALLOW_WRITES=1         允许 Phase 4 / Phase 6 真正执行写操作（默认 0）"
  echo ""
  echo "示例:"
  echo "  run-test-pipeline.sh --skills bss-voucher-manage"
  echo "  run-test-pipeline.sh --skills 'bss-voucher-manage,ecs-manage'"
  echo "  run-test-pipeline.sh --all-installed --fresh"
  echo "  SKILL_INSTALL_CMD='my-runtime skills' run-test-pipeline.sh --skills xxx"
  echo "  run-test-pipeline.sh --skills rds-query --no-siblings     # 单 skill 模式（降级）"
  echo "  run-test-pipeline.sh --skills rds-query --sibling-limit 3 # 限制最多 3 个兄弟"
  exit 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --skills) SKILLS_LIST="$2"; shift 2 ;;
    --all-installed) MODE="all_installed"; shift ;;
    --fresh) FRESH=true; shift ;;
    --no-siblings) WITHOUT_SIBLINGS=true; shift ;;
    --sibling-limit) SIBLING_LIMIT="$2"; shift 2 ;;
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
    --region) export HUAWEI_REGION="$2"; shift 2 ;;
    --help|-h) usage ;;
    *) fail "未知参数: $1"; usage ;;
  esac
done

# Export so child phase scripts can see the sibling config
if $WITHOUT_SIBLINGS; then
  export WITHOUT_SIBLINGS=1
fi
export SIBLING_LIMIT

ensure_jq

# === Resolve Skill List ===
resolve_skills() {
  if [ "$MODE" = "all_installed" ]; then
    local base="${SKILL_PATH:-${SKILL_PATH_HCLOUD:-$SKILL_INSTALL_DIR/huawei-cloud}}"
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
    info "搜索目录: ${SKILL_PATH:-$SKILL_INSTALL_DIR}"
    ls "${SKILL_PATH:-$SKILL_INSTALL_DIR}" 2>/dev/null | grep huawei-cloud || true
    exit 1
  }
  SKILL_PATHS+=("$path")
  info "✅ 找到技能: $name → $path"
done

SKILL_COUNT=${#SKILL_PATHS[@]}

# === Fresh mode ===
if $FRESH; then
  for sp in "${SKILL_PATHS[@]}"; do
    archive_phase_files "$sp"
  done
  info "🧹 --fresh: 已归档旧 phases/ 到 <skill>-test-files/phases/archive/<ts>/（reports/ 历史保留）"
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

# === Trap: ensure cleanup on exit ===
cleanup_on_exit() {
  local rc=$?
  echo ""
  cleanup_after_test "${SKILL_PATHS[@]}"
  exit $rc
}
trap cleanup_on_exit EXIT INT TERM

# === Pipeline Execution ===
TOTAL_START=$(date +%s)

for ((p = START_PHASE; p <= 7; p++)); do
  header "Phase $p"
  case $p in
    0) bash "$SCRIPT_DIR/tier1/phase-0-install-check.sh" "${SKILL_PATHS[@]}" ;;
    1) bash "$SCRIPT_DIR/tier1/phase-1-skill-analysis.sh" "${SKILL_PATHS[@]}" ;;
    2) bash "$SCRIPT_DIR/tier1/phase-2-tech-research.sh" "${SKILL_PATHS[@]}" ;;
    3) bash "$SCRIPT_DIR/tier1/phase-3-gen-testcases.sh" "${SKILL_PATHS[@]}" ;;
    4) bash "$SCRIPT_DIR/tier1/phase-4-execute-tests.sh" "${SKILL_PATHS[@]}" ;;
    5) bash "$SCRIPT_DIR/tier2/phase-5-orchestration.sh" --skills "$SKILLS_LIST" "${SKILL_PATHS[@]}" ;;
    6) bash "$SCRIPT_DIR/tier2/phase-6-full-flow.sh" --skills "$SKILLS_LIST" "${SKILL_PATHS[@]}" ;;
    7) if [ -n "$OUTPUT_DIR" ]; then
         bash "$SCRIPT_DIR/tier3/phase-7-final-report.sh" --skills "$SKILLS_LIST" --output "$OUTPUT_DIR" "${SKILL_PATHS[@]}"
       else
         bash "$SCRIPT_DIR/tier3/phase-7-final-report.sh" --skills "$SKILLS_LIST" "${SKILL_PATHS[@]}"
       fi
       ;;
  esac

  exit_code=$?
  if [ $exit_code -ne 0 ]; then
    if [ $exit_code -eq 77 ]; then
      # Sentinel: Phase 4/6 已向 stderr 输出 env-var 设置模板。
      # 立即停止流水线，不要跳过、不要 fall through。
      # 调用方（agent 或终端）必须将模板原样输出给用户，
      # 引导用户在自己的 shell / PowerShell $PROFILE 中带外设置环境变量，
      # 然后用 --phase $p 续跑。整个流程禁止向用户索要 AK/SK 明文。
      fail "Phase $p 凭证缺失（exit code: 77）"
      warn "已在 stderr 输出 env-var 设置模板（sentinel: $CRED_REQUEST_SENTINEL）"
      warn "调用方必须：① 将模板原样输出给用户，② 禁止在对话中索要 AK/SK 明文"
      warn "         ③ 用户带外设置后，用 --phase $p 续跑"
      warn "         ④ 或者用 --phase 5 跳过 Phase 4 进入离线分析"
      exit 77
    fi
    fail "Phase $p 执行失败（exit code: $exit_code）"
    warn "修复问题后可通过 --phase $p 或 --resume 继续"
    exit $exit_code
  fi
done

TOTAL_END=$(date +%s)
TOTAL_DURATION=$((TOTAL_END - TOTAL_START))

header "🎉 全部 8 个 Phase 执行完成 (Phase 0~7)"
info "总耗时: ${TOTAL_DURATION}s"
info "技能列表: $SKILLS_LIST"
info "报告目录: $OUTPUT_DIR"
