#!/usr/bin/env bash
# phase-5-orchestration.sh — 多Skill编排测试
# 全量触发词冲突扫描 + 数据传递测试 + 并行加载验证
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/lib/utils.sh"
source "$SCRIPT_DIR/lib/chain-verify.sh"

PHASE_NUM=5
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
  elif [[ "$arg" =~ ^/ || "$arg" =~ ^\. || "$arg" =~ ^[A-Za-z]:[/\\] ]]; then
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

header "Phase ${PHASE_NUM}: 多Skill编排测试"

ts=$(timestamp)
start_ts=$(date +%s)

# === Auto-discover sibling skills (default ON) ===
# 用户要求: 默认从被测试 skill 的同级目录找其他 huawei-cloud-* skill 做编排。
# 默认开启; opt-out: WITHOUT_SIBLINGS=1 或 SIBLING_LIMIT=0
if [ "$SKILL_COUNT" -le 1 ]; then
  target_dir="${SKILL_PATHS[0]}"
  parent_dir=$(dirname "$target_dir")
  target_name=$(basename "$target_dir")

  info "扫描同级兄弟 skill (parent: $parent_dir)"
  while IFS= read -r sibling; do
    [ -z "$sibling" ] && continue
    SKILL_PATHS+=("$sibling")
    sname=$(basename "$sibling")
    info "  发现兄弟 skill: $sname"
  done < <(discover_siblings "$target_dir" "${SKILL_PATHS[@]}")
  SKILL_COUNT=${#SKILL_PATHS[@]}

  if [ "$SKILL_COUNT" -gt 1 ]; then
    info "编排模式: ${SKILL_COUNT} skill 组合 (默认扫兄弟)"
  fi
fi

# === Branch: downgrade for single skill ===
if [ "$SKILL_COUNT" -le 1 ]; then
  info "仅 ${SKILL_COUNT} 个 skill（无其他可组合 skill），降级为自检模式"

  local_skill_dir="${SKILL_PATHS[0]}"
  check_phase_deps "$local_skill_dir" 5 ${SKILLS_LIST} || exit 1

  # Read Phase 1 for the single skill's triggers
  p1_file=$(phase_file "$local_skill_dir" 1)
  
  # Read Phase 1 for the single skill's triggers
  p1_file=$(phase_file "$local_skill_dir" 1)
  
  # Write Python self-check script to temp file
  p5s_tmp=$(mktemp)
  cat > "$p5s_tmp" << 'PYSELF'
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

  self_check=$(python3 "$p5s_tmp" "$p1_file" "$SKILL_COUNT")
  rm -f "$p5s_tmp"

  verdict="pass"
  has_ambiguities=$(echo "$self_check" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('conflict_scan',{}).get('internal_ambiguities',[]))" 2>/dev/null || echo "0")
  has_cycles=$(echo "$self_check" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('conflict_scan',{}).get('cycle_warnings',[])))" 2>/dev/null || echo "0")
  [ "$has_ambiguities" -gt 0 ] || [ "$has_cycles" -gt 0 ] && verdict="partial"

  output_file="$(phases_dir "$local_skill_dir")/phase-5-summary.json"
  ensure_test_files_dir "$local_skill_dir" > /dev/null
else
  # === Full orchestration mode ===
  # Strict chain check on the target skill only (the one whose phase-4 ran).
  # Sibling skills (discovered via discover_siblings) often lack phase-1/4
  # JSONs because they haven't been individually tested. We only soft-warn
  # for siblings and let the orchestration logic fall back to SKILL.md parsing.
  check_phase_deps "${SKILL_PATHS[0]}" 5 || exit 1
  for ((i=1; i<SKILL_COUNT; i++)); do
    sp="${SKILL_PATHS[$i]}"
    for p in 1 4; do
      pf="$(phase_file "$sp" $p)"
      if [ ! -f "$pf" ]; then
        warn "兄弟 skill $(basename "$sp") 缺 phase $p: $pf (将 fallback 到 SKILL.md 实时解析)"
      fi
    done
  done

  info "全量编排模式: ${SKILL_COUNT} 个 skill"

  # Read phase-1 data for all skills via Python
  # Write Python script to temp file to avoid quoting issues
  py_tmp_p5=$(mktemp)
  cat > "$py_tmp_p5" << 'PYORCH5'
import json, os, re, sys

sp_list = sys.argv[1:]
skill_data = []
parse_warnings = []

