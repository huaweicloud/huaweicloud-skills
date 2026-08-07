#!/usr/bin/env bash
# phase-7-final-report.sh — 最终报告
# 合并 Phase 0~6 的所有 JSON，输出结构化报告（markdown + JSON）。
# 报告结构：先总结（TL;DR）→ 详细报告（per-phase，含该 phase 产生的用例和执行结果）→ 附件。
# 同 Phase 4 一样，产物写到 <skill>-test-files/reports/report-<ts>/。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/lib/utils.sh"
source "$SCRIPT_DIR/lib/chain-verify.sh"

PHASE_NUM=7
PHASE_NAME="final-report"

# Parse args
SKILLS_LIST=""
SKILL_PATHS=()
OUTPUT_DIR=""
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
  elif [[ "$arg" =~ ^/ || "$arg" =~ ^\. || "$arg" =~ ^[A-Za-z]:[/\\] ]]; then
    SKILL_PATHS+=("$arg")
  fi
done
unset skills_next output_next

header "Phase ${PHASE_NUM}: 最终报告"

ts=$(timestamp)
start_ts=$(date +%s)

# Verify all phases exist
check_phase_deps "${SKILL_PATHS[0]}" 7 || exit 1

# Default report dir is the test-files-dir/reports if --output not set
if [ -z "${OUTPUT_DIR:-}" ]; then
  REPORT_DIR="$(reports_dir "${SKILL_PATHS[0]}")/report-$(date +%Y%m%d-%H%M%S)"
else
  REPORT_DIR="${OUTPUT_DIR}/report-$(date +%Y%m%d-%H%M%S)"
fi
ensure_test_files_dir "${SKILL_PATHS[0]}" > /dev/null
mkdir -p "$REPORT_DIR"

# Build the consolidated report
p7_py_tmp=$(mktemp)
cat > "$p7_py_tmp" << 'PYREPORT'
import json, os, sys
from datetime import datetime

skill_paths = sys.argv[1:]
skills_list = os.environ.get('SKILLS_LIST', '').split(',')
report_dir = os.environ.get('REPORT_DIR', '.')

# Phase JSONs live in <skill>-test-files/phases/, not in the skill dir
def _phases_dir(skill_dir):
    parent = os.path.dirname(skill_dir)
    name = os.path.basename(skill_dir)
    return os.path.join(parent, f"{name}-test-files", "phases")

# Load all phase JSONs
PHASE_NAMES = {
    0: ('install-check', 'Install Check'),
    1: ('skill-analysis', 'Feature Extraction'),
    2: ('tech-research', 'Tech Research'),
    3: ('test-case-generation', 'Test Case Generation'),
    4: ('test-execution', 'Test Execution'),
    5: ('orchestration', 'Orchestration'),
    6: ('full-flow', 'Full Flow E2E'),
}

