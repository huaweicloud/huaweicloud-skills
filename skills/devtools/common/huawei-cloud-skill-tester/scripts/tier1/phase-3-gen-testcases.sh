#!/usr/bin/env bash
# phase-3-gen-testcases.sh — 用例生成
# 基于 Phase 1+2 生成功能用例 TC-F 和 API 用例 TC-A
set -euo pipefail

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
  # 共享占位符替换模块(phase-3/4 单一维护点)
  export PLACEHOLDER_UTILS="$SCRIPT_DIR/lib/placeholder-utils.py"
  cat > "$tc_gen_py_tmp" << 'PYEOF'
import json, os, sys, re
from datetime import datetime, timedelta

# 加载共享占位符替换逻辑(见 lib/placeholder-utils.py)
exec(open(os.environ.get('PLACEHOLDER_UTILS', '')).read())

with open(sys.argv[1]) as f:
    p1 = json.load(f)
with open(sys.argv[2]) as f:
    p2 = json.load(f)

skill_dir = sys.argv[3] if len(sys.argv) > 3 else os.getcwd()

# Dynamic date replacement: replace example dates in commands with current-time
# values so queries fall within data retention periods. (ISSUE-007: SKILL.md
# example dates may be months old, causing empty results.)
_NOW = datetime.utcnow()
_DATE_REPLACEMENTS = {
    # --from/--to with YYYY-MM-DD or YYYYMMDD format
    r'--from[=\s]+\d{4}-\d{2}-\d{2}': '--from=' + (_NOW - timedelta(days=7)).strftime('%Y-%m-%d'),
    r'--to[=\s]+\d{4}-\d{2}-\d{2}': '--to=' + _NOW.strftime('%Y-%m-%d'),
    r'--from[=\s]+\d{8}': '--from=' + (_NOW - timedelta(days=7)).strftime('%Y%m%d'),
    r'--to[=\s]+\d{8}': '--to=' + _NOW.strftime('%Y%m%d'),
    # --start-date/--end-date
    r'--start-date[=\s]+\d{4}-\d{2}-\d{2}': '--start-date=' + (_NOW - timedelta(days=7)).strftime('%Y-%m-%d'),
    r'--end-date[=\s]+\d{4}-\d{2}-\d{2}': '--end-date=' + _NOW.strftime('%Y-%m-%d'),
}

def dynamic_replace_dates(cmd_text):
    """Replace example dates in commands with dynamic current-time values."""
    for pat, repl in _DATE_REPLACEMENTS.items():
        cmd_text = re.sub(pat, repl, cmd_text, flags=re.IGNORECASE)
    return cmd_text

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
    """Generate a boundary variant of a command.

    For CLI: only reduce existing --limit values (never add blindly).
    For script: construct a boundary date scenario (reversed date range).
    For SDK: only reduce existing limit= values.
    (ISSUE-006: boundary case must differ from positive case, not just suffix the name)
    """
    t = cmd_text.strip()
    low = t.lower()
    # 无参/帮助/配置类命令不支持 --limit, 边界保持原样(预期正常执行)
    if re.match(r'^hcloud\s+(--help|-h|--version|help|version|configure)\b', low):
        return t
    if executor == 'cli' and t.startswith('hcloud'):
        if '--limit=' in t:
            return re.sub(r'--limit=\d+', '--limit=1', t)
        return t
    elif executor == 'script':
        # Boundary for script commands: reverse --from/--to dates (to > from → error)
        # or use a 1-day window if dates exist
        if '--from=' in t and '--to=' in t:
            _from_val = re.search(r'--from=(\S+)', t)
            _to_val = re.search(r'--to=(\S+)', t)
            if _from_val and _to_val:
                return t.replace('--from=' + _from_val.group(1), '--from=' + _to_val.group(1)).replace('--to=' + _to_val.group(1), '--to=' + _from_val.group(1))
        return t
    elif executor == 'sdk' and 'limit=' in t:
        return re.sub(r'limit=\d+', 'limit=1', t)
    elif executor == 'script' and '--limit=' in t:
        return re.sub(r'--limit=\d+', '--limit=1', t)
    return t

def make_boundary_sdk_snippet(snippet, method_name):
    """Generate a boundary SDK snippet with limit=1.

    Only reduces existing request.limit values — never blindly inserts
    request.limit for methods that may not support it.
    (TESTER-ISSUE-010: blind --limit addition caused false failures)
    """
    import re as re2
    modified = re2.sub(r'request\.limit\s*=\s*\d+', 'request.limit = 1', snippet)
    return modified

# If clean commands exist, generate test cases from them
# (replace_placeholders 定义在共享模块 lib/placeholder-utils.py, 上方 exec 加载)

