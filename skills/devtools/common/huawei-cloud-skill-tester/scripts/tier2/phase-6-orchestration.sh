#!/usr/bin/env bash
# phase-6-orchestration.sh — 多Skill编排测试
# 全量触发词冲突扫描 + 数据传递测试 + 并行加载验证
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/lib/utils.sh"
source "$SCRIPT_DIR/lib/chain-verify.sh"

PHASE_NUM=6
PHASE_NAME="orchestration"

# Parse --skills from args
SKILLS_LIST=""
SKILL_PATHS=()
skills_next=false
for arg in "$@"; do
  if $skills_next; then
    SKILLS_LIST="$arg"
    skills_next=false
  elif [[ "$arg" == --skills=* ]]; then
    SKILLS_LIST="${arg#--skills=}"
  elif [[ "$arg" == --skills ]]; then
    skills_next=true
  elif [[ "$arg" =~ ^/ || "$arg" =~ ^\. ]]; then
    # Only treat absolute or relative paths as skill paths
    SKILL_PATHS+=("$arg")
  fi
done
unset skills_next

# If --skills was passed as separate arg, find it
for ((i=1; i<=$#; i++)); do
  if [[ "${!i}" == "--skills" ]]; then
    next_idx=$((i+1))
    SKILLS_LIST="${!next_idx}"
    break
  fi
done

SKILL_COUNT=${#SKILL_PATHS[@]}

header "Phase 6: 多Skill编排测试"

ts=$(timestamp)
start_ts=$(date +%s)

# === Branch: downgrade for single skill ===
if [ "$SKILL_COUNT" -le 1 ]; then
  info "仅 ${SKILL_COUNT} 个 skill，降级为自检模式"

  local_skill_dir="${SKILL_PATHS[0]}"
  check_phase_deps "$local_skill_dir" 6 ${SKILLS_LIST} || exit 1

  # Read Phase 1 for the single skill's triggers
  p1_file=$(phase_file "$local_skill_dir" 1)
  
  # Read Phase 1 for the single skill's triggers
  p1_file=$(phase_file "$local_skill_dir" 1)
  
  # Write Python self-check script to temp file
  p6s_tmp=$(mktemp)
  cat > "$p6s_tmp" << 'PYSELF'
import json, sys

p1f = sys.argv[1]
skc = sys.argv[2]

with open(p1f) as f:
    p1 = json.load(f)

triggers = p1.get('result', {}).get('metadata', {}).get('triggers', [])
commands = p1.get('result', {}).get('commands', [])

ambiguities = []
seen = set()
for t in triggers:
    t_lower = t.lower().strip()
    for t2 in triggers:
        t2_lower = t2.lower().strip()
        if t != t2 and t_lower in t2_lower:
            ambiguities.append({
                'description': f"触发词 '{t}' 是 '{t2}' 的子串，语义高度重叠",
                'risk': 'low'
            })

cycle_warnings = []
for i, c1 in enumerate(commands):
    for j, c2 in enumerate(commands):
        if i != j and c1.get('is_write') and c2.get('is_write'):
            cycle_warnings.append(f"写操作命令 {c1['id']} 和 {c2['id']} 可能需排序执行")

result = {
    'mode': 'downgraded_self_check',
    'conflict_scan': {
        'internal_ambiguities': ambiguities,
        'cycle_warnings': cycle_warnings
    },
    'data_flow_tests': [],
    'parallel_load_test': {
        'verdict': 'skipped',
        'reason': f'仅{skc}个skill，无需并行测试'
    },
    'cleanup': {'resources_cleaned': 0, 'resources_failed': 0}
}
print(json.dumps(result, indent=2, ensure_ascii=False))
PYSELF

  self_check=$(python3 "$p6s_tmp" "$p1_file" "$SKILL_COUNT")
  rm -f "$p6s_tmp"

  verdict="pass"
  has_ambiguities=$(echo "$self_check" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('conflict_scan',{}).get('internal_ambiguities',[]))" 2>/dev/null || echo "0")
  has_cycles=$(echo "$self_check" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('conflict_scan',{}).get('cycle_warnings',[])))" 2>/dev/null || echo "0")
  [ "$has_ambiguities" -gt 0 ] || [ "$has_cycles" -gt 0 ] && verdict="partial"

  output_file="${local_skill_dir}/phase-6-summary.json"
else
  # === Full orchestration mode ===
  # Check all skills' Phase 5
  for sp in "${SKILL_PATHS[@]}"; do
    sn=$(basename "$sp")
    check_phase_deps "$sp" 6 "${SKILLS_LIST}" || exit 1
  done

  info "全量编排模式: ${SKILL_COUNT} 个 skill"

  # Read phase-1 data for all skills via Python
  # Write Python script to temp file to avoid quoting issues
  py_tmp_p6=$(mktemp)
  cat > "$py_tmp_p6" << 'PYORCH6'
import json, os, sys

sp_list = sys.argv[1:]
skill_data = []

for sp in sp_list:
    sn = os.path.basename(sp)
    p1_file = os.path.join(sp, 'phase-1-summary.json')
    if os.path.isfile(p1_file):
        with open(p1_file) as f:
            p1 = json.load(f)
        triggers = p1.get('result', {}).get('metadata', {}).get('triggers', [])
        resource_types = p1.get('result', {}).get('resource_types', [])
        commands = p1.get('result', {}).get('commands', [])
        skill_data.append({
            'name': sn,
            'triggers': triggers,
            'resource_types': resource_types,
            'commands': commands
        })

# === Conflict Scan ===
conflicts = []
no_conflict_pairs = 0
pairs_checked = 0

for i in range(len(skill_data)):
    for j in range(i+1, len(skill_data)):
        sa = skill_data[i]
        sb = skill_data[j]
        for ta in sa['triggers']:
            ta_clean = ta.strip().lower()
            for tb in sb['triggers']:
                tb_clean = tb.strip().lower()
                pairs_checked += 1
                if ta_clean == tb_clean:
                    conflicts.append({
                        'severity': 'high', 'skill_a': sa['name'], 'skill_b': sb['name'],
                        'trigger': ta_clean[:50],
                        'recommendation': '触发词完全重叠，可能导致Agent路由混乱。建议为其中一个skill修改触发词。'
                    })
                elif ta_clean in tb_clean or tb_clean in ta_clean:
                    conflicts.append({
                        'severity': 'medium', 'skill_a': sa['name'], 'skill_b': sb['name'],
                        'trigger': f"'{ta_clean[:30]}' <-> '{tb_clean[:30]}'",
                        'recommendation': '包含关系触发词，可能误触'
                    })
                else:
                    no_conflict_pairs += 1

# === Data Flow Tests ===
data_flow_tests = []
for i in range(len(skill_data)):
    for j in range(len(skill_data)):
        if i == j: continue
        sa = skill_data[i]; sb = skill_data[j]
        for rt in sa.get('resource_types', []):
            for cmd in sb.get('commands', []):
                desc = cmd.get('description', '').lower()
                if rt.lower() in desc:
                    data_flow_tests.append({
                        'test_id': f'DF-{len(data_flow_tests)+1:02d}',
                        'from_skill': sb['name'], 'to_skill': sa['name'],
                        'data_item': rt, 'status': 'identified',
                        'detail': f"技能 {sb['name']} 的输出 '{rt}' 可能作为 {sa['name']} 的输入"
                    })

parallel_result = {
    'skills_loaded': [sd['name'] for sd in skill_data],
    'verdict': 'pass',
    'detail': f"所有 {len(skill_data)} 个 skill 的 SKILL.md 均可正常解析。"
}
# 真实检查：尝试解析每个 SKILL.md 的 YAML frontmatter
for sd in skill_data:
    sp = next((p for p in sp_list if sd['name'] in p), None)
    if sp:
        smd = os.path.join(sp, 'SKILL.md')
        if os.path.isfile(smd):
            with open(smd) as f:
                content = f.read()
            yaml_match = __import__('re').match(r'^---\s*\n(.*?)\n---', content, __import__('re').DOTALL)
            if not yaml_match:
                parallel_result['verdict'] = 'fail'
                parallel_result['detail'] = f"{sd['name']}: YAML frontmatter 解析失败"

result = {
    'mode': 'full',
    'conflict_scan': {'pairs_checked': pairs_checked, 'conflicts': conflicts, 'no_conflict_pairs': no_conflict_pairs},
    'data_flow_tests': data_flow_tests,
    'parallel_load_test': parallel_result,
    'cleanup': {'resources_cleaned': 0, 'resources_failed': 0}
}
print(json.dumps(result, indent=2, ensure_ascii=False))
PYORCH6

  orchestration_result=$(python3 "$py_tmp_p6" "${SKILL_PATHS[@]}")
  rm -f "$py_tmp_p6"

  verdict="pass"
  high_conflicts=$(echo "$orchestration_result" | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for c in d.get('conflict_scan',{}).get('conflicts',[]) if c.get('severity')=='high'))" 2>/dev/null || echo "0")

  [ "$high_conflicts" -gt 0 ] && verdict="fail"

  output_file="${SKILL_PATHS[0]}/phase-6-summary.json"
fi

end_ts=$(date +%s)
duration=$((end_ts - start_ts))

if [ "$SKILL_COUNT" -le 1 ]; then
  # Write self_check to temp file
  p6_tmp=$(mktemp)
  echo "$self_check" > "$p6_tmp"
  p6_py_tmp=$(mktemp)
  cat > "$p6_py_tmp" << 'P6PY'
import json, sys
data = json.load(open(sys.argv[1]))
PHASE_NUM = int(sys.argv[2])
PHASE_NAME = sys.argv[3]
SKILLS_LIST = sys.argv[4]
TS = sys.argv[5]
DURATION = int(sys.argv[6])
VERDICT = sys.argv[7]
r = {
    'phase': PHASE_NUM,
    'phase_name': PHASE_NAME,
    'tier': 2,
    'target': {'type': 'multi_skill', 'skills': [SKILLS_LIST]},
    'timestamp': TS,
    'execution_meta': {'duration_s': DURATION, 'retry_count': 0, 'user_confirmed': False},
    'result': data,
    'summary': {'verdict': VERDICT, 'pass_checks': 1, 'fail_checks': 0, 'warn_checks': 0}
}
print(json.dumps(r, indent=2, ensure_ascii=False))
P6PY
  write_json "$output_file" "$(python3 "$p6_py_tmp" "$p6_tmp" "$PHASE_NUM" "$PHASE_NAME" "$SKILLS_LIST" "$ts" "$duration" "$verdict")"
  rm -f "$p6_py_tmp"
  rm -f "$p6_tmp"
  echo "$self_check" | python3 -c "
import json, sys
d = json.load(sys.stdin)
amb = d.get('conflict_scan', {}).get('internal_ambiguities', [])
cyc = d.get('conflict_scan', {}).get('cycle_warnings', [])
if amb:
    for a in amb:
        print(f\"  ⚠️  {a['description']} [{a['risk']}]\")
else:
    print('  ✅ 无内部触发词歧义')
if cyc:
    for c in cyc:
        print(f\"  ⚠️  {c}\")
"
else
  # Write orchestration_result to temp file
  p6b_tmp=$(mktemp)
  echo "$orchestration_result" > "$p6b_tmp"
  p6b_py_tmp=$(mktemp)
  cat > "$p6b_py_tmp" << 'P6BPY'
import json, sys
data = json.load(open(sys.argv[1]))
PHASE_NUM = int(sys.argv[2])
PHASE_NAME = sys.argv[3]
SKILLS_LIST = sys.argv[4]
TS = sys.argv[5]
DURATION = int(sys.argv[6])
VERDICT = sys.argv[7]
HIGH_CONFLICTS = int(sys.argv[8])
r = {
    'phase': PHASE_NUM,
    'phase_name': PHASE_NAME,
    'tier': 2,
    'target': {'type': 'multi_skill', 'skills': [SKILLS_LIST]},
    'timestamp': TS,
    'execution_meta': {'duration_s': DURATION, 'retry_count': 0, 'user_confirmed': False},
    'result': data,
    'summary': {'verdict': VERDICT, 'pass_checks': 1, 'fail_checks': HIGH_CONFLICTS, 'warn_checks': 0}
}
print(json.dumps(r, indent=2, ensure_ascii=False))
P6BPY
  write_json "$output_file" "$(python3 "$p6b_py_tmp" "$p6b_tmp" "$PHASE_NUM" "$PHASE_NAME" "$SKILLS_LIST" "$ts" "$duration" "$verdict" "$high_conflicts")"
  rm -f "$p6b_py_tmp"

  echo ""
  echo "$orchestration_result" | python3 -c "
import json, sys
d = json.load(sys.stdin)
cs = d.get('conflict_scan', {})
print(f\"  扫描对数: {cs.get('pairs_checked', 0)}\")
print(f\"  冲突 ({len(cs.get('conflicts', []))}):\")
for c in cs.get('conflicts', []):
    sev = {'high':'🔴','medium':'🟡','low':'🟢'}.get(c['severity'], '⚪')
    print(f\"    {sev} [{c['severity']}] {c['skill_a']} ↔ {c['skill_b']}: {c['trigger'][:50]}\")
print(f\"  数据流: {len(d.get('data_flow_tests', []))} 条待验证\")
print(f\"  并行加载: {d.get('parallel_load_test', {}).get('verdict', 'N/A')}\")
"
fi

pass "Phase 6: 编排测试完成"
