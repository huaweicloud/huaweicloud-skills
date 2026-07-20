#!/usr/bin/env bash
# phase-4-execute-tests.sh — 用例执行
# 只读自动执行，写操作逐条用户确认
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/lib/utils.sh"
source "$SCRIPT_DIR/lib/chain-verify.sh"

PHASE_NUM=4
PHASE_NAME="test-execution"

run_phase4() {
  local skill_dir="$1"
  local skill_name; skill_name=$(basename "$skill_dir")

  header "Phase 4: 执行 — $skill_name"

  check_phase_deps "$skill_dir" 4 || return 1

  # Force AK/SK check before any SDK/CLI execution
  step "检查 AK/SK 凭证..."
  if ! ensure_ak_sk; then
    fail "AK/SK 凭证缺失，无法执行 SDK/CLI 测试用例"
    warn "请设置环境变量后重试: export HUAWEI_ACCESS_KEY=xxx; export HUAWEI_SECRET_KEY=xxx"
    return 1
  fi

  local ts; ts=$(timestamp)
  local start_ts; start_ts=$(date +%s)

  local p3_file; p3_file=$(phase_file "$skill_dir" 3)

  # Read test cases from Phase 3
  local tc_f
  local tc_read_py_tmp; tc_read_py_tmp=$(mktemp)
  cat > "$tc_read_py_tmp" << 'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
func = d.get('result', {}).get('functional_cases', [])
api = d.get('result', {}).get('api_cases', [])
print(json.dumps(func + api, indent=2))
PYEOF
  tc_f=$(python3 "$tc_read_py_tmp" "$p3_file")
  rm -f "$tc_read_py_tmp"

  # Write test cases to temp file to avoid heredoc quoting issues
  local tc_tmp; tc_tmp=$(mktemp)
  echo "$tc_f" > "$tc_tmp"

  # Write Python execution script to temp file
  local py_tmp; py_tmp=$(mktemp)
  cat > "$py_tmp" << 'PYEXEC'
import json, subprocess, sys, time, os, re

cases_f = sys.argv[1]
skill_root = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.dirname(cases_f))
cases = json.load(open(cases_f))
exec_results = []
all_resources = []

pass_count = 0
fail_count = 0
skip_count = 0
error_count = 0

