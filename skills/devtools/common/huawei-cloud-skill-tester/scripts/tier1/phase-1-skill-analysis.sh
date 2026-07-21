#!/usr/bin/env bash
# phase-1-skill-analysis.sh — 功能提取
# 读取 SKILL.md，提取 metadata、commands、capabilities、resource_types
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/lib/utils.sh"
source "$SCRIPT_DIR/lib/chain-verify.sh"

PHASE_NUM=1
PHASE_NAME="skill-analysis"

run_phase1() {
  local skill_dir="$1"
  local skill_name; skill_name=$(basename "$skill_dir")

  header "Phase 1: 功能提取 — $skill_name"

  check_phase_deps "$skill_dir" 1 || return 1

  local ts; ts=$(timestamp)
  local start_ts; start_ts=$(date +%s)
  local sk_file="$skill_dir/SKILL.md"

  step "读取 SKILL.md..."

  if [ ! -f "$sk_file" ]; then
    fail "SKILL.md 不存在: $sk_file"
    return 1
  fi

  # Extract metadata via Python (write to temp file to avoid bash escaping issues)
  local py_tmp; py_tmp=$(mktemp)
  cat > "$py_tmp" << 'PYANALYSIS'
import json, re, os, sys

sk_file = sys.argv[1]
skill_dir = sys.argv[2]

with open(sk_file, 'r', encoding='utf-8') as f:
    text = f.read()

# Extract YAML frontmatter
m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
if not m:
    print(json.dumps({'error': 'No YAML frontmatter found'}))
    exit(1)

yaml_text = m.group(1)

name = ''
description = ''
triggers = []
tags = []

for line in yaml_text.split('\n'):
    if line.startswith('name:'):
        name = line.split(':',1)[1].strip()
    elif line.startswith('description: |'):
        pass
    elif line.startswith('tags:'):
        tags_match = re.findall(r'\[(.*?)\]', line)
        if tags_match:
            tags = [t.strip().strip('"') for t in tags_match[0].split(',')]
    elif 'Triggers include:' in line:
        pass

# Better approach: extract description block
desc_match = re.search(r'description: \|(.*?)(?:^tags:|\Z)', text, re.DOTALL | re.MULTILINE)
desc_text = ''
if desc_match:
    desc_text = desc_match.group(1).strip()
    trig_match = re.search(r'Triggers include:\s*(.*?)(?:\.|$)', desc_text, re.DOTALL)
    if trig_match:
        trig_raw = trig_match.group(1)
        triggers = re.findall(r'"([^"]*)"', trig_raw)
        if not triggers:
            triggers = re.findall(r'\'([^\']*)\'', trig_raw)
        if not triggers:
            triggers = [t.strip().strip(',').strip().strip('"').strip("'") for t in trig_raw.replace(',', ' ').split() if t.strip()]

# Extract capabilities by looking for sections
cap_list = []
cap_create = []
cap_update = []
cap_delete = []

overview = re.search(r'## \u6982\u8ff0.*?(?=## )', text, re.DOTALL)
if overview:
    ov_text = overview.group()
    for line in ov_text.split('\n'):
        line = line.strip()
        if line.startswith('| **') or line.startswith('|**'):
            cols = [c.strip().strip('*').strip() for c in line.split('|') if c.strip()]
            for c in cols:
                if '\u67e5\u8be2' in c or '\u5217\u8868' in c or '\u67e5\u770b' in c or 'list' in c.lower() or 'show' in c.lower():
                    cap_list.append(c)
                elif '\u521b\u5efa' in c or 'create' in c.lower():
                    cap_create.append(c)
                elif '\u4fee\u6539' in c or '\u66f4\u65b0' in c or 'update' in c.lower():
                    cap_update.append(c)
                elif '\u5220\u9664' in c or '\u56de\u6536' in c or 'delete' in c.lower() or 'reclaim' in c.lower():
                    cap_delete.append(c)

# Extract commands from code blocks across ALL sections (not just Core Commands)
commands = []
cmd_id = 0

# Helper: detect service from text
def detect_service(txt):
    txt_l = txt.lower()
    for svc in ['bss', 'ecs', 'vpc', 'evs', 'eip', 'iam', 'rds', 'dns', 'obs', 'ims', 'as', 'elb']:
        if svc in txt_l:
            return svc
    return None

def _replace_bare_var(m):
    param = m.group(1)
    var = m.group(2)
    defaults = {'offset': 0, 'limit': 10, 'page': 1, 'index': 0, 'count': 10, 'num': 10, 'size': 10, 'start': 0, 'end': 0}
    val = defaults.get(var, 0)
    return 'request.%s = %s' % (param, val)

# Helper: build executable SDK snippet for a method
def build_sdk_snippet(svc, method_name, request_class, code_block):
    snippet_lines = [
        'import os, json',
        'from huaweicloudsdkcore.auth.credentials import GlobalCredentials, BasicCredentials',
    ]
    client_cls = svc[0].upper() + svc[1:] + 'Client'
    sdk_ver = os.environ.get('HUAWEI_SDK_VERSION', 'v2')
    import json as _json
    _ver_overrides = _json.loads(os.environ.get('SDK_VERSION_OVERRIDES', '{"iam":"v3"}'))
    sdk_ver = _ver_overrides.get(svc, sdk_ver)
    snippet_lines.append('from huaweicloudsdk%s.%s import %s, %s' % (svc, sdk_ver, client_cls, request_class))
    snippet_lines.append('')
    snippet_lines.append('ak, sk = "", ""')
    snippet_lines.append('for k, v in os.environ.items():')
    snippet_lines.append('    u = k.upper()')
    snippet_lines.append("    if not (u.startswith('HUAWEI') or u.startswith('HW') or u.startswith('HWC')): continue")
    snippet_lines.append("    if 'ACCESS_KEY' in u or u.endswith('_AK') or u == 'AK': ak = v or ak")
    snippet_lines.append("    if 'SECRET_KEY' in u or u.endswith('_SK') or u == 'SK': sk = v or sk")
    snippet_lines.append("region = os.environ.get('HUAWEI_REGION', 'cn-north-4')")
    if svc == 'bss':
        snippet_lines.append("domain_id = os.getenv('HUAWEI_DOMAIN_ID', '')")
        snippet_lines.append('cred = GlobalCredentials().with_ak(ak).with_sk(sk).with_domain_id(domain_id)')
        snippet_lines.append("client = %s.new_builder().with_credentials(cred).with_region(region).build()" % client_cls)
    else:
        snippet_lines.append('cred = BasicCredentials(ak, sk)')
        snippet_lines.append("client = %s.new_builder().with_credentials(cred).with_region(%s_region=region).build()" % (client_cls, svc))
    snippet_lines.append('')
    req_lines = []
    in_req = False
    for line in code_block.split('\n'):
        stripped = line.strip()
        if stripped.startswith('request = ') or stripped.startswith('request='):
            in_req = True
        if in_req:
            if stripped.startswith('request.') or stripped.startswith('request =') or stripped.startswith('request='):
                req_lines.append(stripped)
            elif stripped.startswith('response =') or stripped.startswith('all_coupons') or stripped.startswith('by_'):
                break
    if req_lines:
        for rl in req_lines:
            rl = re.sub(r'=\s*"COUPON_ID"', "= ''", rl)
            rl = re.sub(r'=\s*"ORDER_ID"', "= ''", rl)
            rl = re.sub(r'=\s*"CARD_ID"', "= ''", rl)
            rl = re.sub(r'=\s*"your_domain_id"', "= ''", rl)
            # Replace bare variable assignments: request.offset = offset → request.offset = 0
            rl = re.sub(r'request\.(\w+)\s*=\s*(offset|limit|page|index|count|num|size|start|end)\s*$', _replace_bare_var, rl)
            snippet_lines.append(rl)
    else:
        snippet_lines.append('request = %s()' % request_class)
    # Auto-fill common required parameters with safe defaults
    # Read overrides from templates/test-defaults.json if it exists
    defaults_path = os.path.join(skill_dir, 'templates', 'test-defaults.json')
    param_defaults = {}
    if os.path.isfile(defaults_path):
        try:
            with open(defaults_path) as df:
                param_defaults = json.load(df).get('request_defaults', {})
        except Exception:
            pass
    # Built-in safe defaults for common BSS parameters
    from datetime import datetime, timedelta
    _now = datetime.utcnow()
    builtin_defaults = {
        'limit': 10, 'offset': 0,
        'coupon_type': 1, 'status': 2,
        'trade_time_begin': (_now - timedelta(days=365)).strftime('%Y-%m-%dT00:00:00Z'),
        'trade_time_end': (_now + timedelta(days=30)).strftime('%Y-%m-%dT23:59:59Z'),
    }
    builtin_defaults.update(param_defaults)
    # Check which request.xxx assignments are already set
    set_params = set()
    for line in snippet_lines:
        m2 = re.match(r'request\.(\w+)\s*=', line)
        if m2:
            set_params.add(m2.group(1))
    # Add missing parameters with defaults (guarded by hasattr to avoid AttributeError)
    for param, value in builtin_defaults.items():
        if param not in set_params:
            if isinstance(value, str):
                snippet_lines.append("if hasattr(request, '%s'): request.%s = '%s'" % (param, param, value))
            else:
                snippet_lines.append('if hasattr(request, "%s"): request.%s = %s' % (param, param, value))
    snippet_lines.append('')
    snippet_lines.append('response = client.%s(request)' % method_name)
    snippet_lines.append('if hasattr(response, "to_dict"):')
    snippet_lines.append('    print(json.dumps(response.to_dict(), indent=2, ensure_ascii=False)[:2000])')
    snippet_lines.append('else:')
    snippet_lines.append('    print(str(response)[:2000])')
    return '\n'.join(snippet_lines)

# 1. Extract from ALL code blocks (bash, python, etc.) across the entire SKILL.md
bt = chr(96)
bt3 = bt * 3
all_code_blocks = re.findall(bt3 + r'(\w+)?\s*\n(.*?)' + bt3, text, re.DOTALL)

for lang, block in all_code_blocks:
    lang = (lang or '').lower().strip()

    if lang == 'python' or lang == 'py':
        method_calls = re.findall(r'(?:response\s*=\s*)?client\.(\w+)\s*\(', block)
        for method_name in method_calls:
            cmd_id += 1
            svc = detect_service(block) or detect_service(text[:text.find(block)]) or 'bss'
            req_cls = ''.join(w.capitalize() for w in method_name.split('_')) + 'Request'
            is_write = any(kw in method_name.lower() for kw in ['create', 'delete', 'update', 'reclaim', 'destroy'])
            snippet = build_sdk_snippet(svc, method_name, req_cls, block)
            commands.append({
                'id': 'CMD-%02d' % cmd_id,
                'source': 'SKILL.md-python-block',
                'description': '%s (SDK)' % method_name,
                'command': snippet,
                'executor': 'sdk',
                'is_write': is_write,
                'method_name': method_name,
                'service': svc,
                'request_class': req_cls
            })

    elif lang == 'bash' or lang == 'sh' or lang == '':
        for cl in block.strip().split('\n'):
            cl = cl.strip()
            if not cl or cl.startswith('#') or cl.startswith('$'):
                continue
            if cl.startswith('python3 ') and 'scripts/' in cl:
                cmd_id += 1
                is_write = any(kw in cl.lower() for kw in ['create', 'delete', 'update', 'destroy', 'activate', 'reclaim'])
                commands.append({
                    'id': 'CMD-%02d' % cmd_id,
                    'source': 'SKILL.md-bash-block',
                    'description': cl[:80],
                    'command': cl,
                    'executor': 'script',
                    'is_write': is_write
                })
            elif cl.startswith('hcloud '):
                cmd_id += 1
                is_write = any(kw in cl.lower() for kw in ['create', 'delete', 'update', 'destroy'])
                clean_cmd = re.sub(r'<[^>]+>', '', cl).strip()
                commands.append({
                    'id': 'CMD-%02d' % cmd_id,
                    'source': 'SKILL.md-bash-block',
                    'description': clean_cmd[:80],
                    'command': clean_cmd,
                    'executor': 'cli',
                    'is_write': is_write
                })

# 2. Fallback: extract from markdown table rows in Core Commands section
if not commands:
    core_section = re.search(r'##.*\u6838\u5fc3\u547d\u4ee4.*?(?=## |\Z)', text, re.DOTALL)
    if not core_section:
        core_section = re.search(r'##.*Core Commands.*?(?=## |\Z)', text, re.DOTALL)
    for line in (core_section.group() if core_section else text).split('\n'):
        line = line.strip()
        if line.startswith('|') and chr(96) in line:
            cols = [c.strip() for c in line.split('|')]
            cmd_text = ''
            for col in cols:
                bt_matches = re.findall(chr(96) + r'([^' + chr(96) + r']+)' + chr(96), col)
                if bt_matches:
                    cmd_text = bt_matches[0]
                    break
            if not cmd_text:
                continue
            clean_cmd = re.sub(r'<[^>]+>', '', cmd_text).strip()
            clean_cmd = re.sub(r'\s+', ' ', clean_cmd)
            exe = 'cli'
            if clean_cmd.startswith('hcloud '):
                exe = 'cli'
            elif clean_cmd.startswith('python3 ') or clean_cmd.startswith('from '):
                exe = 'sdk'
            elif clean_cmd.startswith('curl '):
                exe = 'api'
            is_write = any(kw in clean_cmd.lower() for kw in ['create', 'delete', 'update', 'put', 'post', 'destroy'])
            cmd_id += 1
            commands.append({
                'id': 'CMD-%02d' % cmd_id,
                'source': 'SKILL.md-table',
                'description': clean_cmd[:80],
                'command': clean_cmd,
                'executor': exe,
                'is_write': is_write
            })

# Detect resource types
resource_types = []
res_patterns = {
    'ecs': ['ecs', 'instance', '\u4e91\u670d\u52a1\u5668', '\u5f39\u6027\u4e91\u670d\u52a1\u5668'],
    'vpc': ['vpc', '\u865a\u62df\u79c1\u6709\u4e91'],
    'eip': ['eip', '\u5f39\u6027\u516c\u7f51'],
    'evs': ['evs', 'clouddvolume', '\u4e91\u786c\u76d8'],
    'bss_voucher': ['voucher', 'coupon', '\u4ee3\u91d1\u5238', '\u4f18\u60e0\u5238'],
    'obs': ['obs', '\u5b58\u50a8\u6876', '\u6876'],
    'rds': ['rds', '\u6570\u636e\u5e93', 'mysql']
}
text_lower = text.lower()
for rtype, patterns in res_patterns.items():
    for p in patterns:
        if p.lower() in text_lower:
            resource_types.append(rtype)
            break

has_write = any(c.get('is_write') for c in commands)

# Scripts list
scripts = []
scripts_dir = os.path.join(skill_dir, 'scripts')
if os.path.isdir(scripts_dir):
    for f in sorted(os.listdir(scripts_dir)):
        if f.endswith('.sh'):
            scripts.append('scripts/%s' % f)

refs = []
refs_dir = os.path.join(skill_dir, 'references')
if os.path.isdir(refs_dir):
    for f in sorted(os.listdir(refs_dir)):
        if f.endswith('.md'):
            refs.append('references/%s' % f)

# Also read templates/test-vars.json for SDK/CLI test cases
test_vars_path = os.path.join(skill_dir, 'templates', 'test-vars.json')
if os.path.isfile(test_vars_path):
    try:
        with open(test_vars_path) as tvf:
            tv_data = json.load(tvf)
        for tc in tv_data.get('test_cases', []):
            cmd_id_val = 'CMD-%02d' % (len(commands)+1)
            cmd_desc = tc.get('name', tc.get('command', ''))[:80]
            cmd_raw = tc.get('command', '')
            exe = tc.get('executor', 'sdk')
            # Auto-detect executor from command content
            if cmd_raw.startswith('python3 scripts/') or cmd_raw.startswith('python3 ./scripts/'):
                exe = 'script'
            elif cmd_raw.startswith('python3 -c '):
                exe = 'cli'  # one-liner SDK import check, run as bash
            elif cmd_raw.startswith('hcloud '):
                exe = 'cli'
            is_write_cmd = any(kw in cmd_raw.lower() for kw in ['create', 'delete', 'update', 'activate', 'reclaim', 'destroy'])
            commands.append({
                'id': cmd_id_val,
                'source': 'templates/test-vars.json',
                'description': cmd_desc,
                'command': cmd_raw,
                'executor': exe,
                'is_write': is_write_cmd
            })
    except Exception:
        pass

# Add scripts/ entries as executable commands
for s in scripts:
    cmd_id_val = 'CMD-%02d' % (len(commands)+1)
    is_write = any(kw in s.lower() for kw in ['create', 'delete', 'cleanup', 'destroy'])
    commands.append({
        'id': cmd_id_val,
        'source': 'scripts/%s' % os.path.basename(s),
        'description': 'Run script: bash %s [args]' % s,
        'executor': 'script',
        'is_write': is_write
    })

result = {
    'metadata': {
        'name': name,
        'description': desc_text[:200] if desc_text else '',
        'triggers': triggers,
        'tags': tags
    },
    'capabilities': {
        'list': cap_list,
        'create': cap_create,
        'update': cap_update,
        'delete': cap_delete
    },
    'has_write_operations': has_write,
    'resource_types': list(set(resource_types)),
    'commands': commands,
    'scripts': scripts,
    'references': refs
}
print(json.dumps(result, indent=2, ensure_ascii=False))
PYANALYSIS

  local analysis
  analysis=$(python3 "$py_tmp" "$sk_file" "$skill_dir")
  local analysis_rc=$?
  rm -f "$py_tmp"

  if [ $analysis_rc -ne 0 ]; then
    fail "SKILL.md 解析失败"
    return 1
  fi

  local end_ts; end_ts=$(date +%s)
  local duration=$((end_ts - start_ts))

  # Count commands for summary
  local cmd_count
  cmd_count=$(echo "$analysis" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('commands', [])))")
  local trig_count
  trig_count=$(echo "$analysis" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('metadata', {}).get('triggers', [])))")
  local res_count
  res_count=$(echo "$analysis" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('resource_types', [])))")

  local verdict="pass"
  [ "$cmd_count" -eq 0 ] && verdict="partial"
  [ "$trig_count" -eq 0 ] && verdict="partial"

  local tmp_json; tmp_json=$(mktemp)
  echo "$analysis" > "$tmp_json"

  local summary_py_tmp; summary_py_tmp=$(mktemp)
  cat > "$summary_py_tmp" << 'PYEOF'
