#!/usr/bin/env bash
# phase-7-final-report.sh — 最终报告
# 合并 Phase 0~8 的所有 JSON，输出综合测试报告
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/lib/utils.sh"
source "$SCRIPT_DIR/lib/chain-verify.sh"

PHASE_NUM=7
PHASE_NAME="final-report"

# Parse args
SKILLS_LIST=""
SKILL_PATHS=()
OUTPUT_DIR="reports"
skills_next=false
output_next=false
for arg in "$@"; do
  if $skills_next; then
    SKILLS_LIST="$arg"
    skills_next=false
  elif $output_next; then
    OUTPUT_DIR="$arg"
    output_next=false
  elif [[ "$arg" == --skills=* ]]; then
    SKILLS_LIST="${arg#--skills=}"
  elif [[ "$arg" == --output=* ]]; then
    OUTPUT_DIR="${arg#--output=}"
  elif [[ "$arg" == --skills ]]; then
    skills_next=true
  elif [[ "$arg" == --output ]]; then
    output_next=true
  elif [[ "$arg" =~ ^/ || "$arg" =~ ^\\. ]]; then
    SKILL_PATHS+=("$arg")
  fi
done
unset skills_next output_next

header "Phase ${PHASE_NUM}: 最终报告"

ts=$(timestamp)
start_ts=$(date +%s)

# Verify all phases exist
check_phase_deps "${SKILL_PATHS[0]}" 7 || exit 1

REPORT_DIR="${OUTPUT_DIR}/report-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$REPORT_DIR"

# Build consolidated report
# Write Python script to temp file
p9_py_tmp=$(mktemp)
cat > "$p9_py_tmp" << 'PYREPORT'
import json, os, sys
from datetime import datetime

skill_paths = sys.argv[1:]
skills_list = os.environ.get('SKILLS_LIST', '').split(',')

phases_summary = []
overall_pass = 0
overall_fail = 0
overall_skip = 0
total_test_cases = 0
total_test_pass = 0
total_test_fail = 0
total_test_skip = 0
all_manual_interventions = []
skills_tested = []
resources_created = 0
resources_cleaned = 0
resources_manual = 0
failures_detail = []
warnings = []

PHASE_NAMES = {
    0: 'install-check', 1: 'skill-analysis', 2: 'tech-research',
    3: 'test-case-generation', 4: 'test-execution',
    5: 'orchestration', 6: 'full-flow'
}
PHASE_COUNT = len(PHASE_NAMES)

# Collect phase summaries
for p in range(PHASE_COUNT):
    summary = {'phase': p, 'name': PHASE_NAMES.get(p, f'phase-{p}'), 'verdict': 'missing', 'duration_s': 0}
    
    for sp in skill_paths:
        pf = os.path.join(sp, f'phase-{p}-summary.json')
        if os.path.isfile(pf) and os.path.getsize(pf) > 0:
            try:
                with open(pf, encoding='utf-8') as f:
                    data = json.load(f)
                v = data.get('summary', {}).get('verdict', 'missing')
                d = data.get('execution_meta', {}).get('duration_s', 0)
            except (json.JSONDecodeError, UnicodeDecodeError):
                v = 'partial'
                d = 0
            
            # Prefer first skill's data
            if summary['verdict'] == 'missing':
                summary['verdict'] = v
                summary['duration_s'] = d
            elif v != 'missing' and summary['verdict'] == 'missing':
                summary['verdict'] = v
                summary['duration_s'] = d
            break
    
    phases_summary.append(summary)
    
    if summary['verdict'] == 'pass': overall_pass += 1
    elif summary['verdict'] == 'fail': overall_fail += 1
    elif summary['verdict'] == 'skipped': overall_skip += 1

# Collect test statistics and details from phase 4 of each skill
for sp in skill_paths:
    sn = os.path.basename(sp)
    p4f = os.path.join(sp, 'phase-4-summary.json')
    p5f = os.path.join(sp, 'phase-5-summary.json')
    
    skill_info = {'name': sn}
    
    # Phase 4 stats
    if os.path.isfile(p4f) and os.path.getsize(p4f) > 0:
        try:
            with open(p4f, encoding='utf-8') as f:
                p4 = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            p4 = {}
        stats = p4.get('result', {}).get('statistics', {})
        skill_info['phases_completed'] = 5  # Tier 1 phases (0-4)
        skill_info['test_cases'] = stats.get('total', 0)
        skill_info['pass'] = stats.get('pass', 0)
        skill_info['fail'] = stats.get('fail', 0)
        total_test_cases += stats.get('total', 0)
        total_test_pass += stats.get('pass', 0)
        total_test_fail += stats.get('fail', 0)
        total_test_skip += stats.get('skip', 0)
        
        # Collect failures
        for er in p4.get('result', {}).get('execution_results', []):
            if er.get('status') in ('fail', 'error'):
                failures_detail.append({
                    'phase': 4,
                    'tc_id': er.get('tc_id', ''),
                    'error': er.get('error', er.get('output_snippet', '')[:100]),
                    'recommendation': '检查命令参数或SDK版本'
                })
    else:
        skill_info['phases_completed'] = 0
    
    # Phase 5 stats
    if os.path.isfile(p5f) and os.path.getsize(p5f) > 0:
        try:
            with open(p5f, encoding='utf-8') as f:
                p5 = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            p5 = {}
        rsrc = p5.get('result', {})
        auto_c = len(rsrc.get('auto_cleaned', []))
        fail_c = len(rsrc.get('failed_cleanup', []))
        manual_c = len(rsrc.get('manual_cleanup_instructions', []))
        resources_created += len(rsrc.get('resources_to_clean', []))
        resources_cleaned += auto_c
        resources_manual += manual_c
        
        for m in rsrc.get('manual_cleanup_instructions', []):
            all_manual_interventions.append({
                'phase': 5,
                'resource_type': m.get('resource_type', ''),
                'resource_id': m.get('resource_id', ''),
                'steps': m.get('manual_steps', [])
            })
    
    skills_tested.append(skill_info)