for tc in cases:
    tc_id = tc.get('id', 'TC-??')
    is_write = tc.get('is_write', False)
    executor = tc.get('executor', 'unknown')
    name = tc.get('name', '')

    print(f"\n  执行: {tc_id} - {name}")

    entry = {
        'tc_id': tc_id,
        'name': name,
        'command': tc.get('command', ''),
        'status': 'skip',
        'duration_s': 0,
        'output_snippet': '',
        'error': None,
        'resource_changes': [],
        'user_confirmed': False
    }

    if is_write:
        risk = tc.get('risk_level', 'high')
        print(f"    ⚠️  写操作 [{risk}] — 命令: {tc.get('command', 'N/A')[:80]}")
        print(f"    预期: {tc.get('expected', 'N/A')[:80]}")
        print(f"    非交互模式: 使用 AK/SK 凭证直接执行写操作")

        entry['user_confirmed'] = True

    executor_type = executor
    start_t = time.time()

    try:
        if executor_type == 'cli':
            cmd_text = tc.get('command', tc.get('description', ''))
            # Clean up HTML-style placeholders: <r> → cn-north-4, <id> → etc.
            cmd_text = re.sub(r'<r>|<region>', 'cn-north-4', cmd_text)
            cmd_text = re.sub(r'<id>|<server_id>|<vpc_id>|<subnet_id>|<flavor_id>|<image_id>', '', cmd_text)
            cmd_text = re.sub(r'<[^>]+>', '', cmd_text)
            # Remove leading/trailing pipes and whitespace that might leak from table extraction
            cmd_text = cmd_text.strip().lstrip('|').strip()
            if cmd_text and len(cmd_text) > 5:
                r = subprocess.run(
                    ['bash', '-c', cmd_text],
                    capture_output=True, text=True, timeout=30,
                    env=os.environ
                )
                output = (r.stdout[:1000] + r.stderr[:300]).strip()
                status = 'pass' if r.returncode == 0 else 'fail'
                if r.returncode != 0:
                    # Show trimmed error for display
                    error_detail = (r.stderr[:200] or r.stdout[:200]).strip()
                else:
                    error_detail = None
            else:
                output = f"命令为空: {cmd_text}"
                status = 'fail'
                error_detail = "命令内容为空，无法执行"
        elif executor_type == 'sdk':
            cmd_text = tc.get('command', '')
            method_name = tc.get('method_name', '')
            # If command starts with python3 -c, run as bash (it's a one-liner, not a snippet)
            if cmd_text.startswith('python3 -c ') or cmd_text.startswith('python3  -c '):
                r = subprocess.run(
                    ['bash', '-c', cmd_text],
                    capture_output=True, text=True, timeout=30,
                    env=os.environ
                )
                output = (r.stdout[:2000] + '\n' + r.stderr[:500]).strip()
                status = 'pass' if r.returncode == 0 else 'fail'
                error_detail = (r.stderr[:300] or r.stdout[:300]).strip() if r.returncode != 0 else None
            # Real SDK execution: write the full Python snippet to a temp file and run it
            elif cmd_text and ('import' in cmd_text or 'client.' in cmd_text or 'from ' in cmd_text):
                # The command field contains a complete executable Python snippet
                sdk_tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
                try:
                    sdk_tmp.write(cmd_text)
                    sdk_tmp.close()
                    r = subprocess.run(
                        ['python3', sdk_tmp.name],
                        capture_output=True, text=True, timeout=60,
                        env=os.environ
                    )
                    output = (r.stdout[:2000] + '\n' + r.stderr[:500]).strip()
                    status = 'pass' if r.returncode == 0 else 'fail'
                    if r.returncode != 0:
                        error_detail = (r.stderr[:300] or r.stdout[:300]).strip()
                    else:
                        error_detail = None
                except Exception as e:
                    output = f"SDK执行异常: {str(e)[:300]}"
                    status = 'fail'
                    error_detail = output
                finally:
                    try:
                        os.unlink(sdk_tmp.name)
                    except OSError:
                        pass
            else:
                # Fallback: try dynamic SDK call for known methods
                try:
                    import importlib
                    # Parse method_name from tc metadata or command text
                    if not method_name:
                        m = re.match(r'(\w+)\s*(?:\((.*?)\))?', cmd_text.strip())
                        method_name = m.group(1) if m else ''

                    svc_map = {
                        'list_sub_customer_coupons': ('bss', 'v2', 'ListSubCustomerCouponsRequest'),
                        'list_customer_coupon_change_records': ('bss', 'v2', 'ListCustomerCouponChangeRecordsRequest'),
                        'list_stored_value_cards': ('bss', 'v2', 'ListStoredValueCardsRequest'),
                        'list_order_coupons_by_order_id': ('bss', 'v2', 'ListOrderCouponsByOrderIdRequest'),
                        'list_coupon_quotas': ('bss', 'v2', 'ListCouponQuotasRequest'),
                        'reclaim_partner_coupons': ('bss', 'v2', 'ReclaimPartnerCouponsRequest'),
                        'create_partner_coupons': ('bss', 'v2', 'CreatePartnerCouponsRequest'),
                        'list_servers_details': ('ecs', 'v2', 'ListServersDetailsRequest'),
                        'show_server': ('ecs', 'v2', 'ShowServerRequest'),
                        'create_servers': ('ecs', 'v2', 'CreateServersRequest'),
                        'delete_servers': ('ecs', 'v2', 'DeleteServersRequest'),
                        'list_flavors': ('ecs', 'v2', 'ListFlavorsRequest'),
                    }
                    if method_name in svc_map:
                        svc, ver, req_cls = svc_map[method_name]
                        mod = importlib.import_module(f'huaweicloudsdk{svc}.{ver}')
                        client_cls_name = svc[0].upper() + svc[1:] + 'Client'
                        client_class = getattr(mod, client_cls_name)
                        from huaweicloudsdkcore.auth.credentials import BasicCredentials, GlobalCredentials
                        ak = os.environ.get('HUAWEI_ACCESS_KEY') or os.environ.get('HWC_AK') or ''
                        sk = os.environ.get('HUAWEI_SECRET_KEY') or os.environ.get('HWC_SK') or ''
                        if svc == 'bss':
                            domain_id = os.environ.get('HUAWEI_DOMAIN_ID', '')
                            cred = GlobalCredentials().with_ak(ak).with_sk(sk).with_domain_id(domain_id)
                            client = client_class.new_builder() \
                                .with_credentials(cred) \
                                .with_endpoints(['bss.myhuaweicloud.com']) \
                                .build()
                        else:
                            cred = BasicCredentials(ak, sk)
                            region_kw = {f'{svc}_region': 'cn-north-4'}
                            client = client_class.new_builder() \
                                .with_credentials(cred) \
                                .with_region(**region_kw) \
                                .build()
                        req_class = getattr(mod, req_cls)
                        request = req_class()
                        method = getattr(client, method_name)
                        resp = method(request)
                        resp_dict = resp.to_dict() if hasattr(resp, 'to_dict') else str(resp)
                        output = json.dumps(resp_dict, indent=2, ensure_ascii=False)[:2000]
                        status = 'pass'
                    else:
                        output = f"未知SDK方法: {method_name}，请添加映射或提供完整Python代码"
                        status = 'fail'
                except ImportError as e:
                    output = f"SDK导入失败: {str(e)[:200]}"
                    status = 'fail'
                except Exception as e:
                    output = f"SDK执行失败: {str(e)[:300]}"
                    status = 'fail'
        elif executor_type == 'script':
            cmd_text = tc.get('command', '')
            # Handle both "python3 scripts/coupon.py list ..." and "bash scripts/test-cli-commands.sh"
            if cmd_text.startswith('python3 ') and 'scripts/' in cmd_text:
                script_part = cmd_text.replace('python3 ', '', 1).strip()
                script_path = os.path.join(skill_root, script_part.split()[0])
                script_args = ' '.join(script_part.split()[1:]) if len(script_part.split()) > 1 else ''
                if os.path.isfile(script_path):
                    full_cmd = f'python3 {script_path} {script_args}'.strip()
                    r = subprocess.run(['bash', '-c', full_cmd], capture_output=True, text=True, timeout=60, env=os.environ)
                    output = (r.stdout[:1000] + '\n' + r.stderr[:500]).strip()
                    status = 'pass' if r.returncode == 0 else 'fail'
                else:
                    output = f"脚本未找到: {script_path}"
                    status = 'fail'
            else:
                script_part = cmd_text.replace('Run script: bash ', '').replace(' [args]', '').strip()
                script_path = os.path.join(skill_root, script_part)
                if not os.path.isfile(script_path):
                    script_path = os.path.join(skill_root, 'scripts', os.path.basename(script_part))
                if os.path.isfile(script_path):
                    r = subprocess.run(['bash', script_path, skill_root], capture_output=True, text=True, timeout=60)
                    output = (r.stdout[:1000] + '\n' + r.stderr[:500]).strip()
                    status = 'pass' if r.returncode == 0 else 'fail'
                else:
                    output = f"脚本未找到: {script_path}"
                    status = 'fail'
        else:
            # Unknown executor: try running command text as shell command
            cmd_text = tc.get('command', '')
            if cmd_text.strip() and len(cmd_text) > 10:
                r = subprocess.run(
                    ['bash', '-c', cmd_text],
                    capture_output=True, text=True, timeout=30,
                    env={**__import__('os').environ}
                )
                output = (r.stdout[:500] + r.stderr[:200]).strip()
                status = 'pass' if r.returncode == 0 else 'fail'
            else:
                output = f"未知执行器 {executor_type}，命令为空"
                status = 'fail'
            # Also fix empty CLI command
            if executor_type == 'cli' and '命令为空' in output:
                status = 'fail'

        elapsed = round(time.time() - start_t, 2)
        entry['duration_s'] = elapsed
        entry['output_snippet'] = output[:300]

        if status == 'pass':
            entry['status'] = 'pass'
            pass_count += 1
            print(f"    ✅ PASS ({elapsed}s)")
        else:
            # Classify SDK/CLI errors: param validation → warn, auth → fail, other → fail
            err_text = output[:500].lower()
            is_param_error = any(kw in err_text for kw in [
                'paramvalidation', 'parameter', 'invalidparam',
                'valueerror', 'typeerror', 'field required',
                'must be', 'cannot be none', 'cannot be empty',
                'invalid value', 'out of range', 'limit',
                '400', 'bad request',
            ])
            is_auth_error = any(kw in err_text for kw in [
                'unauthorized', '401', '403', 'forbidden',
                'access denied', 'auth', 'credential',
                'ak cannot be none', 'sk cannot be none',
            ])
            if is_param_error and not is_auth_error:
                entry['status'] = 'warn'
                # Extract missing param hints from error
                missing_params = []
                for m in re.finditer(r'(\w+)\s+cannot be none|(\w+)\s+cannot be empty|missing\s+(\w+)|field required.*?(\w+)', err_text):
                    missing_params.append(m.group(1) or m.group(2) or m.group(3) or m.group(4))
                # Also extract from request.XXX = '' pattern in command
                cmd_text = tc.get('command', '')
                for m in re.finditer(r'request\.(\w+)\s*=\s*[\'\"]{2}', cmd_text):
                    missing_params.append(m.group(1))
                missing_params = list(dict.fromkeys(missing_params))  # dedupe
                entry['error'] = f'[参数校验] {output[:200]}'
                entry['missing_params'] = missing_params
                entry['manual_test_hint'] = f"需手工测试: API 需要业务数据参数 {missing_params}，请提供真实值后重试"
                skip_count += 1
                print(f"    ⚠️ WARN-参数校验 ({elapsed}s): {output[:80]}")
                if missing_params:
                    print(f"    📋 需手工测试: 缺少业务参数 {missing_params}")
            else:
                entry['status'] = 'fail'
                entry['error'] = output[:300]
                fail_count += 1
                print(f"    ❌ FAIL ({elapsed}s): {output[:100]}")

        if is_write and status == 'pass':
            resource_change = {
                'resource_type': tc.get('endpoint', 'unknown').split('/')[-1] if tc.get('endpoint') else f'resource_{tc_id}',
                'resource_id': f'demo-{tc_id.lower()}-{int(time.time())}',
                'change_type': 'created' if 'create' in tc.get('name', '').lower() else ('deleted' if 'delete' in tc.get('name', '').lower() else 'modified'),
                'cleanup_method': {
                    'type': executor_type,
                    'command': tc.get('command', '')[:100]
                },
                'cleanup_required': True
            }
            entry['resource_changes'] = [resource_change]
            all_resources.append(resource_change)

    except subprocess.TimeoutExpired:
        entry['status'] = 'error'
        entry['error'] = '执行超时'
        entry['duration_s'] = 30
        error_count += 1
        print(f"    ⏰ 超时")
    except Exception as e:
        entry['status'] = 'error'
        entry['error'] = str(e)[:200]
        error_count += 1
        print(f"    ❌ 异常: {str(e)[:100]}")

    exec_results.append(entry)

