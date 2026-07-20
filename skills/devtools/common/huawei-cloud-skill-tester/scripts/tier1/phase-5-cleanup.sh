#!/usr/bin/env bash
# phase-5-cleanup.sh — 资源清理
# 自动清理 Phase 4 产生的资源变更，失败则输出手动指引
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/lib/utils.sh"
source "$SCRIPT_DIR/lib/chain-verify.sh"

PHASE_NUM=5
PHASE_NAME="cleanup"

run_phase5() {
  local skill_dir="$1"
  local skill_name; skill_name=$(basename "$skill_dir")

  header "Phase 5: 清理 — $skill_name"

  check_phase_deps "$skill_dir" 5 || return 1

  local ts; ts=$(timestamp)
  local start_ts; start_ts=$(date +%s)
  local p4_file; p4_file=$(phase_file "$skill_dir" 4)

  # Read Phase 4 resources
  local resources
  local res_read_py_tmp; res_read_py_tmp=$(mktemp)
  cat > "$res_read_py_tmp" << 'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
resources = d.get('result', {}).get('all_resources_changed', [])
print(json.dumps(resources, indent=2))
PYEOF
  resources=$(python3 "$res_read_py_tmp" "$p4_file")
  rm -f "$res_read_py_tmp"

  local res_count
  res_count=$(echo "$resources" | python3 -c "import json,sys; r=json.load(sys.stdin); print(len(r))")

  local result
  if [ "$res_count" -eq 0 ]; then
    info "Phase 4 无资源变更，跳过清理"
    result='{
      "mode": "skipped_no_resources",
      "resources_to_clean": [],
      "auto_cleaned": [],
      "failed_cleanup": [],
      "manual_cleanup_instructions": []
    }'
  else
    step "检测到 ${res_count} 个资源变更，尝试自动清理..."

    local res_tmp; res_tmp=$(mktemp)
    echo "$resources" > "$res_tmp"

    local cleanup_py_tmp; cleanup_py_tmp=$(mktemp)
    cat > "$cleanup_py_tmp" << 'PYEOF'
import json, sys, time, subprocess

with open(sys.argv[1]) as f:
    resources = json.load(f)
auto_cleaned = []
failed_cleanup = []
manual_instructions = []

for res in resources:
    rid = res.get('resource_id', 'unknown')
    rtype = res.get('resource_type', 'unknown')
    ctype = res.get('change_type', 'modified')
    cleanup_method = res.get('cleanup_method', {})
    cleanup_type = cleanup_method.get('type', 'none')
    cleanup_cmd = cleanup_method.get('command', '')
    cleanup_req = res.get('cleanup_required', True)
    
    print(f"  资源: {rid} ({rtype}, {ctype})")
    
    if not cleanup_req:
        print(f"    ⏭️  无需清理")
        auto_cleaned.append({
            'resource_id': rid,
            'status': 'skipped',
            'attempts': 0,
            'error': '无需清理（资源已删除或为只读操作）'
        })
        continue
    
    # Attempt real cleanup with retry
    success = False
    attempts_count = 0
    last_error = ''

    env = __import__('os').environ.copy()
    for attempt in range(1, 4):
        attempts_count = attempt
        print(f"    清理尝试 {attempt}/3...")

        try:
            if cleanup_type == 'cli' and cleanup_cmd:
                r = subprocess.run(
                    ['bash', '-c', cleanup_cmd],
                    capture_output=True, text=True, timeout=30,
                    env=env
                )
                if r.returncode == 0:
                    success = True
                    print(f"    ✅ 清理成功 (CLI)")
                    break
                else:
                    last_error = r.stderr[:200] or r.stdout[:200]
                    print(f"    ❌ CLI失败: {last_error[:80]}")
            elif cleanup_type == 'sdk' and cleanup_cmd:
                r = subprocess.run(
                    ['python3', '-c', cleanup_cmd],
                    capture_output=True, text=True, timeout=30,
                    env=env
                )
                if r.returncode == 0:
                    success = True
                    print(f"    ✅ 清理成功 (SDK)")
                    break
                else:
                    last_error = r.stderr[:200] or r.stdout[:200]
                    print(f"    ❌ SDK失败: {last_error[:80]}")
            else:
                last_error = f"无可用清理方法 (type={cleanup_type})"
                print(f"    ⏭️  {last_error}")
                break
        except subprocess.TimeoutExpired:
            last_error = '执行超时'
            print(f"    ⏰ 超时")
        except Exception as e:
            last_error = str(e)[:200]
            print(f"    ❌ 异常: {last_error[:80]}")
    
    if success:
        auto_cleaned.append({
            'resource_id': rid,
            'status': 'success',
            'attempts': attempts_count,
            'error': None
        })
    else:
        failed_cleanup.append({
            'resource_id': rid,
            'reason': last_error or '清理失败：已重试3次',
            'manual_steps': [
                f'1. 登录华为云控制台',
                f'2. 找到 {rtype} 资源 {rid}',
                f'3. 手动删除该资源'
            ]
        })
        manual_instructions.append({
            'resource_type': rtype,
            'resource_id': rid,
            'reason': last_error or '自动清理失败',
            'manual_steps': [
                f'hcloud <Service> Delete --<id>={rid}',
                f'或: 华为云控制台 → {rtype} → 删除'
            ],
            'reference': '华为云控制台'
        })