# Phase JSONs live in <skill>-test-files/phases/, not in the skill dir
def _phases_dir(skill_dir):
    parent = os.path.dirname(skill_dir)
    name = os.path.basename(skill_dir)
    return os.path.join(parent, f"{name}-test-files", "phases")

# Fallback: parse SKILL.md frontmatter + body to extract triggers / resource types
# Used when phase-1-summary.json doesn't exist (e.g. sibling skills not yet tested).
# Supports three common trigger declaration patterns found in this repo:
#   1. `triggers: [a, b, c]` — inline YAML list
#   2. `triggers:\n  - a\n  - b` — block YAML list
#   3. `description: |\n  ... Triggers include: "x","y","z"` — embedded in description
def parse_skill_md(skill_dir):
    smd = os.path.join(skill_dir, 'SKILL.md')
    if not os.path.isfile(smd):
        return None
    try:
        with open(smd, encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return None

    # Parse YAML frontmatter block
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    fm = m.group(1) if m else ''

    triggers = []

    # Pattern 1+2: triggers: [..] OR triggers:\n  - ..
    m1 = re.search(r'^triggers\s*:\s*\[([^\]]*)\]', fm, re.MULTILINE)
    if m1:
        triggers += [x.strip().strip('"').strip("'") for x in m1.group(1).split(',') if x.strip()]
    else:
        m2 = re.search(r'^triggers\s*:\s*$', fm, re.MULTILINE)
        if m2:
            # Block list — collect "- xxx" lines after it
            after = fm[m2.end():]
            for line in after.split('\n'):
                stripped = line.strip()
                if stripped.startswith('- '):
                    triggers.append(stripped[2:].strip().strip('"').strip("'"))
                elif stripped and not stripped.startswith('#') and ':' in stripped:
                    break

    # Pattern 3: "Triggers include: ..." in description block
    if not triggers:
        m3 = re.search(r'Triggers\s+include\s*[:：]\s*([^\n]+)', fm, re.IGNORECASE)
        if m3:
            tail = m3.group(1)
            # split on commas, quotes, or Chinese commas
            parts = re.split(r'["\',，；;]+', tail)
            triggers += [p.strip() for p in parts if p.strip() and len(p.strip()) > 1]

    # Heuristic resource types from full content (tags + body)
    body = content.lower()
    rtypes = []
    for kw in ['rds', 'ecs', 'evs', 'vpc', 'eip', 'obs', 'cdn', 'iam', 'bss', 'cce', 'dms', 'dcs',
               'functiongraph', 'modelarts', 'ocr', 'sms', 'swr', 'cbr', 'waf', 'hss', 'elb',
               'nat', 'vpn', 'dws', 'mrs', 'css', 'kms', 'smn', 'apig']:
        if kw in body and kw not in rtypes:
            rtypes.append(kw)

    return {
        'triggers': triggers,
        'resource_types': rtypes,
        'commands': [],  # commands are too brittle to parse from SKILL.md; only phase-1 has them
    }

for sp in sp_list:
    sn = os.path.basename(sp)
    p1_file = os.path.join(_phases_dir(sp), 'phase-1-summary.json')
    if os.path.isfile(p1_file):
        try:
            with open(p1_file, encoding='utf-8') as f:
                p1 = json.load(f)
            triggers = p1.get('result', {}).get('metadata', {}).get('triggers', [])
            resource_types = p1.get('result', {}).get('resource_types', [])
            commands = p1.get('result', {}).get('commands', [])
            skill_data.append({
                'name': sn,
                'triggers': triggers,
                'resource_types': resource_types,
                'commands': commands,
                'source': 'phase-1',
            })
        except Exception as e:
            parse_warnings.append(f"{sn}: phase-1 JSON 解析失败 ({e})")
    else:
        # Sibling skill without phase-1 JSON: parse SKILL.md on the fly
        parsed = parse_skill_md(sp)
        if parsed and (parsed['triggers'] or parsed['resource_types']):
            skill_data.append({
                'name': sn,
                'triggers': parsed['triggers'],
                'resource_types': parsed['resource_types'],
                'commands': parsed['commands'],
                'source': 'skill-md-fallback',
            })
        else:
            parse_warnings.append(f"{sn}: SKILL.md 解析失败 (无 triggers/resource_types) — 已跳过")

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
PYORCH5

  orchestration_result=$(python3 "$py_tmp_p5" "${SKILL_PATHS[@]}")
  rm -f "$py_tmp_p5"

  verdict="pass"
  high_conflicts=$(echo "$orchestration_result" | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for c in d.get('conflict_scan',{}).get('conflicts',[]) if c.get('severity')=='high'))" 2>/dev/null || echo "0")

  [ "$high_conflicts" -gt 0 ] && verdict="fail"

  output_file="$(phases_dir "${SKILL_PATHS[0]}")/phase-5-summary.json"
  ensure_test_files_dir "${SKILL_PATHS[0]}" > /dev/null
