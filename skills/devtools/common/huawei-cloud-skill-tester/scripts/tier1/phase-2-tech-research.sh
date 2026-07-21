#!/usr/bin/env bash
# phase-2-tech-research.sh — 技术调研
# 对 Phase 1 提取的每条命令做 CLI→SDK→API 三级降级验证
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/lib/utils.sh"
source "$SCRIPT_DIR/lib/chain-verify.sh"

PHASE_NUM=2
PHASE_NAME="tech-research"

run_phase2() {
  local skill_dir="$1"
  local skill_name; skill_name=$(basename "$skill_dir")

  header "Phase 2: 技术调研 — $skill_name"

  check_phase_deps "$skill_dir" 2 || return 1

  local ts; ts=$(timestamp)
  local start_ts; start_ts=$(date +%s)
  local p1_file; p1_file=$(phase_file "$skill_dir" 1)

  # Read commands from Phase 1
  local cmds_json
  local cmds_py_tmp; cmds_py_tmp=$(mktemp)
  cat > "$cmds_py_tmp" << 'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
cmds = d.get('result', {}).get('commands', [])
print(json.dumps(cmds, indent=2))
PYEOF
  cmds_json=$(python3 "$cmds_py_tmp" "$p1_file")
  rm -f "$cmds_py_tmp"

  # Write commands JSON to temp file
  local cmds_tmp; cmds_tmp=$(mktemp)
  echo "$cmds_json" > "$cmds_tmp"

  # Write Python research script to temp file (avoids all heredoc quoting issues)
  local py_tmp; py_tmp=$(mktemp)
  cat > "$py_tmp" << 'PYRESEARCH'
import json, subprocess, os, sys

cmds_f = sys.argv[1]
cmds = json.load(open(cmds_f))
results = []

cli_avail = 0
sdk_avail = 0
api_avail = 0
not_avail = 0

for cmd in cmds:
    desc = cmd.get('description', '')
    executor = cmd.get('executor', 'unknown')
    cmd_raw = cmd.get('command', cmd.get('command_raw', ''))

    entry = {
        'cmd_id': cmd.get('id', 'CMD-00'),
        'description': desc[:100],
        'cli': {'available': False, 'command': None, 'reason': '未调研'},
        'sdk': {'available': False, 'package': None, 'method': None, 'api_path': None, 'error': None},
        'api': {'available': False, 'endpoint': None, 'source': 'not_found'},
        'recommended_executor': 'unknown',
        'risk_level': 'medium'
    }

    # CLI check: try a simple help command
    hcloud_cmd = None
    desc_lower = desc.lower()
    cmd_lower = cmd_raw.lower()
    search_text = desc_lower + ' ' + cmd_lower
    # BSS is NOT supported by hcloud CLI — skip CLI check for BSS
    bss_only = any(kw in search_text for kw in ['bss', 'coupon', 'voucher', 'stored_value', 'card', 'order_coupon', '\u4ee3\u91d1\u5238', '\u4f18\u60e0\u5238', '\u50a8\u503c\u5361'])
    if bss_only:
        entry['cli'] = {'available': False, 'command': None, 'reason': 'BSS not supported by hcloud CLI'}
    else:
        for svc in ['ecs', 'vpc', 'evs', 'eip', 'ims', 'as', 'elb', 'rds', 'dns', 'obs']:
            if svc in search_text or svc.upper() in search_text:
                try:
                    r = subprocess.run(
                        ['hcloud', svc.upper(), '--help'],
                        capture_output=True, text=True, timeout=10
                    )
                    if r.returncode == 0:
                        entry['cli'] = {
                            'available': True,
                            'command': f'hcloud {svc.upper()} <Operation> --cli-region={os.environ.get("HUAWEI_REGION", "cn-north-4")}',
                            'reason': f'hcloud {svc.upper()} CLI 可用'
                        }
                        entry['recommended_executor'] = 'cli'
                        entry['risk_level'] = 'low'
                        cli_avail += 1
                    else:
                        entry['cli'] = {
                            'available': False,
                            'command': None,
                            'reason': f'hcloud {svc.upper()} 命令不存在: {r.stderr[:100]}'
                        }
                except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                    entry['cli'] = {
                        'available': False,
                        'command': None,
                        'reason': f'hcloud CLI 不可用: {str(e)[:80]}'
                    }
                break
        else:
            entry['cli'] = {'available': False, 'command': None, 'reason': '无法从描述推断 hcloud 服务名'}

    # If CLI not available, try SDK
    if not entry['cli']['available']:
        for svc_pkg, sdk_cls in [
            ('bss', 'BssClient'), ('ecs', 'EcsClient'), ('vpc', 'VpcClient'),
            ('evs', 'EvsClient'), ('eip', 'EipClient'), ('iam', 'IamClient'),
            ('rds', 'RdsClient'), ('dns', 'DnsClient'), ('obs', 'ObsClient')
        ]:
            try:
                import_cmd = f'from huaweicloudsdk{svc_pkg}.v2 import {sdk_cls}'
                r = subprocess.run(
                    ['python3', '-c', import_cmd],
                    capture_output=True, text=True, timeout=10
                )
                if r.returncode == 0:
                    entry['sdk'] = {
                        'available': True,
                        'package': f'huaweicloudsdk{svc_pkg}.v2',
                        'method': f'{sdk_cls}.<method>()',
                        'api_path': None,
                        'error': None
                    }
                    entry['recommended_executor'] = 'sdk'
                    entry['risk_level'] = 'low'
                    sdk_avail += 1

                    # Try to find _http_info for API path
                    try:
                        find_result = subprocess.run(
                            ['python3', '-c', f'''
import inspect, importlib
try:
    mod = importlib.import_module("huaweicloudsdk{svc_pkg}.v2")
    client_file = inspect.getfile(getattr(mod, "{sdk_cls}"))
    print(client_file)
except Exception as e:
    print(f"ERROR: {{e}}")
'''],
                            capture_output=True, text=True, timeout=10
                        )
                        client_path = find_result.stdout.strip()
                        if client_path and not client_path.startswith('ERROR'):
                            grep_r = subprocess.run(
                                ['grep', '-oP', 'resource_path\\s*=\\s*"([^"]+)"', client_path],
                                capture_output=True, text=True, timeout=10
                            )
                            if grep_r.stdout:
                                paths = list(set(grep_r.stdout.strip().split('\n')))
                                entry['sdk']['api_path'] = paths[0]
                                entry['api'] = {
                                    'available': True,
                                    'endpoint': paths[0],
                                    'source': 'sdk_http_info'
                                }
                                api_avail += 1
                    except Exception:
                        pass
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        else:
            not_avail += 1
            entry['recommended_executor'] = 'manual'
            entry['risk_level'] = 'high'
            entry['sdk'] = {'available': False, 'package': None, 'method': None, 'api_path': None, 'error': '未找到匹配的 SDK 包'}

    results.append(entry)

summary = {
    'cli_available': cli_avail,
    'sdk_available': sdk_avail,
    'api_available': api_avail,
    'not_available': not_avail
}

output = {'research': results, 'summary': summary}
print(json.dumps(output, indent=2, ensure_ascii=False))
PYRESEARCH

  local research
  research=$(python3 "$py_tmp" "$cmds_tmp")
  rm -f "$py_tmp"

  local end_ts; end_ts=$(date +%s)
  local duration=$((end_ts - start_ts))

  local cli_count; cli_count=$(echo "$research" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['summary']['cli_available'])")
  local sdk_count; sdk_count=$(echo "$research" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['summary']['sdk_available'])")
  local na_count; na_count=$(echo "$research" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['summary']['not_available'])")

  local verdict="pass"
  [ "$na_count" -gt 0 ] && verdict="partial"

  local tmp_json; tmp_json=$(mktemp)
  echo "$research" > "$tmp_json"
  local summary_py_tmp; summary_py_tmp=$(mktemp)
  cat > "$summary_py_tmp" << 'PYEOF'
import json, sys
with open(sys.argv[1]) as f:
    research_data = json.load(f)
r = {
    "phase": int(sys.argv[2]),
    "phase_name": sys.argv[3],
    "tier": 1,
    "target": {"type": "single_skill", "skills": [sys.argv[4]]},
    "timestamp": sys.argv[5],
    "execution_meta": {"duration_s": int(sys.argv[6]), "retry_count": 0, "user_confirmed": False},
    "result": research_data,
    "summary": {"verdict": sys.argv[7], "pass_checks": int(sys.argv[8]), "fail_checks": int(sys.argv[9]), "warn_checks": 0}
}
print(json.dumps(r, indent=2, ensure_ascii=False))
PYEOF
  python3 "$summary_py_tmp" "$tmp_json" "$PHASE_NUM" "$PHASE_NAME" "$skill_name" "$ts" "$duration" "$verdict" "$cli_count" "$na_count" > "$(phase_file "$skill_dir" 2)"
  rm -f "$summary_py_tmp"
  rm -f "$tmp_json"
  rm -f "$cmds_tmp"

  echo ""
  info "调研结果: CLI ${cli_count} | SDK ${sdk_count} | API 发现 | 未可用 ${na_count}"
  echo "$research" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for r in d['research']:
    exe = r['recommended_executor']
    icon = '✅' if exe != 'manual' else '⛔'
    print(f\"  {icon} {r['cmd_id']}: 推荐={exe}, CLI={r['cli']['available']}, SDK={r['sdk']['available']}\")
"
}

for skill_dir in "$@"; do
  run_phase2 "$skill_dir" || exit 1
  echo ""
done

pass "Phase 2: 技术调研全部完成"