# Collect warnings from various phases
for sp in skill_paths:
    p6f = os.path.join(sp, 'phase-6-summary.json')
    if os.path.isfile(p6f) and os.path.getsize(p6f) > 0:
        try:
            with open(p6f, encoding='utf-8') as f:
                p6 = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            p6 = {}
        conflicts = p6.get('result', {}).get('conflict_scan', {}).get('conflicts', [])
        for c in conflicts:
            warnings.append({
                'phase': 6,
                'severity': c.get('severity', 'medium'),
                'message': f"触发词冲突: {c.get('skill_a', '')} ↔ {c.get('skill_b', '')} — {c.get('trigger', '')[:50]}"
            })

total_duration = sum(p['duration_s'] for p in phases_summary if p['duration_s'])

# Environment info
env_info = {}
SKIP_HCLOUD = False
try:
    import subprocess
    r = subprocess.run(['python3', '--version'], capture_output=True, text=True, timeout=5)
    env_info['python_version'] = r.stdout.strip()
except Exception:
    env_info['python_version'] = 'unknown'

try:
    r = subprocess.run(['hcloud', '--version'] if not SKIP_HCLOUD else ['echo', 'N/A'], capture_output=True, text=True, timeout=5)
    env_info['hcloud_version'] = r.stdout.strip()[:50] if r.stdout else 'N/A'
except Exception:
    env_info['hcloud_version'] = 'N/A'

result = {
    'test_id': f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
    'environment': env_info,
    'phases_summary': phases_summary,
    'overall_statistics': {
        'total_phases': PHASE_COUNT,
        'phase_pass': overall_pass,
        'phase_fail': overall_fail,
        'phase_skipped': overall_skip,
        'total_duration_s': round(total_duration, 2),
        'test_cases_total': total_test_cases,
        'test_cases_pass': total_test_pass,
        'test_cases_fail': total_test_fail,
        'test_cases_skip': total_test_skip,
        'pass_rate': round(total_test_pass / total_test_cases * 100, 1) if total_test_cases > 0 else 0
    },
    'skills_tested': skills_tested,
    'resources_created': resources_created,
    'resources_cleaned': resources_cleaned,
    'resources_manual': resources_manual,
    'manual_interventions': all_manual_interventions,
    'failures_detail': failures_detail,
    'warnings': warnings,
    'html_report': '',
    'json_report': ''
}

# Write JSON report
report_dir = os.environ.get('REPORT_DIR', 'reports')
json_path = os.path.join(report_dir, 'test-report.json')
with open(json_path, 'w') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

result['json_report'] = json_path

# Generate Markdown summary
md = []
md.append("# 华为云 Skill 测试报告\n")
md.append(f"**测试ID:** {result['test_id']}  ")
md.append(f"**时间:** {datetime.now().isoformat()}  \n")
md.append("## 总体统计\n")
md.append(f"| 指标 | 值 |")
md.append(f"|------|----|")
md.append(f"| Phase通过 | {overall_pass}/{PHASE_COUNT} |")
md.append(f"| Phase失败 | {overall_fail}/{PHASE_COUNT} |")
md.append(f"| 测试用例总数 | {total_test_cases} |")
md.append(f"| 用例通过 | {total_test_pass} |")
md.append(f"| 用例失败 | {total_test_fail} |")
md.append(f"| 用例跳过 | {total_test_skip} |")
md.append(f"| 通过率 | {result['overall_statistics']['pass_rate']}% |")
md.append(f"| 总耗时 | {round(total_duration, 1)}s |\n")