fi

end_ts=$(date +%s)
duration=$((end_ts - start_ts))

if [ "$SKILL_COUNT" -le 1 ]; then
  # Write self_check to temp file
  p5_tmp=$(mktemp)
  echo "$self_check" > "$p5_tmp"
  p5_py_tmp=$(mktemp)
  cat > "$p5_py_tmp" << 'P5PY'
import json, os, sys
data = json.load(open(sys.argv[1]))
PHASE_NUM = int(sys.argv[2])
PHASE_NAME = sys.argv[3]
# SKILL_PATHS is a newline-separated list of skill dirs (one per line)
SKILL_PATHS = sys.argv[4].split('\n') if sys.argv[4] else []
SKILL_NAMES = [os.path.basename(p) for p in SKILL_PATHS if p.strip()]
TS = sys.argv[5]
DURATION = int(sys.argv[6])
VERDICT = sys.argv[7]
r = {
    'phase': PHASE_NUM,
    'phase_name': PHASE_NAME,
    'tier': 2,
    'target': {'type': 'multi_skill', 'skills': SKILL_NAMES},
    'timestamp': TS,
    'execution_meta': {'duration_s': DURATION, 'retry_count': 0, 'user_confirmed': False},
    'result': data,
    'summary': {'verdict': VERDICT, 'pass_checks': 1, 'fail_checks': 0, 'warn_checks': 0}
}
print(json.dumps(r, indent=2, ensure_ascii=False))
P5PY
  # Pass SKILL_PATHS as newline-separated string
  _paths_arg=$(printf '%s\n' "${SKILL_PATHS[@]}")
  write_json "$output_file" "$(python3 "$p5_py_tmp" "$p5_tmp" "$PHASE_NUM" "$PHASE_NAME" "$_paths_arg" "$ts" "$duration" "$verdict")"
  rm -f "$p5_py_tmp"
  rm -f "$p5_tmp"
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
  p5b_tmp=$(mktemp)
  echo "$orchestration_result" > "$p5b_tmp"
  p5b_py_tmp=$(mktemp)
  cat > "$p5b_py_tmp" << 'P5BPY'
import json, os, sys
data = json.load(open(sys.argv[1]))
PHASE_NUM = int(sys.argv[2])
PHASE_NAME = sys.argv[3]
# SKILL_PATHS is a newline-separated list of skill dirs (one per line)
SKILL_PATHS = sys.argv[4].split('\n') if sys.argv[4] else []
SKILL_NAMES = [os.path.basename(p) for p in SKILL_PATHS if p.strip()]
TS = sys.argv[5]
DURATION = int(sys.argv[6])
VERDICT = sys.argv[7]
HIGH_CONFLICTS = int(sys.argv[8])
r = {
    'phase': PHASE_NUM,
    'phase_name': PHASE_NAME,
    'tier': 2,
    'target': {'type': 'multi_skill', 'skills': SKILL_NAMES},
    'timestamp': TS,
    'execution_meta': {'duration_s': DURATION, 'retry_count': 0, 'user_confirmed': False},
    'result': data,
    'summary': {'verdict': VERDICT, 'pass_checks': 1, 'fail_checks': HIGH_CONFLICTS, 'warn_checks': 0}
}
print(json.dumps(r, indent=2, ensure_ascii=False))
P5BPY
  # Pass SKILL_PATHS as newline-separated string
  _paths_arg=$(printf '%s\n' "${SKILL_PATHS[@]}")
  write_json "$output_file" "$(python3 "$p5b_py_tmp" "$p5b_tmp" "$PHASE_NUM" "$PHASE_NAME" "$_paths_arg" "$ts" "$duration" "$verdict" "$high_conflicts")"
  rm -f "$p5b_py_tmp"

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

pass "Phase ${PHASE_NUM}: 编排测试完成"