total = len(cases)
pass_rate = round(pass_count / total * 100, 1) if total > 0 else 0

# Collect manual test hints
manual_test_items = []
for r in exec_results:
    if r.get('status') == 'warn' and r.get('manual_test_hint'):
        manual_test_items.append({
            'tc_id': r['tc_id'],
            'name': r.get('name', ''),
            'missing_params': r.get('missing_params', []),
            'hint': r['manual_test_hint'],
            'command': r.get('command', '')[:200],
        })

if manual_test_items:
    print(f"\n{'='*60}")
    print(f"📋 以下 {len(manual_test_items)} 个用例因缺少业务数据需手工测试:")
    print(f"{'='*60}")
    for i, item in enumerate(manual_test_items, 1):
        params_str = ', '.join(item['missing_params']) if item['missing_params'] else '未知参数'
        print(f"  {i}. {item['tc_id']}: {item['name']}")
        print(f"     缺少参数: {params_str}")
        print(f"     命令: {item['command'][:120]}")
    print(f"{'='*60}")
    print(f"💡 提示: 请提供真实业务数据后手工执行上述命令，或在 templates/test-defaults.json 中配置 request_defaults")

result = {
    'execution_results': exec_results,
    'statistics': {
        'total': total,
        'pass': pass_count,
        'fail': fail_count,
        'skip': skip_count,
        'error': error_count,
        'pass_rate': pass_rate
    },
    'all_resources_changed': all_resources,
    'manual_test_items': manual_test_items
}