def is_template_or_interactive(cmd_text):
    """识别不可自动执行的模板命令/交互命令: 返回 True 则跳过生成。"""
    import re
    t = (cmd_text or '').strip().lower()
    if not t:
        return True
    # 裸 hcloud(模板清理后无操作子命令)
    if t == 'hcloud':
        return True
    # hcloud 帮助/配置类交互命令(无实际操作子命令)。
    # 注意: 过滤 --version 选项(实际不支持), 但保留 version 子命令(真实可执行)。
    if re.match(r'^hcloud\s+(--help|-h|--version|help|configure)\b', t):
        return True
    # 含 [--key=value ...] 等模板语法
    if re.search(r'\[\s*--[a-z-]+=\.\.\.', t) or re.search(r'\[\s*--key=value', t):
        return True
    # 未解析的 URL/API 模板占位符({endpoint}/https://{...})或残留 {xxx}
    if re.search(r'\{endpoint\}|\{url\}|\{host\}|https?://\{', t) or re.search(r'\{[a-z_]+\}', t):
        return True
    # 残留 <xxx> 占位符(非 shell 重定向, 是未替换模板)
    if re.search(r'\b(curl|wget)\b.*<[a-z_]+>', t):
        return True
    # 残留空 --cli-region=(占位符清理后仍无值)
    if re.search(r'--cli-region=\s*(?:\s|$)', t):
        return True
    return False

if commands and any(c.get('command') for c in commands):
    for cmd in commands:
        tc_f_id += 1
        cmd_text = cmd.get('command', cmd.get('description', ''))
        cmd_text = replace_placeholders(cmd_text, skill_dir)
        cmd_text = dynamic_replace_dates(cmd_text)
        # Skip commands that are descriptions without executable code
        if not cmd.get('command') and not cmd.get('command_raw'):
            continue
        # Skip placeholder commands with <...> or [...] that aren't real commands
        if cmd_text and cmd_text.startswith('python3 ') and '<' in cmd_text and '>' in cmd_text:
            continue
        # Skip interactive/template commands (hcloud configure, [--key=value ...])
        if is_template_or_interactive(cmd_text):
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
        if not is_write and cmd_text and not is_template_or_interactive(cmd_text):
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
    # 负向用例生成(#005): 对 CLI 命令生成"未知参数"变体, 验证报错质量。
    # 负向用例预期 CLI 拒绝未知参数(非零退出码 + 错误提示); 若命令静默接受, 则判 fail。
    # type 用英文 'negative' 作为稳定标识(避免中文硬编码耦合, 展示名仍含"负向")。
    for cmd in commands:
        c_text = cmd.get('command', '')
        if not c_text or not c_text.strip().startswith('hcloud '):
            continue
        if cmd.get('is_write', False):
            continue
        if is_template_or_interactive(c_text):
            continue
        tc_f_id += 1
        neg_cmd = c_text.strip() + ' --invalid-flag-xyz'
        functional_cases.append({
            'id': f'TC-F-{tc_f_id:02d}',
            'name': f"{cmd.get('description', c_text[:40])}-负向(未知参数)",
            'type': 'negative',
            'command': neg_cmd,
            'expected': 'CLI 应拒绝未知参数并给出错误提示',
            'is_write': False,
            'risk_level': 'low',
            'executor': 'cli',
            'prerequisites': [],
            'verification_method': '非零退出码且报错即通过',
            'dependencies': [],
            'method_name': '',
            'service': cmd.get('service', ''),
            'request_class': ''
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
  testcases=$(python3 "$tc_gen_py_tmp" "$p1_file" "$p2_file" "$skill_dir")
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
  ensure_test_files_dir "$skill_dir" > /dev/null
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

# Parse args: getopts for -s, pre-filter --skill (getopts can't handle --long)
SKILL_DIRS=()
_rest=()
while [ $# -gt 0 ]; do
  case "$1" in
    --skill) SKILL_DIRS+=("$2"); shift 2 ;;
    --skill=*) SKILL_DIRS+=("${1#--skill=}"); shift ;;
    --help|-h) echo "用法: $(basename "$0") [-s <dir>]... [--skill <dir>]... [<dir>...]"; exit 0 ;;
    *) _rest+=("$1"); shift ;;
  esac
done
set -- ${_rest[@]+"${_rest[@]}"}
OPTIND=1
while getopts ":s:h" opt; do
  case $opt in
    s) SKILL_DIRS+=("$OPTARG") ;;
    h) echo "用法: $(basename "$0") [-s <dir>]... [--skill <dir>]... [<dir>...]"; exit 0 ;;
    \?) ;;
  esac
done
shift $((OPTIND-1))
for arg in "$@"; do SKILL_DIRS+=("$arg"); done

for skill_dir in "${SKILL_DIRS[@]}"; do
  run_phase3 "$skill_dir" || exit 1
  echo ""
done

pass "Phase 3: 用例生成全部完成"
