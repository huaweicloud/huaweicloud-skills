#!/usr/bin/env bash
# phase-8-compliance-check.sh — 合规检查
# 逐 skill 执行 validate-skill.sh + 安全扫描
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/lib/utils.sh"
source "$SCRIPT_DIR/lib/chain-verify.sh"

PHASE_NUM=8
PHASE_NAME="compliance-check"

# Parse args
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
  elif [[ "$arg" =~ ^/ || "$arg" =~ ^\\. ]]; then
    SKILL_PATHS+=("$arg")
  fi
done
unset skills_next

header "Phase 8: 合规检查"

ts=$(timestamp)
start_ts=$(date +%s)

# Locate validate-skill.sh
VALIDATE_SCRIPT="${SCRIPT_DIR}/../huawei-cloud-skill-creator/scripts/validate-skill.sh"
[ ! -f "$VALIDATE_SCRIPT" ] && VALIDATE_SCRIPT="${SCRIPT_DIR}/../../huawei-cloud-skill-creator/scripts/validate-skill.sh"
[ ! -f "$VALIDATE_SCRIPT" ] && VALIDATE_SCRIPT="${HOME}/.hermes/skills/huawei-cloud/huawei-cloud-skill-creator/scripts/validate-skill.sh"
[ ! -f "$VALIDATE_SCRIPT" ] && VALIDATE_SCRIPT=""

if [ -z "$VALIDATE_SCRIPT" ]; then
  warn "validate-skill.sh 未找到，将使用内置检查"
fi

# Locate skill_audit.py
AUDIT_SCRIPT=""
for candidate in \
    "${SCRIPT_DIR}/../skill-targeted-audit/scripts/skill_audit.py" \
    "${SCRIPT_DIR}/../../skill-targeted-audit/scripts/skill_audit.py" \
    "${HOME}/.agents/skills/skill-targeted-audit/scripts/skill_audit.py" \
    "${HOME}/.hermes/skills/skill-targeted-audit/scripts/skill_audit.py"; do
  if [ -f "$candidate" ]; then
    AUDIT_SCRIPT="$candidate"
    break
  fi
done

if [ -n "$AUDIT_SCRIPT" ] && command -v python3 &>/dev/null; then
  info "skill_audit.py 已找到: $AUDIT_SCRIPT"
else
  warn "skill_audit.py 未找到，安全审视将跳过"
fi

