#!/usr/bin/env bash
# phase-3-gen-testcases.sh — 用例生成
# 基于 Phase 1+2 生成功能用例 TC-F 和 API 用例 TC-A
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/lib/utils.sh"
source "$SCRIPT_DIR/lib/chain-verify.sh"

PHASE_NUM=3
PHASE_NAME="test-case-generation"

run_phase3() {
  local skill_dir="$1"
  local skill_name; skill_name=$(basename "$skill_dir")

  header "Phase 3: 用例生成 — $skill_name"

  check_phase_deps "$skill_dir" 3 || return 1

  local ts; ts=$(timestamp)
  local start_ts; start_ts=$(date +%s)

  # Read Phase 1 (capabilities) and Phase 2 (research)
  local p1_file; p1_file=$(phase_file "$skill_dir" 1)
  local p2_file; p2_file=$(phase_file "$skill_dir" 2)

  local testcases
  local tc_gen_py_tmp; tc_gen_py_tmp=$(mktemp)
  cat > "$tc_gen_py_tmp" << 'PYEOF'
import json, sys

with open(sys.argv[1]) as f:
    p1 = json.load(f)
with open(sys.argv[2]) as f:
    p2 = json.load(f)

caps = p1.get('result', {}).get('capabilities', {})
research = p2.get('result', {}).get('research', [])
commands = p1.get('result', {}).get('commands', [])

functional_cases = []
api_cases = []
tc_f_id = 0
tc_a_id = 0

# Generate functional test cases from commands (preferred) or capabilities
executor_map = {}
for r in research:
    desc = r.get('description', '').lower()
    executor_map[desc] = r.get('recommended_executor', 'sdk')

def make_boundary_cmd(cmd_text, executor):
    """Generate a boundary variant of a command. Use limit=1 (most APIs reject limit=0)."""
    if executor == 'cli' and cmd_text.startswith('hcloud'):
        if '--limit=' in cmd_text:
            import re as re2
            return re2.sub(r'--limit=\d+', '--limit=1', cmd_text)
        elif '-limit' not in cmd_text:
            return cmd_text + ' --limit=1'
        return cmd_text
    elif executor == 'sdk' and 'limit=' in cmd_text:
        import re as re2
        return re2.sub(r'limit=\d+', 'limit=1', cmd_text)
    elif executor == 'script' and '--limit=' in cmd_text:
        import re as re2
        return re2.sub(r'--limit=\d+', '--limit=1', cmd_text)
    return cmd_text

def make_boundary_sdk_snippet(snippet, method_name):
    """Generate a boundary SDK snippet with limit=1 (most APIs reject limit=0)."""
    import re as re2
    modified = re2.sub(r'request\.limit\s*=\s*\d+', 'request.limit = 1', snippet)
    if 'request.limit' not in modified and 'ListSub' in method_name:
        modified = modified.replace(
            f'response = client.{method_name}(request)',
            f'request.limit = 1\nresponse = client.{method_name}(request)'
        )
    return modified

# If clean commands exist, generate test cases from them
def replace_placeholders(text):
    import re, os
    _region = os.environ.get('HUAWEI_REGION', 'cn-north-4')
    text = re.sub(r'\{region\}|\{cli_region\}|\{location\}', _region, text)
    text = re.sub(r'<region>|<cli-region>|<location>', _region, text)
    text = re.sub(r'\{id\}|\{instance_id\}|\{server_id\}|\{vpc_id\}|\{subnet_id\}|\{flavor_id\}|\{image_id\}|\{config_id\}', 'test-placeholder', text)
    text = re.sub(r'<id>|<instance_id>|<server_id>|<vpc_id>|<subnet_id>|<flavor_id>|<image_id>|<config_id>', 'test-placeholder', text)
    text = re.sub(r'--cli-region=\{.*?\}|\{.*?\}', '', text)
    return text

if commands and any(c.get('command') for c in commands):
    for cmd in commands:
        tc_f_id += 1
        cmd_text = cmd.get('command', cmd.get('description', ''))
        cmd_text = replace_placeholders(cmd_text)
        # Skip commands that are descriptions without executable code
        if not cmd.get('command') and not cmd.get('command_raw'):
            continue
        # Skip placeholder commands with <...> or [...] that aren't real commands
        if cmd_text and cmd_text.startswith('python3 ') and '<' in cmd_text and '>' in cmd_text:
            continue
        is_write = cmd.get('is_write', False)
        risk = 'high' if is_write else 'low'
        desc_lower = cmd.get('description', '').lower()
        executor = cmd.get('executor', 'sdk')
        # Use Phase 2 research to refine executor, but preserve script executor
        if executor != 'script':
            for r_desc, r_exec in executor_map.items():
                if r_desc in desc_lower or desc_lower[:20] in r_desc:
                    executor = r_exec
                    break
        method_name = cmd.get('method_name', '')
        
        functional_cases.append({
            'id': f'TC-F-{tc_f_id:02d}',
            'name': cmd.get('description', cmd_text[:60]) if cmd.get('description') else f"命令-{tc_f_id:02d}",
            'type': '正向' if not is_write else '变更',
            'command': cmd_text,
            'expected': 'SDK调用成功并返回数据' if executor == 'sdk' else ('CLI命令执行成功' if executor == 'cli' else '脚本执行成功'),
            'is_write': is_write,
            'risk_level': risk,
            'executor': executor,
            'prerequisites': [],
            'verification_method': '执行后检查返回码和输出',
            'dependencies': [],
            'method_name': method_name,
            'service': cmd.get('service', ''),
            'request_class': cmd.get('request_class', '')
        })
        
        # Edge case for read operations: add limit/boundary variant
        if not is_write and cmd_text:
            tc_f_id += 1
            if executor == 'sdk' and method_name:
                bound_cmd = make_boundary_sdk_snippet(cmd_text, method_name)
            else:
                bound_cmd = make_boundary_cmd(cmd_text, executor)
            functional_cases.append({
                'id': f'TC-F-{tc_f_id:02d}',
                'name': f"{cmd.get('description', cmd_text[:40])}-边界",
                'type': '边界',
                'command': bound_cmd,
                'expected': '返回空结果或正确提示',
                'is_write': False,
                'risk_level': 'low',
                'executor': executor,
                'prerequisites': [],
                'verification_method': '不报错即为通过',
                'dependencies': [],
                'method_name': method_name,
                'service': cmd.get('service', ''),
                'request_class': cmd.get('request_class', '')
            })
else:
    # Fallback: generate from capabilities (old behavior)
    for action_type, items in caps.items():
        for item in items:
            tc_f_id += 1
            is_write = action_type in ('create', 'update', 'delete')
            risk = 'high' if action_type in ('create', 'delete') else ('medium' if action_type == 'update' else 'low')
            
            # Find matching research entry
            executor = 'sdk'
            for r in research:
                if r.get('description', '').lower() in item.lower() or item.lower() in r.get('description', '').lower():
                    executor = r.get('recommended_executor', 'sdk')
                    break
            
            functional_cases.append({
                'id': f'TC-F-{tc_f_id:02d}',
                'name': f"{item}-正向",
                'type': '正向',
                'command': item,
                'expected': f'成功{item}',
                'is_write': is_write,
                'risk_level': risk,
                'executor': executor,
                'prerequisites': [],
                'verification_method': '执行后验证结果',
                'dependencies': []
            })
            
            # Add edge case for read operations
            if not is_write:
                tc_f_id += 1
                functional_cases.append({
                    'id': f'TC-F-{tc_f_id:02d}',
                    'name': f"{item}-边界(limit=0/空过滤)",
                    'type': '边界',
                    'command': item,
                    'expected': '返回空结果或正确提示',
                    'is_write': False,
                    'risk_level': 'low',
                    'executor': executor,
                    'prerequisites': [],
                    'verification_method': '不报错即为通过',
                    'dependencies': []
                })

# Generate API test cases from research API paths
for r in research:
    api_info = r.get('api', {})
    if api_info.get('available') and api_info.get('endpoint'):
        tc_a_id += 1
        api_cases.append({
            'id': f'TC-A-{tc_a_id:02d}',
            'name': f"API-{r.get('description', 'unknown')[:40]}",
            'endpoint': api_info['endpoint'],
            'method': 'GET',
            'expected': 'HTTP 200',
            'is_write': False,
            'risk_level': 'medium'
        })

# If no capabilities extracted, generate from commands
if not functional_cases:
    for cmd in commands:
        tc_f_id += 1
        functional_cases.append({
            'id': f'TC-F-{tc_f_id:02d}',
            'name': f"CMD-{cmd.get('id', '')}: {cmd.get('description', '')[:50]}",
            'type': '正向',
            'command': cmd.get('command_raw') or cmd.get('description', ''),
            'source': cmd.get('source', ''),
            'expected': '执行成功',
            'is_write': cmd.get('is_write', False),
            'risk_level': 'high' if cmd.get('is_write', False) else 'low',
            'executor': cmd.get('executor', 'unknown'),
            'prerequisites': [],
            'verification_method': '执行并检查返回值',
            'dependencies': []
        })

result = {
    'functional_cases': functional_cases,
    'api_cases': api_cases,
    'statistics': {
        'total': len(functional_cases) + len(api_cases),
        'functional': len(functional_cases),
        'api': len(api_cases),
        'write_operations': sum(1 for c in functional_cases if c['is_write']),
        'read_operations': sum(1 for c in functional_cases if not c['is_write']),
        'high_risk': sum(1 for c in functional_cases if c['risk_level'] == 'high'),
        'low_risk': sum(1 for c in functional_cases if c['risk_level'] == 'low')
    }
}

print(json.dumps(result, indent=2, ensure_ascii=False))
PYEOF
  testcases=$(python3 "$tc_gen_py_tmp" "$p1_file" "$p2_file")
  rm -f "$tc_gen_py_tmp"

  local end_ts; end_ts=$(date +%s)
  local duration=$((end_ts - start_ts))

  local total
  total=$(echo "$testcases" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['statistics']['total'])")
  local write_ops
  write_ops=$(echo "$testcases" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['statistics']['write_operations'])")
  local high_risk
  high_risk=$(echo "$testcases" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['statistics']['high_risk'])")

  local api_count
  api_count=$(echo "$testcases" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['statistics']['api'])")
  local func_count
  func_count=$(echo "$testcases" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['statistics']['functional'])")

  local verdict="pass"
  [ "$total" -eq 0 ] && verdict="fail"

  local tmp_json; tmp_json=$(mktemp)
  echo "$testcases" > "$tmp_json"
  local summary_py_tmp; summary_py_tmp=$(mktemp)
  cat > "$summary_py_tmp" << 'PYEOF'
import json, sys
with open(sys.argv[1]) as f:
    tc_data = json.load(f)
r = {
    "phase": int(sys.argv[2]),
    "phase_name": sys.argv[3],
    "tier": 1,
    "target": {"type": "single_skill", "skills": [sys.argv[4]]},
    "timestamp": sys.argv[5],
    "execution_meta": {"duration_s": int(sys.argv[6]), "retry_count": 0, "user_confirmed": False},
    "result": tc_data,
    "summary": {"verdict": sys.argv[7], "pass_checks": int(sys.argv[8]), "fail_checks": 0, "warn_checks": 0}
}
print(json.dumps(r, indent=2, ensure_ascii=False))
PYEOF
  python3 "$summary_py_tmp" "$tmp_json" "$PHASE_NUM" "$PHASE_NAME" "$skill_name" "$ts" "$duration" "$verdict" "$total" > "$(phase_file "$skill_dir" 3)"
  rm -f "$summary_py_tmp"
  rm -f "$tmp_json"

  echo ""
  info "生成用例: 共 ${total} 条 (功能 ${func_count}, API ${api_count})"
  info "写操作: ${write_ops} 条 | 高风险: ${high_risk} 条"
  echo ""
  echo "$testcases" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('  📋 功能用例:')
for c in d.get('functional_cases', []):
    mark = '✏️' if c['is_write'] else '📖'
    print(f\"    {mark} {c['id']}: {c['name'][:50]} [{c['risk_level']}]\")
print('  📋 API用例:')
for c in d.get('api_cases', []):
    print(f\"    🔗 {c['id']}: {c.get('endpoint', '')} [{c['risk_level']}]\")
"
}

for skill_dir in "$@"; do
  run_phase3 "$skill_dir" || exit 1
  echo ""
done

pass "Phase 3: 用例生成全部完成"