import json, sys

with open(sys.argv[1]) as f:
    analysis = json.load(f)

cmd_count = len(analysis.get("commands", []))
trig_count = len(analysis.get("metadata", {}).get("triggers", []))
verdict = "pass"
if cmd_count == 0:
    verdict = "partial"
if trig_count == 0:
    verdict = "partial"

r = {
    "phase": int(sys.argv[2]),
    "phase_name": sys.argv[3],
    "tier": 1,
    "target": {"type": "single_skill", "skills": [sys.argv[4]]},
    "timestamp": sys.argv[5],
    "execution_meta": {"duration_s": int(sys.argv[6]), "retry_count": 0, "user_confirmed": False},
    "result": analysis,
    "summary": {"verdict": verdict, "pass_checks": cmd_count, "fail_checks": 0, "warn_checks": 0}
}
print(json.dumps(r, indent=2, ensure_ascii=False))
PYEOF
  python3 "$summary_py_tmp" "$tmp_json" "$PHASE_NUM" "$PHASE_NAME" "$skill_name" "$ts" "$duration" > "$(phase_file "$skill_dir" 1)"
  rm -f "$summary_py_tmp"

  rm -f "$tmp_json"

  echo ""
  info "提取结果: ${cmd_count} 条命令, ${trig_count} 个触发词, ${res_count} 种资源类型"
  info "写操作: $(echo "$analysis" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('has_write_operations', False))")"
  echo ""
  echo "$analysis" | python3 -c "
import json,sys
d=json.load(sys.stdin)
cmds = d.get('commands', [])
if cmds:
    print('  命令列表:')
    for c in cmds:
        mark = '[W]' if c['is_write'] else '[R]'
        print(f'    {mark} {c[\"id\"]}: {c[\"description\"][:60]}')
trigs = d.get('metadata', {}).get('triggers', []) 
if trigs:
    print(f'  触发词({len(trigs)}): {trigs[:8]}...')
"
}

for skill_dir in "$@"; do
  run_phase1 "$skill_dir" || exit 1
  echo ""
done

pass "Phase 1: 功能提取全部完成"