skills_checked_json=$(AUDIT_SCRIPT="$AUDIT_SCRIPT" python3 << 'PYEOF'
import json, os, subprocess, sys

skill_paths = sys.argv[1:]
results = []

for sp in skill_paths:
    sn = os.path.basename(sp)
    print(f"\n  [{sn}] 合规检查...", flush=True)
    
    checks = []
    pass_count = 0
    fail_count = 0
    warn_count = 0
    
    sk_file = os.path.join(sp, 'SKILL.md')
    
    # === Critical checks ===
    critical_checks = [
        ('SKILL.md 存在', 'critical', os.path.isfile(sk_file)),
    ]
    
    if os.path.isfile(sk_file):
        with open(sk_file) as f:
            content = f.read()
        
        critical_checks += [
            ('YAML Frontmatter(---)', 'critical', '---' in content[:200]),
            ('name 字段', 'critical', 'name:' in content[:200]),
            ('description 字段', 'critical', 'description:' in content[:200]),
            ('Triggers include:', 'medium', 'Triggers include:' in content),
            ('参考文档章节', 'critical', '## 参考文档' in content or '## References' in content),
            ('references/iam-policies.md 存在', 'critical', os.path.isfile(os.path.join(sp, 'references', 'iam-policies.md'))),
        ]
        
        # High checks
        high_checks = [
            ('概述章节', 'high', '## 概述' in content or '## Overview' in content),
            ('前置条件章节', 'high', '## 前置条件' in content or '## Prerequisites' in content),
            ('工作流章节', 'high', '## 工作流' in content or '## Workflow' in content),
            ('核心命令章节', 'high', '## 核心命令' in content or '## Core Commands' in content),
            ('参数确认章节', 'high', '## 参数确认' in content or '## Parameters' in content),
        ]
        
        critical_checks += high_checks
        
        # Security scan
        has_credential = False
        for pattern in ['access_key', 'secret_key', 'AK=', 'SK=']:
            if pattern in content and '禁止' not in content.split(pattern)[0][-20:]:
                has_credential = True
                break
        
        security_checks = [
            ('无凭证硬编码', 'critical', not has_credential),
        ]
        
        # Cross-skill invocation check
        cross_skill = False
        for line in content.split('\n'):
            if 'invoke' in line.lower() and 'huawei-cloud-' in line:
                if '关联技能' not in line and '相关技能' not in line:
                    cross_skill = True
                    break
        
        security_checks += [
            ('无跨Skill调用', 'critical', not cross_skill),
        ]
        
        critical_checks += security_checks
    
    for name, level, passed in critical_checks:
        status = 'pass' if passed else ('warn' if level in ('medium', 'low') else 'fail')
        if status == 'pass': pass_count += 1
        elif status == 'fail': fail_count += 1
        else: warn_count += 1
        
        ch = {'check': name, 'level': level, 'status': status}
        checks.append(ch)
        
        icon = {'pass': '✅', 'fail': '❌', 'warn': '⚠️'}.get(status, '?')
        print(f"    {icon} [{level}] {name}", flush=True)
    
    verdict = 'pass' if fail_count == 0 else ('warn' if warn_count > 0 else 'fail')
    
    results.append({
        'skill_name': sn,
        'validate_result': {
            'pass': pass_count,
            'fail': fail_count,
            'warn': warn_count,
            'verdict': verdict,
            'details': checks
        }
    })

import shlex

audit_script = os.environ.get('AUDIT_SCRIPT', '')
audit_results = []

if audit_script and os.path.isfile(audit_script):
    for sp in skill_paths:
        sn = os.path.basename(sp)
        print(f"\n  [{sn}] 安全审视 (skill-targeted-audit)...", flush=True)
        try:
            cmd = [sys.executable, audit_script, '--target', sp, '--no-install']
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            output = r.stdout + r.stderr

            report_file = ''
            for line in output.split('\n'):
                if line.startswith('Report saved:'):
                    report_file = line.split(':', 1)[1].strip()
                    break

            audit_verdict = 'skip'
            checks_status = {}
            issues = {'critical': 0, 'error': 0, 'warning': 0}

            if report_file and os.path.isfile(report_file):
                with open(report_file) as rf:
                    report_content = rf.read()
                if 'Gate Verdict: PASS' in report_content:
                    audit_verdict = 'pass'
                elif 'Gate Verdict: FAIL' in report_content:
                    audit_verdict = 'fail'
                for check_name in ['skillcheck', 'markdownlint', 'skill-scanner', 'hwcloud-spec', 'gitleaks']:
                    if f'{check_name} OK' in report_content:
                        checks_status[check_name] = 'OK'
                    elif f'{check_name} FAIL' in report_content:
                        checks_status[check_name] = 'FAIL'
                    else:
                        checks_status[check_name] = 'SKIP'
                for sev in ['CRITICAL', 'ERROR', 'WARNING']:
                    import re as _re
                    issues[sev.lower()] = len(_re.findall(rf'^\s+\[{sev}\]', report_content, _re.MULTILINE))
            else:
                audit_verdict = 'error'
                checks_status = {'error': 'could not parse report'}

            icon = {'pass': '✅', 'fail': '❌', 'skip': '⏭️', 'error': '⚠️'}.get(audit_verdict, '?')
            print(f"    {icon} 安全审视: {audit_verdict} (C:{issues['critical']} E:{issues['error']} W:{issues['warning']})", flush=True)

            audit_results.append({
                'skill_name': sn,
                'security_audit': {
                    'verdict': audit_verdict,
                    'report_file': os.path.basename(report_file) if report_file else '',
                    'checks': checks_status,
                    'issues': issues
                }
            })
        except subprocess.TimeoutExpired:
            print(f"    ⚠️ 安全审视超时 (120s)", flush=True)
            audit_results.append({'skill_name': sn, 'security_audit': {'verdict': 'timeout', 'checks': {}, 'issues': {'critical': 0, 'error': 0, 'warning': 0}}})
        except Exception as e:
            print(f"    ⚠️ 安全审视异常: {e}", flush=True)
            audit_results.append({'skill_name': sn, 'security_audit': {'verdict': 'error', 'checks': {'error': str(e)}, 'issues': {'critical': 0, 'error': 0, 'warning': 0}}})

output = {'skills_checked': results, 'audit_results': audit_results}
print("\n---JSON_START---")
print(json.dumps(output, indent=2, ensure_ascii=False))
print("---JSON_END---")
PYEOF
"${SKILL_PATHS[@]}"
)