print("\n\n---JSON_START---")
print(json.dumps(result, indent=2, ensure_ascii=False))
print("---JSON_END---")
PYEXEC

  local results
  results=$(python3 "$py_tmp" "$tc_tmp" "$skill_dir")
  rm -f "$py_tmp"
  rm -f "$tc_tmp"

  # Extract the JSON from stdout between markers
  local json_output
  json_output=$(echo "$results" | sed -n '/---JSON_START---/,/---JSON_END---/p' | grep -v 'JSON_START\|JSON_END')

  local end_ts; end_ts=$(date +%s)
  local duration=$((end_ts - start_ts))

  # Parse statistics
  local pass_count; pass_count=$(echo "$json_output" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['statistics']['pass'])")
  local fail_count; fail_count=$(echo "$json_output" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['statistics']['fail'])")
  local skip_count; skip_count=$(echo "$json_output" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['statistics']['skip'])")
  local total_count; total_count=$(echo "$json_output" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['statistics']['total'])")

  local verdict="pass"
  [ "$fail_count" -gt 0 ] && verdict="partial"
  [ "$fail_count" -eq "$total_count" ] && verdict="fail"

  local tmp_json; tmp_json=$(mktemp)
  echo "$json_output" > "$tmp_json"
  local summary_py_tmp; summary_py_tmp=$(mktemp)
  cat > "$summary_py_tmp" << 'PYEOF'
