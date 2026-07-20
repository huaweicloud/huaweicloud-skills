#!/usr/bin/env bash
# phase-0-install-check.sh — 安装验证
# 检查 skill 目录完整性，模拟安装/卸载/重装状态
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/lib/utils.sh"
source "$SCRIPT_DIR/lib/chain-verify.sh"

PHASE_NUM=0
PHASE_NAME="install-check"

run_phase0() {
  local skill_dir="$1"
  local skill_name; skill_name=$(basename "$skill_dir")

  header "Phase 0: 安装验证 — $skill_name"

  # Check deps (Phase 0 has no deps)
  check_phase_deps "$skill_dir" 0 || return 1

  local ts; ts=$(timestamp)
  local start_ts; start_ts=$(date +%s)

  # === Directory Integrity ===
  step "检查目录完整性..."
  local checks
  local checks_py_tmp; checks_py_tmp=$(mktemp)
  cat > "$checks_py_tmp" << 'PYEOF'
import json, os, sys
d = sys.argv[1]
r = {
    'SKILL.md': os.path.isfile(d+'/SKILL.md'),
    'scripts/': os.path.isdir(d+'/scripts'),
    'references/': os.path.isdir(d+'/references'),
    'references/iam-policies.md': os.path.isfile(d+'/references/iam-policies.md'),
}
print(json.dumps(r))
PYEOF
  checks=$(python3 "$checks_py_tmp" "$skill_dir")
  rm -f "$checks_py_tmp"
  local dir_pass
  dir_pass=$(echo "$checks" | python3 -c "import json,sys; d=json.load(sys.stdin); print(all(d.values()))")

  # === Install/Uninstall/Reinstall ===
  local hermes_skill_dir="$HOME/.hermes/skills"
  local target_dir="$hermes_skill_dir/$skill_name"
  local is_remote=false
  [[ "$skill_dir" == http://* || "$skill_dir" == https://* ]] && is_remote=true

  step "执行安装测试..."
  local install_status="pass" install_duration=0
  local uninstall_status="pass" uninstall_duration=0
  local reinstall_status="pass" reinstall_duration=0

  # --- Install ---
  if $is_remote; then
    # Remote skill: use hermes skills install
    local inst_start; inst_start=$(date +%s%N)
    hermes skills install "$skill_dir" --yes 2>/dev/null && install_status="pass" || install_status="fail"
    local inst_end; inst_end=$(date +%s%N)
    install_duration=$(( (inst_end - inst_start) / 1000000 ))
  elif [ -d "$target_dir" ]; then
    info "💡 技能已安装于 ~/.hermes/skills/，跳过安装"
    install_status="skipped"
  else
    # Local skill: copy directory
    local inst_start; inst_start=$(date +%s%N)
    mkdir -p "$hermes_skill_dir"
    cp -r "$skill_dir" "$target_dir" && install_status="pass" || install_status="fail"
    local inst_end; inst_end=$(date +%s%N)
    install_duration=$(( (inst_end - inst_start) / 1000000 ))
  fi
  [ "$install_status" = "pass" ] && pass "安装成功 (${install_duration}ms)" || [ "$install_status" = "skipped" ] || fail "安装失败"

  # --- Uninstall ---
  step "执行卸载测试..."
  if $is_remote; then
    local uninst_start; uninst_start=$(date +%s%N)
    hermes skills uninstall "$skill_name" --yes 2>/dev/null && uninstall_status="pass" || uninstall_status="fail"
    local uninst_end; uninst_end=$(date +%s%N)
    uninstall_duration=$(( (uninst_end - uninst_start) / 1000000 ))
  elif [ -d "$target_dir" ] && [ -n "$target_dir" ] && [ "$target_dir" != "/" ] && [ "$target_dir" != "$HOME" ]; then
    local uninst_start; uninst_start=$(date +%s%N)
    rm -rf "$target_dir" && uninstall_status="pass" || uninstall_status="fail"
    local uninst_end; uninst_end=$(date +%s%N)
    uninstall_duration=$(( (uninst_end - uninst_start) / 1000000 ))
  else
    info "技能目录不存在，跳过卸载"
    uninstall_status="skipped"
  fi
  [ "$uninstall_status" = "pass" ] && pass "卸载成功 (${uninstall_duration}ms)" || [ "$uninstall_status" = "skipped" ] || fail "卸载失败"

  # --- Reinstall ---
  step "执行重装测试..."
  if $is_remote; then
    local reinst_start; reinst_start=$(date +%s%N)
    hermes skills install "$skill_dir" --yes 2>/dev/null && reinstall_status="pass" || reinstall_status="fail"
    local reinst_end; reinst_end=$(date +%s%N)
    reinstall_duration=$(( (reinst_end - reinst_start) / 1000000 ))
  else
    local reinst_start; reinst_start=$(date +%s%N)
    cp -r "$skill_dir" "$target_dir" && reinstall_status="pass" || reinstall_status="fail"
    local reinst_end; reinst_end=$(date +%s%N)
    reinstall_duration=$(( (reinst_end - reinst_start) / 1000000 ))
  fi
  [ "$reinstall_status" = "pass" ] && pass "重装成功 (${reinstall_duration}ms)" || fail "重装失败"

  # === Build Result ===
  local dir_pass_bool
  dir_pass_bool=$(echo "$dir_pass" | tr '[:upper:]' '[:lower:]')
  
  local verdict
  [ "$dir_pass_bool" = "true" ] && verdict="pass" || verdict="fail"

  local end_ts; end_ts=$(date +%s)
  local duration=$((end_ts - start_ts))

  local result
  local tmp_checks; tmp_checks=$(mktemp)
  echo "$checks" > "$tmp_checks"
  local result_py_tmp; result_py_tmp=$(mktemp)
  cat > "$result_py_tmp" << 'PYEOF'
import json, sys

with open(sys.argv[1]) as f:
    ck = json.load(f)

dir_pass_bool_val = sys.argv[2] == "True"
install_status = sys.argv[3]
install_duration = float(sys.argv[4])
uninstall_status = sys.argv[5]
uninstall_duration = float(sys.argv[6])
reinstall_status = sys.argv[7]
reinstall_duration = float(sys.argv[8])
target_exists = sys.argv[9] == "True"

r = {
    "install": {"status": install_status, "existing": target_exists, "duration_s": install_duration * 1e-3},
    "uninstall": {"status": uninstall_status, "duration_s": uninstall_duration * 1e-3},
    "reinstall": {"status": reinstall_status, "duration_s": reinstall_duration * 1e-3},
    "directory_integrity": {
        "pass": dir_pass_bool_val,
        "checks": ck
    }
}
print(json.dumps(r, indent=2, ensure_ascii=False))
PYEOF
  result=$(python3 "$result_py_tmp" "$tmp_checks" "$dir_pass_bool" "$install_status" "${install_duration:-0}" "$uninstall_status" "${uninstall_duration:-0}" "$reinstall_status" "${reinstall_duration:-0}" "$( [ -d "$target_dir" ] && echo True || echo False )")
  rm -f "$result_py_tmp"
  rm -f "$tmp_checks"

  # Build summary
  local pass_checks
  pass_checks=$(echo "$checks" | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for v in d.values() if v))")
  local fail_checks
  fail_checks=$(echo "$checks" | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for v in d.values() if not v))")

  # Write phase JSON using temp file to avoid quoting conflicts
  local tmp_json; tmp_json=$(mktemp)
  echo "$result" > "$tmp_json"
  
  local summary_py_tmp; summary_py_tmp=$(mktemp)
  cat > "$summary_py_tmp" << 'PYEOF'
import json, sys

with open(sys.argv[1]) as f:
    result_data = json.load(f)

r = {
    "phase": int(sys.argv[2]),
    "phase_name": sys.argv[3],
    "tier": 1,
    "target": {"type": "single_skill", "skills": [sys.argv[4]]},
    "timestamp": sys.argv[5],
    "execution_meta": {"duration_s": int(sys.argv[6]), "retry_count": 0, "user_confirmed": False},
    "result": result_data,
    "summary": {"verdict": sys.argv[7], "pass_checks": int(sys.argv[8]), "fail_checks": int(sys.argv[9]), "warn_checks": 0}
}
print(json.dumps(r, indent=2, ensure_ascii=False))
PYEOF
  python3 "$summary_py_tmp" "$tmp_json" "$PHASE_NUM" "$PHASE_NAME" "$skill_name" "$ts" "$duration" "$verdict" "$pass_checks" "$fail_checks" > "$(phase_file "$skill_dir" 0)"
  rm -f "$summary_py_tmp"

  rm -f "$tmp_json"

  echo ""
  if [ "$verdict" = "pass" ]; then
    pass "Phase 0 完成 — 目录完整性通过"
  else
    fail "Phase 0 完成 — 目录完整性失败，部分文件缺失"
  fi
}

# Run for each skill
for skill_dir in "$@"; do
  run_phase0 "$skill_dir" || exit 1
  echo ""
done

pass "Phase 0: 安装验证全部完成"