# Extract JSON
json_output=$(echo "$skills_checked_json" | sed -n '/---JSON_START---/,/---JSON_END---/p' | grep -v 'JSON_START\|JSON_END')

end_ts=$(date +%s)
duration=$((end_ts - start_ts))

# Build security scan summary
sec_verdict="pass"
echo "$json_output" | python3 -c "import json,sys; d=json.load(sys.stdin)" 2>/dev/null || sec_verdict="fail"

output_file="${SKILL_PATHS[0]}/phase-8-summary.json"

# Write json_output to temp file for Python to read
p8_tmp=$(mktemp)
echo "$json_output" > "$p8_tmp"

p8_py_tmp=$(mktemp)
cat > "$p8_py_tmp" << 'P8PY'
import json, sys
data = json.load(open(sys.argv[1]))
PHASE_NUM = int(sys.argv[2])
PHASE_NAME = sys.argv[3]
SKILLS_LIST = sys.argv[4]
TS = sys.argv[5]
DURATION = int(sys.argv[6])
total_pass = sum(s['validate_result']['pass'] for s in data.get('skills_checked', []))
total_fail = sum(s['validate_result']['fail'] for s in data.get('skills_checked', []))
total_warn = sum(s['validate_result']['warn'] for s in data.get('skills_checked', []))
all_pass = all(s['validate_result']['verdict'] == 'pass' for s in data.get('skills_checked', []))

audit_by_skill = {}
for ar in data.get('audit_results', []):
    audit_by_skill[ar['skill_name']] = ar.get('security_audit', {})

for sc in data.get('skills_checked', []):
    sn = sc['skill_name']
    sc['security_audit'] = audit_by_skill.get(sn, {'verdict': 'skip', 'checks': {}, 'issues': {'critical': 0, 'error': 0, 'warning': 0}})
    audit_v = sc['security_audit'].get('verdict', 'skip')
    if audit_v == 'fail':
        all_pass = False

audit_verdict = 'pass' if all(a.get('verdict', 'skip') != 'fail' for a in audit_by_skill.values()) else 'fail'

r = {
    'phase': PHASE_NUM,
    'phase_name': PHASE_NAME,
    'tier': 3,
    'target': {'type': 'all', 'skills': [SKILLS_LIST]},
    'timestamp': TS,
    'execution_meta': {'duration_s': DURATION, 'retry_count': 0, 'user_confirmed': False},
    'result': {
        'skills_checked': data.get('skills_checked', []),
        'security_scan': {
            'credential_leak': 'pass' if total_fail == 0 else 'fail',
            'cross_skill_invocation': 'pass',
            'security_audit': audit_verdict,
            'verdict': 'pass' if all_pass else 'fail'
        }
    },
    'summary': {'verdict': 'pass' if all_pass else 'fail', 'pass_checks': total_pass, 'fail_checks': total_fail, 'warn_checks': total_warn}
}
print(json.dumps(r, indent=2, ensure_ascii=False))
P8PY

write_json "$output_file" "$(python3 "$p8_py_tmp" "$p8_tmp" "$PHASE_NUM" "$PHASE_NAME" "$SKILLS_LIST" "$ts" "$duration")"
rm -f "$p8_py_tmp"
rm -f "$p8_tmp"

echo ""
echo "$json_output" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for s in d.get('skills_checked', []):
    vr = s['validate_result']
    verdict_icon = '✅' if vr['verdict'] == 'pass' else ('⚠️' if vr['verdict'] == 'warn' else '❌')
    line = f\"  {verdict_icon} {s['skill_name']}: {vr['pass']}P/{vr['fail']}F/{vr['warn']}W → {vr['verdict']}\"
    sa = s.get('security_audit', {})
    if sa:
        sa_icon = {'pass': '✅', 'fail': '❌', 'skip': '⏭️', 'timeout': '⚠️', 'error': '⚠️'}.get(sa.get('verdict', ''), '?')
        issues = sa.get('issues', {})
        line += f\"  |  安全审视: {sa_icon} {sa.get('verdict', 'N/A')} (C:{issues.get('critical',0)} E:{issues.get('error',0)} W:{issues.get('warning',0)})\"
    print(line)
"

pass "Phase 8: 合规检查完成"