def load_phase(sp, p):
    pf = os.path.join(_phases_dir(sp), f'phase-{p}-summary.json')
    if not os.path.isfile(pf) or os.path.getsize(pf) == 0:
        return None
    try:
        with open(pf, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

# Build detail for each phase
def build_phase_0(pd):
    """Phase 0: install-check → directory integrity + install/uninstall/reinstall"""
    if not pd: return None
    r = pd.get('result', {})
    di = r.get('directory_integrity', {})
    checks = di.get('checks', {})
    install = r.get('install', {})
    uninstall = r.get('uninstall', {})
    reinstall = r.get('reinstall', {})
    return {
        'directory_integrity': {
            'pass': di.get('pass', False),
            'checks': checks,
        },
        'install': install,
        'uninstall': uninstall,
        'reinstall': reinstall,
    }

def build_phase_1(pd):
    """Phase 1: skill-analysis → metadata, commands, capabilities, resource_types"""
    if not pd: return None
    r = pd.get('result', {})
    return {
        'metadata': r.get('metadata', {}),
        'capabilities': r.get('capabilities', {}),
        'has_write_operations': r.get('has_write_operations', False),
        'resource_types': r.get('resource_types', []),
        'commands': r.get('commands', []),
        'triggers_count': len(r.get('metadata', {}).get('triggers', [])),
        'commands_count': len(r.get('commands', [])),
    }

def build_phase_2(pd):
    """Phase 2: tech-research → per-command CLI/SDK/API availability"""
    if not pd: return None
    r = pd.get('result', {})
    research = r.get('research', [])
    summary = r.get('summary', {})
    return {
        'research': research,
        'summary': summary,
    }

def build_phase_3(pd):
    """Phase 3: test-case-generation → functional + API cases"""
    if not pd: return None
    r = pd.get('result', {})
    return {
        'functional_cases': r.get('functional_cases', []),
        'api_cases': r.get('api_cases', []),
        'statistics': r.get('statistics', {}),
    }

def build_phase_4(pd):
    """Phase 4: test-execution → per-case results + manual items"""
    if not pd: return None
    r = pd.get('result', {})
    return {
        'execution_results': r.get('execution_results', []),
        'statistics': r.get('statistics', {}),
        'all_resources_changed': r.get('all_resources_changed', []),
        'manual_test_items': r.get('manual_test_items', []),
    }

def build_phase_5(pd):
    """Phase 5: orchestration → conflict scan + data flow + parallel load"""
    if not pd: return None
    r = pd.get('result', {})
    target_skills = pd.get('target', {}).get('skills', [])
    return {
        'skills_involved': target_skills,
        'mode': r.get('mode', 'unknown'),
        'conflict_scan': r.get('conflict_scan', {}),
        'data_flow_tests': r.get('data_flow_tests', []),
        'parallel_load_test': r.get('parallel_load_test', {}),
    }

def build_phase_6(pd):
    """Phase 6: full-flow → E2E scenario steps"""
    if not pd: return None
    r = pd.get('result', {})
    scenario = r.get('scenario', {})
    target_skills = pd.get('target', {}).get('skills', [])
    return {
        'skills_involved': target_skills,
        'mode': r.get('mode', 'unknown'),
        'scenario': scenario,
        'state_consistency': r.get('state_consistency', {}),
        'cleanup': r.get('cleanup', {}),
    }

PHASE_BUILDERS = {
    0: build_phase_0,
    1: build_phase_1,
    2: build_phase_2,
    3: build_phase_3,
    4: build_phase_4,
    5: build_phase_5,
    6: build_phase_6,
}

# Aggregate per skill
all_skills = []
for sp in skill_paths:
    sn = os.path.basename(sp)
    phases_detail = {}
    phases_summary = []
    for p in range(7):
        pd = load_phase(sp, p)
        name_en, name_zh = PHASE_NAMES[p]
        if pd is None:
            phases_summary.append({
                'phase': p, 'name': name_en, 'verdict': 'missing',
                'duration_s': 0, 'summary': '未运行 (chain verify 跳过或前置缺失)',
            })
            phases_detail[str(p)] = None
            continue
        meta = pd.get('execution_meta', {})
        summ = pd.get('summary', {})
        detail = PHASE_BUILDERS[p](pd)
        # Build per-phase one-line summary
        if p == 0:
            ds = detail or {}
            chk = ds.get('directory_integrity', {}).get('checks', {})
            ok = sum(1 for v in chk.values() if v)
            tot = len(chk)
            one_line = f"{ok}/{tot} 目录硬要求通过; install/uninstall/reinstall 完整循环"
        elif p == 1:
            ds = detail or {}
            one_line = f"提取 {ds.get('commands_count', 0)} 条命令, {ds.get('triggers_count', 0)} 个触发词, 写操作: {ds.get('has_write_operations', False)}"
        elif p == 2:
            ds = detail or {}
            s = ds.get('summary', {})
            one_line = f"CLI: {s.get('cli_available', 0)}, SDK: {s.get('sdk_available', 0)}, API: {s.get('api_available', 0)}, 不可用: {s.get('not_available', 0)}"
        elif p == 3:
            ds = detail or {}
            st = ds.get('statistics', {})
            one_line = f"生成 {st.get('total', 0)} 条用例 (功能 {st.get('functional', 0)} + API {st.get('api', 0)}); 写 {st.get('write_operations', 0)}, 高风险 {st.get('high_risk', 0)}"
        elif p == 4:
            ds = detail or {}
            st = ds.get('statistics', {})
            one_line = f"执行 {st.get('total', 0)} 条: {st.get('pass', 0)} pass / {st.get('fail', 0)} fail / {st.get('warn', 0)} warn / {st.get('error', 0)} error"
        elif p == 5:
            ds = detail or {}
            cs = ds.get('conflict_scan', {})
            confs = len(cs.get('conflicts', []))
            df = len(ds.get('data_flow_tests', []))
            one_line = f"模式: {ds.get('mode', '?')}; 冲突 {confs}, 数据流候选 {df}"
        elif p == 6:
            ds = detail or {}
            sc = ds.get('scenario', {})
            one_line = f"模式: {ds.get('mode', '?')}; 场景 '{sc.get('name', '?')}', {len(sc.get('steps', []))} 步"
        else:
            one_line = ''
        phases_summary.append({
            'phase': p, 'name': name_en, 'verdict': summ.get('verdict', 'unknown'),
            'duration_s': meta.get('duration_s', 0), 'summary': one_line,
        })
        phases_detail[str(p)] = detail
    all_skills.append({
        'name': sn,
        'skill_path': sp,
        'phases_summary': phases_summary,
        'phases_detail': phases_detail,
    })

# Build top-level summary
def verdict_icon(v):
    return {'pass': '✅', 'fail': '❌', 'partial': '⚠️', 'skipped': '⏭️', 'downgraded': '🔄', 'missing': '⛔'}.get(v, '?')

phases_pass = phases_partial = phases_fail = phases_skipped = phases_missing = 0
total_cases = total_pass = total_fail = total_warn = total_skip = total_error = 0
total_manual = 0
total_resources = 0
overall_verdict = 'pass'  # default

for skill in all_skills:
    for ps in skill['phases_summary']:
        v = ps['verdict']
        if v == 'pass': phases_pass += 1
        elif v == 'partial': phases_partial += 1
        elif v == 'fail': phases_fail += 1
        elif v == 'skipped': phases_skipped += 1
        elif v == 'missing': phases_missing += 1
    # Aggregate from phase 3 + phase 4 detail
    p3 = skill['phases_detail'].get('3')
    p4 = skill['phases_detail'].get('4')
    if p3:
        st = p3.get('statistics', {})
        total_cases += st.get('total', 0)
    if p4:
        st = p4.get('statistics', {})
        total_pass += st.get('pass', 0)
        total_fail += st.get('fail', 0)
        total_warn += st.get('warn', 0)
        total_skip += st.get('skip', 0)
        total_error += st.get('error', 0)
        total_manual += len(p4.get('manual_test_items', []))
        total_resources += len(p4.get('all_resources_changed', []))

# Compute overall verdict
if phases_fail > 0 or total_error > 0:
    overall_verdict = 'fail'
elif phases_partial > 0 or total_fail > 0 or phases_missing > 0:
    overall_verdict = 'partial'

pass_rate = round(total_pass / total_cases * 100, 1) if total_cases > 0 else 0

summary = {
    'verdict': overall_verdict,
    'verdict_label': {'pass': '✅ PASS', 'partial': '⚠️ PARTIAL', 'fail': '❌ FAIL'}.get(overall_verdict, overall_verdict),
    'phases_total': 7,
    'phases_pass': phases_pass,
    'phases_partial': phases_partial,
    'phases_fail': phases_fail,
    'phases_skipped': phases_skipped,
    'phases_missing': phases_missing,
    'test_cases_total': total_cases,
    'test_cases_pass': total_pass,
    'test_cases_fail': total_fail,
    'test_cases_warn': total_warn,
    'test_cases_skip': total_skip,
    'test_cases_error': total_error,
    'pass_rate': pass_rate,
    'manual_items_count': total_manual,
    'cloud_resources_changed': total_resources,
}

# Auto-generate key findings
findings = []
# Phase 0
for skill in all_skills:
    p0 = skill['phases_detail'].get('0')
    if p0:
        di = p0.get('directory_integrity', {})
        if not di.get('pass'):
            failed = [k for k, v in di.get('checks', {}).items() if not v]
            findings.append(f"⚠️ {skill['name']}: 目录完整性失败, 缺: {', '.join(failed)}")
        else:
            ok = sum(1 for v in di.get('checks', {}).values() if v)
            findings.append(f"✅ {skill['name']}: 4 项目录硬要求全部通过 ({ok}/4)")
# Phase 1
for skill in all_skills:
    p1 = skill['phases_detail'].get('1')
    if p1:
        n_cmd = p1.get('commands_count', 0)
        n_trig = p1.get('triggers_count', 0)
        w = p1.get('has_write_operations', False)
        if w:
            findings.append(f"⚠️ {skill['name']}: 含写操作命令 (Phase 4 需要 ALLOW_WRITES=1)")
        else:
            findings.append(f"✅ {skill['name']}: 纯只读, 提取 {n_cmd} 条命令 / {n_trig} 个触发词")
# Phase 4
for skill in all_skills:
    p4 = skill['phases_detail'].get('4')
    if p4:
        st = p4.get('statistics', {})
        if st.get('fail', 0) > 0:
            findings.append(f"❌ {skill['name']} Phase 4: {st.get('fail', 0)} 个用例失败 (查看下方失败归类)")
        if st.get('warn', 0) > 0:
            findings.append(f"⚠️ {skill['name']} Phase 4: {st.get('warn', 0)} 个用例需手工补业务数据 (见 manual_test_items)")
    else:
        findings.append(f"⏭️ {skill['name']} Phase 4: 未执行 (Phase 4 因 env-var 中无 HUAWEI_ACCESS_KEY/HUAWEI_SECRET_KEY 而退出 77；用户需带外设置环境变量后重跑)")

test_id = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
env_info = {
    'python_version': sys.version.split()[0] if sys.version else '',
}

# ===== Build JSON =====
result_json = {
    'test_id': test_id,
    'generated_at': datetime.now().isoformat(),
    'skills': all_skills,
    'summary': summary,
    'key_findings': findings,
    'environment': env_info,
    'report_dir': report_dir,
}

# ===== Build Markdown =====
md = []
md.append(f"# Huawei Cloud Skill Test Report\n")
md.append(f"**Test ID:** `{test_id}`  ")
md.append(f"**Generated:** {datetime.now().isoformat()}  ")
md.append(f"**Skills:** {', '.join(s['name'] for s in all_skills)}  ")
md.append(f"**Report dir:** `{report_dir}`  \n")

# === Section 1: Summary ===
md.append("## 📊 Summary (TL;DR)\n")
md.append(f"**Overall Verdict: {summary['verdict_label']}**\n")
md.append("| Metric | Value |")
md.append("|--------|-------|")
md.append(f"| Phases | {summary['phases_pass']} pass / {summary['phases_partial']} partial / {summary['phases_fail']} fail / {summary['phases_skipped']} skipped (of 7) |")
md.append(f"| Test Cases | total {summary['test_cases_total']} | pass {summary['test_cases_pass']} | fail {summary['test_cases_fail']} | warn {summary['test_cases_warn']} | skip {summary['test_cases_skip']} | error {summary['test_cases_error']} |")
md.append(f"| Pass Rate | {summary['pass_rate']}% |")
md.append(f"| Manual Items | {summary['manual_items_count']} (need real business data) |")
md.append(f"| Cloud Resources Changed | {summary['cloud_resources_changed']} (Phase 4 only) |\n")

# Skills Tested list — 列出本次测试涉及的所有 skill 及其角色
if all_skills:
    md.append("**Skills Tested:**\n")
    md.append("| # | Skill | Path |")
    md.append("|---|-------|------|")
    for i, s in enumerate(all_skills, 1):
        md.append(f"| {i} | `{s['name']}` | `{s['skill_path']}` |")
    md.append("")

if findings:
    md.append("**Key Findings:**\n")
    for f in findings:
        md.append(f"- {f}")
    md.append("")

# === Section 2: Per-Phase Detail ===
md.append("## 📋 Phase-by-Phase Detail\n")
for skill in all_skills:
    md.append(f"### Skill: `{skill['name']}`\n")
    md.append(f"_Path: `{skill['skill_path']}`_\n")

    for p in range(7):
        ps = skill['phases_summary'][p]
        name_en, name_zh = PHASE_NAMES[p]
        icon = verdict_icon(ps['verdict'])
        md.append(f"#### Phase {p} — {name_zh} (`{name_en}`)")
        md.append(f"**Verdict:** {icon} {ps['verdict']}  |  **Duration:** {ps['duration_s']}s")
        md.append(f"**Summary:** {ps['summary']}\n")

        detail = skill['phases_detail'].get(str(p))
        if detail is None:
            md.append(f"_此 phase 未运行 (chain 缺失或未触发)_\n")
            continue

        # Per-phase content
        if p == 0:
            di = detail.get('directory_integrity', {})
            checks = di.get('checks', {})
            md.append("**Directory integrity (4 项硬要求):**\n")
            md.append("| Check | Status |")
            md.append("|-------|--------|")
            for name, ok in checks.items():
                md.append(f"| `{name}` | {'✅' if ok else '❌'} |")
            md.append("")
            md.append("**Install / Uninstall / Reinstall:**\n")
            md.append("| Action | Status | Duration | Note |")
            md.append("|--------|--------|----------|------|")
            for label, key in [('Install', 'install'), ('Uninstall', 'uninstall'), ('Reinstall', 'reinstall')]:
                d = detail.get(key, {})
                s = d.get('status', '?')
                dur = d.get('duration_s', 0)
                note = d.get('reason', '') or d.get('existing', '')
                if note and not isinstance(note, str):
                    note = str(note)
                if s == 'skipped':
                    note = f"已存在, 跳过" if not note else note
                md.append(f"| {label} | {s} | {dur}s | {note} |")
            md.append("")

        elif p == 1:
            md.append("**Extracted metadata:**\n")
            md.append(f"- Triggers: {detail.get('triggers_count', 0)}")
            md.append(f"- Commands: {detail.get('commands_count', 0)}")
            md.append(f"- Resource types: {', '.join(detail.get('resource_types', [])) or '(none)'}")
            md.append(f"- Has write operations: **{detail.get('has_write_operations', False)}**\n")
            cmds = detail.get('commands', [])
            if cmds:
                md.append("**Commands extracted ({}):**\n".format(len(cmds)))
                md.append("| ID | Source | Description | Executor | W/R |")
                md.append("|----|--------|-------------|----------|-----|")
                for c in cmds:
                    wr = 'W' if c.get('is_write') else 'R'
                    md.append(f"| {c.get('id', '?')} | {(c.get('source', '?') or '?')[:30]} | {(c.get('description', '?') or '?')[:50]} | {c.get('executor', '?')} | {wr} |")
                md.append("")

        elif p == 2:
            s = detail.get('summary', {})
            research = detail.get('research', [])
            md.append("**Per-command availability:**\n")
            md.append(f"- CLI: **{s.get('cli_available', 0)}**/{len(research)}  |  SDK: {s.get('sdk_available', 0)}/{len(research)}  |  API: {s.get('api_available', 0)}/{len(research)}  |  Unavailable: {s.get('not_available', 0)}/{len(research)}")
            md.append("")
            if research:
                md.append("| ID | Recommended | CLI | SDK | API | Risk |")
                md.append("|----|-------------|-----|-----|-----|------|")
                for r in research:
                    cli = '✅' if r.get('cli', {}).get('available') else '❌'
                    sdk = '✅' if r.get('sdk', {}).get('available') else '❌'
                    api = '✅' if r.get('api', {}).get('available') else '❌'
                    md.append(f"| {r.get('cmd_id', '?')} | {r.get('recommended_executor', '?')} | {cli} | {sdk} | {api} | {r.get('risk_level', '?')} |")
                md.append("")

        elif p == 3:
            st = detail.get('statistics', {})
            func_cases = detail.get('functional_cases', [])
            api_cases = detail.get('api_cases', [])
            md.append("**Statistics:**\n")
            md.append(f"- Functional cases: **{st.get('functional', 0)}**")
            md.append(f"- API cases: {st.get('api', 0)}")
            md.append(f"- Write operations: {st.get('write_operations', 0)}")
            md.append(f"- High risk: {st.get('high_risk', 0)}")
            md.append(f"- Low risk: {st.get('low_risk', 0)}\n")
            all_cases = func_cases + api_cases
            if all_cases:
                md.append(f"**Test cases generated ({len(all_cases)}):**\n")
                md.append("| ID | Name | Type | Risk | Executor | Source |")
                md.append("|----|------|------|------|----------|--------|")
                for c in all_cases:
                    md.append(f"| {c.get('id', '?')} | {(c.get('name', '?') or '?')[:50]} | {c.get('type', '?')} | {c.get('risk_level', '?')} | {c.get('executor', '?')} | {(c.get('source', '?') or '?')[:25]} |")
                md.append("")

        elif p == 4:
            st = detail.get('statistics', {})
            results = detail.get('execution_results', [])
            manual = detail.get('manual_test_items', [])
            md.append("**Statistics:**\n")
            md.append(f"- Total: {st.get('total', 0)}  |  Pass: **{st.get('pass', 0)}**  |  Fail: **{st.get('fail', 0)}**  |  Warn: **{st.get('warn', 0)}**  |  Skip: {st.get('skip', 0)}  |  Error: {st.get('error', 0)}")
            md.append(f"- Pass rate: {st.get('pass_rate', 0)}%\n")

            if results:
                md.append(f"**Test case results ({len(results)}):**\n")
                md.append("| ID | Status | Duration | Error/Output |")
                md.append("|----|--------|----------|---------------|")
                for r in results:
                    s = r.get('status', '?')
                    icon = {'pass': '✅', 'fail': '❌', 'warn': '⚠️', 'skip': '⏭️', 'error': '💥'}.get(s, '?')
                    dur = r.get('duration_s', 0)
                    err = r.get('error') or r.get('output_snippet') or r.get('manual_test_hint', '')
                    if err:
                        # Strip ANSI codes
                        import re
                        err = re.sub(r'\x1b\[[0-9;]*m', '', err)
                        err = err.replace('\n', ' ')[:120]
                    md.append(f"| {r.get('tc_id', '?')} | {icon} {s} | {dur}s | {err} |")
                md.append("")

            # Categorize failures
            fails = [r for r in results if r.get('status') == 'fail']
            warns = [r for r in results if r.get('status') == 'warn']
            if fails:
                md.append(f"**Failures ({len(fails)}) — 需要修 SKILL.md / templates/test-defaults.json:**\n")
                # Group by error pattern
                from collections import Counter
                err_patterns = Counter()
                for f in fails:
                    err = f.get('error') or ''
                    import re
                    err = re.sub(r'\x1b\[[0-9;]*m', '', err)
                    # Extract key error phrase
                    m = re.search(r'\[USE_ERROR\]([^[\n]*)', err)
                    if m:
                        phrase = m.group(1).strip()[:60]
                    else:
                        phrase = err[:60]
                    err_patterns[phrase] += 1
                for phrase, count in err_patterns.most_common():
                    md.append(f"- _{count}×_ `{phrase}`")
                md.append("")
                md.append("**Affected cases:**\n")
                for f in fails:
                    md.append(f"- {f.get('tc_id', '?')}: {(f.get('name', '?') or '?')[:50]}")
                md.append("")

            if warns:
                md.append(f"**Warns ({len(warns)}) — 需要手工补业务数据:**\n")
                for w in warns:
                    md.append(f"- {w.get('tc_id', '?')}: {(w.get('name', '?') or '?')[:50]}")
                    if w.get('missing_params'):
                        md.append(f"  - 缺参: {', '.join(w.get('missing_params', []))}")
                    if w.get('manual_test_hint'):
                        md.append(f"  - 提示: {w.get('manual_test_hint', '')[:80]}")
                md.append("")

            if manual:
                md.append(f"**Manual test items ({len(manual)}) — 完整命令见 `phases/phase-4-summary.json` → `result.manual_test_items`**\n")

        elif p == 5:
            cs = detail.get('conflict_scan', {})
            conflicts = cs.get('conflicts', [])
            data_flows = detail.get('data_flow_tests', [])
            plt = detail.get('parallel_load_test', {})
            si = detail.get('skills_involved', [])
            if si:
                md.append(f"**Skills involved in this orchestration ({len(si)}):**")
                for s in si:
                    md.append(f"- `{s}`")
                md.append("")
            md.append(f"**Mode:** `{detail.get('mode', '?')}`\n")
            md.append(f"**Conflict scan:**")
            md.append(f"- Pairs checked: {cs.get('pairs_checked', 'N/A')}")
            md.append(f"- Conflicts: **{len(conflicts)}** (high: {sum(1 for c in conflicts if c.get('severity') == 'high')}, medium: {sum(1 for c in conflicts if c.get('severity') == 'medium')})")
            if 'internal_ambiguities' in cs:
                md.append(f"- Internal ambiguities: {len(cs.get('internal_ambiguities', []))}")
            if 'cycle_warnings' in cs:
                md.append(f"- Cycle warnings: {len(cs.get('cycle_warnings', []))}")
            md.append("")
            md.append(f"**Data flow candidates:** {len(data_flows)}")
            md.append(f"**Parallel load test:** {plt.get('verdict', 'N/A')} — {plt.get('detail', '')}\n")
            if conflicts:
                md.append("**Conflict details:**\n")
                md.append("| Severity | Skill A | Skill B | Trigger | Recommendation |")
                md.append("|----------|---------|---------|---------|----------------|")
                for c in conflicts[:20]:
                    md.append(f"| {c.get('severity', '?')} | {c.get('skill_a', '?')} | {c.get('skill_b', '?')} | {(c.get('trigger', '?') or '?')[:40]} | {(c.get('recommendation', '?') or '?')[:50]} |")
                md.append("")

        elif p == 6:
            sc = detail.get('scenario', {})
            state = detail.get('state_consistency', {})
            cleanup = detail.get('cleanup', {})
            si = detail.get('skills_involved', [])
            if si:
                md.append(f"**Skills involved in this E2E flow ({len(si)}):**")
                for s in si:
                    md.append(f"- `{s}`")
                md.append("")
            md.append(f"**Mode:** `{detail.get('mode', '?')}`\n")
            md.append(f"**Scenario:** {sc.get('name', '?')}")
            md.append(f"**Description:** {sc.get('description', '?')}")
            md.append(f"**Derived automatically:** {sc.get('derived_automatically', '?')}")
            md.append(f"**User confirmed:** {sc.get('user_confirmed', '?')}\n")
            steps = sc.get('steps', [])
            if steps:
                md.append(f"**Steps ({len(steps)}):**\n")
                md.append("| Seq | Action | Skill | Status | Output |")
                md.append("|-----|--------|-------|--------|--------|")
                for s in steps:
                    a = s.get('action', '?') or '?'
                    icon = {'pass': '✅', 'fail': '❌', 'skip': '⏭️'}.get(s.get('status', '?'), '?')
                    out = s.get('output', '') or ''
                    if out:
                        out = out.replace('\n', ' ')[:60]
                    md.append(f"| {s.get('seq', '?')} | {a[:50]} | {s.get('skill', '?')} | {icon} {s.get('status', '?')} | {out} |")
                md.append("")
            md.append(f"**State consistency:** {'✅' if state.get('pass') else '❌'} {state.get('detail', '')}")
            md.append(f"**Final state:** {state.get('final_state_summary', 'N/A')}\n")
            md.append(f"**Cleanup:** verdict={cleanup.get('verdict', '?')}, cleaned={cleanup.get('resources_cleaned', 0)}, failed={cleanup.get('resources_failed', 0)}, manual={len(cleanup.get('manual_required', []))}\n")

# === Section 3: Attachments ===
md.append("## 📎 Attachments\n")
for skill in all_skills:
    sn = skill['name']
    tfd = os.path.join(os.path.dirname(skill['skill_path']), f"{sn}-test-files")
    md.append(f"**Skill `{sn}` test artifacts:**")
    md.append(f"- Phase JSONs: `{tfd}/phases/phase-{{0..7}}-summary.json`")
    md.append(f"- Archived (old runs): `{tfd}/phases/archive/<ts>/`")
    md.append(f"- Reports history: `{tfd}/reports/`")
    md.append("")

# Write JSON
json_path = os.path.join(report_dir, 'test-report.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(result_json, f, indent=2, ensure_ascii=False)

# Write Markdown
md_path = os.path.join(report_dir, 'test-report.md')
with open(md_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(md))

print(f"\n  📁 Reports written:")
print(f"     JSON: {json_path}")
print(f"     MD:   {md_path}")
print(f"\n  📊 Summary:")
print(f"     Phases: {summary['phases_pass']} pass / {summary['phases_partial']} partial / {summary['phases_fail']} fail (of {summary['phases_total']})")
print(f"     Test cases: {summary['test_cases_total']} total, {summary['test_cases_pass']} pass ({summary['pass_rate']}%)")
print(f"     Manual items: {summary['manual_items_count']}")
print(f"     Verdict: {summary['verdict_label']}")
PYREPORT

REPORT_DIR="$REPORT_DIR" \
  python3 "$p7_py_tmp" "${SKILL_PATHS[@]}" 2>&1
rm -f "$p7_py_tmp"

# Write Phase 7 summary (links to the full report)
output_file="$(phases_dir "${SKILL_PATHS[0]}")/phase-${PHASE_NUM}-summary.json"
p7_tmp=$(mktemp)
cat > "$p7_tmp" <<EOF
{
  "phase": $PHASE_NUM,
  "phase_name": "$PHASE_NAME",
  "tier": 3,
  "target": {"type": "all", "skills": ["$SKILLS_LIST"]},
  "timestamp": "$ts",
  "execution_meta": {"duration_s": 0, "retry_count": 0, "user_confirmed": false},
  "result": {"report_dir": "$REPORT_DIR"},
  "summary": {"verdict": "pass", "pass_checks": 0, "fail_checks": 0, "warn_checks": 0}
}
EOF
write_json "$output_file" "$(cat "$p7_tmp")"
rm -f "$p7_tmp"

end_ts=$(date +%s)
duration=$((end_ts - start_ts))

echo ""
header "🎉 三轨八节测试全部完成"