md.append("## Phase 状态\n")
md.append("| Phase | 名称 | 结果 | 耗时 |")
md.append("|-------|------|------|------|")
for ps in phases_summary:
    icon = {'pass': '✅', 'fail': '❌', 'partial': '⚠️', 'skipped': '⏭️', 'downgraded': '🔄', 'missing': '⛔'}.get(ps['verdict'], '?')
    md.append(f"| {ps['phase']} | {ps['name']} | {icon} {ps['verdict']} | {ps['duration_s']}s |")

if failures_detail:
    md.append("\n## 失败详情\n")
    md.append("| Phase | 用例 | 错误 | 建议 |")
    md.append("|-------|------|------|------|")
    for f in failures_detail:
        md.append(f"| {f['phase']} | {f['tc_id']} | {f['error'][:60]} | {f['recommendation']} |")

if all_manual_interventions:
    md.append("\n## 需手动操作项\n")
    for m in all_manual_interventions:
        md.append(f"- **{m['resource_type']}** ({m['resource_id']}):")
        for s in m.get('steps', []):
            md.append(f"  - {s}")

if warnings:
    md.append("\n## 警告\n")
    for w in warnings[:5]:
        md.append(f"- [{w['severity']}] {w['message'][:80]}")

md_path = os.path.join(report_dir, 'test-report.md')
with open(md_path, 'w') as f:
    f.write('\n'.join(md))

result['markdown_report'] = md_path

print("\n---JSON_START---")
print(json.dumps(result, indent=2, ensure_ascii=False))
print("---JSON_END---")
PYREPORT

report=$(SKILLS_LIST="$SKILLS_LIST" REPORT_DIR="$REPORT_DIR" python3 "$p9_py_tmp" "${SKILL_PATHS[@]}")
rm -f "$p9_py_tmp"

json_output=$(echo "$report" | sed -n '/---JSON_START---/,/---JSON_END---/p' | grep -v 'JSON_START\|JSON_END')

end_ts=$(date +%s)
duration=$((end_ts - start_ts))

# Write Phase 9 output
output_file="${SKILL_PATHS[0]}/phase-${PHASE_NUM}-summary.json"
p9_tmp=$(mktemp)
echo "$json_output" > "$p9_tmp"
p9_wrap_tmp=$(mktemp)
cat > "$p9_wrap_tmp" << 'P9WRAP'
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding='utf-8'))
except (json.JSONDecodeError, UnicodeDecodeError, FileNotFoundError):
    data = {'overall_statistics': {'test_cases_total': 0, 'test_cases_fail': 0}, 'warnings': []}
PHASE_NUM = int(sys.argv[2])
PHASE_NAME = sys.argv[3]
SKILLS_LIST = sys.argv[4]
TS = sys.argv[5]
DURATION = int(sys.argv[6])
r = {
    'phase': PHASE_NUM,
    'phase_name': PHASE_NAME,
    'tier': 3,
    'target': {'type': 'all', 'skills': [SKILLS_LIST]},
    'timestamp': TS,
    'execution_meta': {'duration_s': DURATION, 'retry_count': 0, 'user_confirmed': False},
    'result': data,
    'summary': {'verdict': 'pass', 'pass_checks': data.get('overall_statistics', {}).get('test_cases_total', 0), 'fail_checks': data.get('overall_statistics', {}).get('test_cases_fail', 0), 'warn_checks': len(data.get('warnings', []))}
}
print(json.dumps(r, indent=2, ensure_ascii=False))
P9WRAP

write_json "$output_file" "$(python3 "$p9_wrap_tmp" "$p9_tmp" "$PHASE_NUM" "$PHASE_NAME" "$SKILLS_LIST" "$ts" "$duration")"
rm -f "$p9_wrap_tmp"
rm -f "$p9_tmp"

echo ""
echo "$json_output" | python3 -c "
import json, sys
d = json.load(sys.stdin)
s = d.get('overall_statistics', {})
print(f'  📊 统计总览:')
print(f'     Phase: {s.get(\"phase_pass\", 0)}/9 通过, {s.get(\"phase_fail\", 0)} 失败')
print(f'     用例: {s.get(\"test_cases_pass\", 0)}/{s.get(\"test_cases_total\", 0)} 通过 ({s.get(\"pass_rate\", 0)}%)')
print(f'     资源: 创建 {d.get(\"resources_created\", 0)}, 清理 {d.get(\"resources_cleaned\", 0)}, 需手动 {d.get(\"resources_manual\", 0)}')
print(f'     总耗时: {s.get(\"total_duration_s\", 0)}s')
print(f'     失败: {len(d.get(\"failures_detail\", []))} 项')
print(f'     警告: {len(d.get(\"warnings\", []))} 项')
print(f'')
print(f'  📁 报告已写入:')
print(f'     Markdown: {sys.argv[1]}/test-report.md')
print(f'     JSON: {sys.argv[1]}/test-report.json')
" "$REPORT_DIR"

pass "Phase ${PHASE_NUM}: 最终报告完成"
echo ""
header "🎉 三轨七阶测试全部完成"