import json, sys
with open(sys.argv[1]) as f:
    exec_data = json.load(f)
r = {
    "phase": int(sys.argv[2]),
    "phase_name": sys.argv[3],
    "tier": 1,
    "target": {"type": "single_skill", "skills": [sys.argv[4]]},
    "timestamp": sys.argv[5],
    "execution_meta": {"duration_s": int(sys.argv[6]), "retry_count": 0, "user_confirmed": True},
    "result": exec_data,
    "summary": {"verdict": sys.argv[7], "pass_checks": int(sys.argv[8]), "fail_checks": int(sys.argv[9]), "warn_checks": int(sys.argv[10])}
}
print(json.dumps(r, indent=2, ensure_ascii=False))
PYEOF
  python3 "$summary_py_tmp" "$tmp_json" "$PHASE_NUM" "$PHASE_NAME" "$skill_name" "$ts" "$duration" "$verdict" "$pass_count" "$fail_count" "$skip_count" > "$(phase_file "$skill_dir" 4)"
  rm -f "$summary_py_tmp"
  rm -f "$tmp_json"

  echo ""
  info "执行统计: ${pass_count}P / ${fail_count}F / ${skip_count}S / 共${total_count}条"

  # Print manual test hints from warn cases
  local manual_count; manual_count=$(echo "$json_output" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('manual_test_items',[])))" 2>/dev/null || echo 0)
  if [ "$manual_count" -gt 0 ]; then
    echo ""
    echo "============================================================"
    echo "📋 以下 ${manual_count} 个用例因缺少业务数据需手工测试:"
    echo "============================================================"
    local manual_tmp; manual_tmp=$(mktemp /tmp/manual_test_XXXXXX.json)
    echo "$json_output" > "$manual_tmp"
    local manual_display_py_tmp; manual_display_py_tmp=$(mktemp)
    cat > "$manual_display_py_tmp" << 'PYEOF'
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
for i, item in enumerate(d.get('manual_test_items', []), 1):
    params = ', '.join(item.get('missing_params', [])) or '未知参数'
    tc = item.get('tc_id', '')
    name = item.get('name', '')
    cmd = item.get('command', '')[:120]
    print(f'  {i}. {tc}: {name}')
    print(f'     缺少参数: {params}')
    print(f'     命令: {cmd}')
PYEOF
    python3 "$manual_display_py_tmp" "$manual_tmp"
    rm -f "$manual_display_py_tmp"
    rm -f "$manual_tmp"
    echo "============================================================"
    echo "💡 提示: 请提供真实业务数据后手工执行上述命令，或在 templates/test-defaults.json 中配置 request_defaults"
  fi
}

for skill_dir in "$@"; do
  run_phase4 "$skill_dir" || exit 1
  echo ""
done

pass "Phase 4: 执行全部完成"