result = {
    'mode': 'normal',
    'resources_to_clean': resources,
    'auto_cleaned': auto_cleaned,
    'failed_cleanup': failed_cleanup,
    'manual_cleanup_instructions': manual_instructions
}
print(json.dumps(result, indent=2, ensure_ascii=False))
PYEOF
    result=$(python3 "$cleanup_py_tmp" "$res_tmp")
    rm -f "$cleanup_py_tmp" "$res_tmp"
  fi

  local end_ts; end_ts=$(date +%s)
  local duration=$((end_ts - start_ts))

  # Count results
  local auto_count; auto_count=$(echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('auto_cleaned', [])))")
  local fail_count; fail_count=$(echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('failed_cleanup', [])))")
  local manual_count; manual_count=$(echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('manual_cleanup_instructions', [])))")

  local verdict="pass"
  [ "$fail_count" -gt 0 ] && verdict="partial"

  local tmp_json; tmp_json=$(mktemp)
  echo "$result" > "$tmp_json"
  local summary_py_tmp; summary_py_tmp=$(mktemp)
  cat > "$summary_py_tmp" << 'PYEOF'
import json, sys
with open(sys.argv[1]) as f:
    cleanup_data = json.load(f)
r = {
    "phase": int(sys.argv[2]),
    "phase_name": sys.argv[3],
    "tier": 1,
    "target": {"type": "single_skill", "skills": [sys.argv[4]]},
    "timestamp": sys.argv[5],
    "execution_meta": {"duration_s": int(sys.argv[6]), "retry_count": 3, "user_confirmed": False},
    "result": cleanup_data,
    "summary": {"verdict": sys.argv[7], "pass_checks": int(sys.argv[8]), "fail_checks": int(sys.argv[9]), "warn_checks": int(sys.argv[10])}
}
print(json.dumps(r, indent=2, ensure_ascii=False))
PYEOF
  python3 "$summary_py_tmp" "$tmp_json" "$PHASE_NUM" "$PHASE_NAME" "$skill_name" "$ts" "$duration" "$verdict" "$auto_count" "$fail_count" "$manual_count" > "$(phase_file "$skill_dir" 5)"
  rm -f "$summary_py_tmp"
  rm -f "$tmp_json"

  echo ""
  info "清理结果: 自动清理 ${auto_count} | 失败 ${fail_count} | 需手动 ${manual_count}"
  if [ "$manual_count" -gt 0 ]; then
    warn "以下资源需要手动清理:"
    echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for m in d.get('manual_cleanup_instructions', []):
    print(f\"  ⛔ {m['resource_type']}: {m['resource_id']}\")
    print(f\"     步骤: {m['manual_steps'][0]}\")
"
  fi
}

for skill_dir in "$@"; do
  run_phase5 "$skill_dir" || exit 1
  echo ""
done

pass "Phase 5: 清理全部完成"
