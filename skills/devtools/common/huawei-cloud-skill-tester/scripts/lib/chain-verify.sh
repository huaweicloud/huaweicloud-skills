#!/usr/bin/env bash
# chain-verify.sh — Chain verification functions for Huawei Cloud Skill Tester
set -uo pipefail

# utils.sh is sourced by the calling phase script before this file

# === Core chain verification ===

# check_phase_deps: Verify all required phase JSON files exist
# Usage: check_phase_deps <skill_dir> <current_phase> [other_skills...]
check_phase_deps() {
  local skill_dir="$1"
  local current_phase="$2"
  shift 2

  local missing=()

  case "$current_phase" in
    0)
      # Phase 0: no deps
      ;;
    1)
      [ ! -f "$(phase_file "$skill_dir" 0)" ] && missing+=("phase-0-summary.json")
      ;;
    2)
      [ ! -f "$(phase_file "$skill_dir" 1)" ] && missing+=("phase-1-summary.json")
      ;;
    3)
      [ ! -f "$(phase_file "$skill_dir" 1)" ] && missing+=("phase-1-summary.json")
      [ ! -f "$(phase_file "$skill_dir" 2)" ] && missing+=("phase-2-summary.json")
      ;;
    4)
      [ ! -f "$(phase_file "$skill_dir" 3)" ] && missing+=("phase-3-summary.json")
      ;;
    5)
      [ ! -f "$(phase_file "$skill_dir" 4)" ] && missing+=("phase-4-summary.json")
      ;;
    6)
      # Phase 6: needs ALL skills' phase-5
      for skill in "$@"; do
        local sd; sd=$(find_skill_path "$skill") || { missing+=("skill '$skill' not found"); continue; }
        [ ! -f "$(phase_file "$sd" 5)" ] && missing+=("${skill}: phase-5-summary.json")
      done
      ;;
    7)
      [ ! -f "$(phase_file "$skill_dir" 6)" ] && missing+=("phase-6-summary.json")
      ;;
    8)
      # Phase 8: no strict deps on execution, but check skill existence
      ;;
    9)
      # Phase 9: check ALL phase-0~8 exist
      for p in 0 1 2 3 4 5 6 7 8; do
        [ ! -f "$(phase_file "$skill_dir" $p)" ] && missing+=("phase-${p}-summary.json")
      done
      for skill in "$@"; do
        local sd; sd=$(find_skill_path "$skill") || continue
        for p in 0 1 2 3 4 5; do
          [ ! -f "$(phase_file "$sd" $p)" ] && missing+=("${skill}: phase-${p}-summary.json")
        done
      done
      ;;
  esac

  if [ ${#missing[@]} -gt 0 ]; then
    echo ""
    fail "链式验证失败 — 缺失以下阶段文件："
    for m in "${missing[@]}"; do
      echo "  ⛔  $m"
    done
    echo ""
    warn "请先完成缺失阶段，或使用 --fresh 从头开始"
    return 1
  fi

  return 0
}

# === Resume / Fresh logic ===

find_first_missing_phase() {
  local skill_dir="$1"
  for p in 0 1 2 3 4 5 6 7 8 9; do
    [ ! -f "$(phase_file "$skill_dir" $p)" ] && echo "$p" && return 0
  done
  echo "all_done"
}

# === Verdict helpers ===

verdict_summary() {
  local pass_count="$1"
  local fail_count="$2"
  local warn_count="${3:-0}"

  if [ "$fail_count" -gt 0 ]; then
    echo "fail"
  elif [ "$warn_count" -gt 0 ]; then
    echo "partial"
  else
    echo "pass"
  fi
}

# === Fresh mode cleanup ===

cleanup_phase_files() {
  local skill_dir="$1"
  [ -z "$skill_dir" ] && { fail "cleanup_phase_files: skill_dir 为空"; return 1; }
  info "🧹 --fresh: 清理 ${skill_dir}/phase-*.json"
  rm -f "${skill_dir}"/phase-*.json
  info "✅ 已清理"
}
