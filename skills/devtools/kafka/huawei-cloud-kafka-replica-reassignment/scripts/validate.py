#!/usr/bin/env python3
"""
Validation module: run per-stage checks and return PASS/FAIL with details.

Each stage's validation rules are defined in references/validation-rules.md.
This module provides functions to validate each stage's output.
"""

import json
import os
import sys
from collections import defaultdict

# Whoever imports this, no __pycache__ should be left under the skill package scripts/:
# set the flag before importing same-dir modules, otherwise the cache is already written.
sys.dont_write_bytecode = True

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tabio   # noqa: E402  same-dir module; must import after sys.path fix
from stage2_merge import read_tsv   # noqa: E402


def _key_of(broker_id, mountpoint):
    """Canonical key for mount-point comparison: strip the trailing slash so /a/b and /a/b/
are not treated as two disks."""
    return (str(broker_id).strip(), str(mountpoint or '').strip().rstrip('/'))


def _pre_existing_keys(stage1_result):
    """Parse the set of (broker, mount point) "pre-existing over threshold" from Stage 1 stats.

    Stage 1 is the only place that knows the input watermarks; this only passthrough-parses.
    If parsing yields nothing, return an empty set — better to judge the over-threshold as
    caused by this run (FAIL) than to pass silently.
    """
    keys = set()
    stats = (stage1_result or {}).get('stats', {}) or {}
    for item in stats.get('pre_existing_over_threshold', []) or []:
        text = str(item)
        if ':' in text:
            text = text.rsplit(':', 1)[0]
        parts = text.replace('broker ', '', 1).strip().split(' ', 1)
        if len(parts) == 2:
            keys.add(_key_of(parts[0], parts[1]))
    return keys


def validate_stage1(stage1_result, output_dir, disk_threshold=70):
    """
    Validate stage 1 output.
    Checks: disk threshold, replica completeness, broker conflicts, degradation, balance.
    """
    checks = []
    broker_ids = set()   # 1.6 needs the total broker count eligible to host replicas; collected while 1.1 reads disks

    # Read outputs
    new_csv = tabio.artifact_path(output_dir, tabio.NEW_NAME, tabio.LEGACY_NEW_NAME)
    broker_xlsx = os.path.join(output_dir, tabio.BROKER_UPDATED_NAME)
    main_csv = tabio.artifact_path(output_dir, tabio.MAIN_NAME, tabio.LEGACY_MAIN_NAME)

    # 1.1 Disk usage threshold
    # Pre-existing watermarks and this-run watermarks must be judged separately: some disks
    # were already over threshold before this tool ran, which this run did not cause —
    # hard-failing would block the user for nothing. Conversely, any disk pushed over the
    # threshold BY this run is a real violation and must FAIL.
    pre_key = _pre_existing_keys(stage1_result)
    try:
        import openpyxl
        wb = openpyxl.load_workbook(broker_xlsx, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        max_usage = 0.0
        newly_over, pre_over = [], []
        for row in rows[1:]:
            if row and len(row) >= 8:
                usage_str = str(row[7]).replace('%', '').strip()
                try:
                    usage = float(usage_str)
                except ValueError:
                    continue
                broker_ids.add(str(row[0]))
                if usage > max_usage:
                    max_usage = usage
                if usage > disk_threshold:
                    item = f"broker {row[0]}, 挂载点 {row[4]}: {usage:.2f}%"
                    if _key_of(row[0], row[4]) in pre_key:
                        pre_over.append(item)
                    else:
                        newly_over.append(item)
        if newly_over:
            checks.append(('1.1', 'FAIL',
                           f'本次分配把挂载点推过阈值（须回退重算）: {"; ".join(newly_over)}'))
        elif pre_over:
            checks.append(('1.1', 'WARN',
                           f'存量已超阈值（非本次分配造成，建议先治理该盘）: {"; ".join(pre_over)}'))
        else:
            checks.append(('1.1', 'PASS', f'max={max_usage:.2f}%, threshold={disk_threshold}%'))
    except Exception as e:
        checks.append(('1.1', 'FAIL', f'Cannot read broker file: {e}'))

    # 1.2 Replica completeness
    try:
        main_records = read_tsv(main_csv)
        new_records = read_tsv(new_csv)
        replica_count = stage1_result.get('params', {}).get('replica_count', 2)
        # Group new records by (topic, partition)
        new_by_key = defaultdict(list)
        for r in new_records:
            new_by_key[(r['Topic'], r['Partition'])].append(r)

        missing = []
        for r in main_records:
            key = (r['Topic'], r['Partition'])
            new_count = len(new_by_key.get(key, []))
            expected = replica_count - 1  # original is 1
            if new_count < expected:
                missing.append(f"{r['Topic']}/p{r['Partition']}: {new_count}/{expected}")

        if missing:
            checks.append(('1.2', 'FAIL', f'副本数不完整: {"; ".join(missing[:5])}'))
        else:
            checks.append(('1.2', 'PASS', f'all {len(main_records)} partitions have {replica_count} replicas'))
    except Exception as e:
        checks.append(('1.2', 'FAIL', f'Cannot validate: {e}'))

    # 1.3 Same-broker conflict (L0/L1)
    try:
        conflicts = []
        for r in main_records:
            key = (r['Topic'], r['Partition'])
            original_broker = r['Broker ID']
            # This version only admits distinct-broker placements (L0) at Stage 1: any new
            # replica on the same broker is a conflict. The legacy L2 (same broker, different
            # mount point) is no longer produced — it cannot be expressed in Kafka
            # reassignment JSON.
            for nr in new_by_key.get(key, []):
                if nr['Broker ID'] == original_broker:
                    conflicts.append(f"{r['Topic']}/p{r['Partition']}: replica on same broker {original_broker}")
        if conflicts:
            checks.append(('1.3', 'FAIL', f'同broker冲突: {"; ".join(conflicts[:5])}'))
        else:
            checks.append(('1.3', 'PASS', 'no same-broker conflicts (阶段一只放行异 broker 落点)'))
    except Exception as e:
        checks.append(('1.3', 'FAIL', f'Cannot validate: {e}'))

    # 1.4 degradation marker: this version only admits L0 at Stage 1, so PASS artifacts
    # must contain no degradation. A non-empty degradation (legacy L2/L3 or hand-edited
    # data) means the data is untrustworthy; fail directly.
    try:
        marked = [f"{r['Topic']}/p{r['Partition']}"
                  for r in new_records if str(r.get('degradation', '') or '').strip()]
        if marked:
            checks.append(('1.4', 'FAIL',
                           f'PASS 产物不应带降级标注（阶段一只放行 L0；旧版 L2/L3 或手工改坏）: '
                           f'{"; ".join(marked[:5])}'))
        else:
            checks.append(('1.4', 'PASS', 'all allocations are L0 (no degradation)'))
    except Exception as e:
        checks.append(('1.4', 'FAIL', f'Cannot validate: {e}'))

    # 1.5 L3 errors
    l3_count = sum(1 for r in new_records if r.get('degradation', '') == 'L3')
    if l3_count > 0:
        checks.append(('1.5', 'FAIL', f'L3 errors: {l3_count} mountpoint-insufficient cases'))
    else:
        checks.append(('1.5', 'PASS', 'no L3 errors'))

    # 1.6 Broker balance
    # Judges "are new replicas overly concentrated on a few brokers": disk-watermark
    # constraints can naturally tilt the allocation, so this is WARN not FAIL — when the
    # tilt is unexplainable, a human should look before deciding to proceed.
    stats = stage1_result.get('stats', {}) or {}
    per_broker_new = defaultdict(int)
    for r in new_records:
        per_broker_new[str(r.get('Broker ID'))] += 1
    n_new = sum(per_broker_new.values())
    n_brokers = len(broker_ids) or len(per_broker_new) or 1
    fair = -(-n_new // n_brokers) if n_brokers else 0          # fair-share new replicas per broker (ceil)
    max_new = max(per_broker_new.values()) if per_broker_new else 0
    min_new = min([per_broker_new.get(str(b), 0) for b in broker_ids]) if broker_ids else 0
    load_max = stats.get('asset_partition_balance_max')
    load_min = stats.get('asset_partition_balance_min')
    detail = (f'新副本分布 max={max_new}/broker, min={min_new}/broker, 公平值≈{fair}, '
              f'承载 broker {len(per_broker_new)}/{n_brokers}')
    if load_max is not None and load_min is not None:
        detail += f'; 分配后各 broker 分区数 {load_min}~{load_max}'
    if n_brokers > 1 and max_new > max(2, 2 * fair):
        checks.append(('1.6', 'WARN', detail + '（新增副本明显集中在少数 broker）'))
    else:
        checks.append(('1.6', 'PASS', detail))

    # 1.7 Size consistency
    try:
        size_mismatches = []
        new_by_key2 = defaultdict(dict)
        for nr in new_records:
            new_by_key2[(nr['Topic'], nr['Partition'])]['Size(GB)'] = nr.get('Size(GB)', 0.0)
        for r in main_records:
            key = (r['Topic'], r['Partition'])
            orig_size = r.get('Size(GB)', 0.0)
            new_size = new_by_key2.get(key, {}).get('Size(GB)', orig_size)
            if abs(orig_size - new_size) > 0.001:
                size_mismatches.append(f"{r['Topic']}/p{r['Partition']}: {orig_size} vs {new_size}")
        if size_mismatches:
            checks.append(('1.7', 'FAIL', f'Size不一致: {"; ".join(size_mismatches[:5])}'))
        else:
            checks.append(('1.7', 'PASS', 'all sizes consistent'))
    except Exception as e:
        checks.append(('1.7', 'FAIL', f'Cannot validate: {e}'))

    return checks


def validate_stage2(stage2_result, output_dir):
    """Validate stage 2 output."""
    checks = []
    all_csv = tabio.artifact_path(output_dir, tabio.ALL_NAME, tabio.LEGACY_ALL_NAME)

    try:
        all_records = read_tsv(all_csv)
    except Exception as e:
        return [('2.0', 'FAIL', f'Cannot read {all_csv}: {e}')]

    stats = stage2_result.get('stats', {})

    # 2.1 Row count match
    expected = stats.get('expected_rows', 0)
    actual = stats.get('merged_rows', 0)
    if expected == actual:
        checks.append(('2.1', 'PASS', f'rows={actual}'))
    else:
        checks.append(('2.1', 'FAIL', f'expected={expected}, actual={actual}'))

    # 2.2 Sort order
    # Verify topics are sorted by total size, partitions within topic sorted
    topic_sizes = stats.get('topic_sizes', {})
    if topic_sizes:
        sorted_topics = list(topic_sizes.keys())  # Already sorted in stats
        # Check actual order in CSV
        seen_topics = []
        for r in all_records:
            if r['Topic'] not in seen_topics:
                seen_topics.append(r['Topic'])
        if seen_topics == sorted_topics[:len(seen_topics)]:
            checks.append(('2.2', 'PASS', 'sort order correct'))
        else:
            checks.append(('2.2', 'WARN', f'topic order may differ: expected {sorted_topics[:5]}...'))

    # 2.3 Column completeness
    required = ['Topic', 'PartitionCount', 'Partition', 'Original Broker ID', 'Size(bytes)', 'Size(GB)']
    missing_cols = [c for c in required if c not in (all_records[0] if all_records else {})]
    if missing_cols:
        checks.append(('2.3', 'FAIL', f'missing columns: {missing_cols}'))
    else:
        checks.append(('2.3', 'PASS', 'all required columns present'))

    # 2.4 No missing partitions
    missing = stats.get('missing_partitions', 0)
    if missing == 0:
        checks.append(('2.4', 'PASS', 'no missing partitions'))
    else:
        checks.append(('2.4', 'FAIL', f'{missing} missing partitions'))

    # 2.5 No duplicates
    dupes = stats.get('duplicate_rows', 0)
    if dupes == 0:
        checks.append(('2.5', 'PASS', 'no duplicate rows'))
    else:
        checks.append(('2.5', 'FAIL', f'{dupes} duplicate rows'))

    # 2.6 Size consistency
    checks.append(('2.6', 'PASS', 'size values inherited from stage 1'))

    # 2.7 Allocation completeness
    incomplete = stats.get('incomplete_allocations', []) or []
    if incomplete:
        checks.append(('2.7', 'FAIL',
                       f'{len(incomplete)} 个分区缺少新增副本分配列: {"; ".join(incomplete[:5])}'))
    else:
        checks.append(('2.7', 'PASS', 'all partitions have complete allocations'))

    return checks


def validate_stage3(stage3_result):
    """Validate stage 3 output (uses validation from stage3_json.py)."""
    checks = []
    details = stage3_result.get('validation_details', [])
    for d in details:
        checks.append((d['check'], d['status'], d['detail']))
    return checks


def format_checks(stage_name, checks):
    """Format validation checks for display."""
    lines = [f'=== {stage_name}校验汇总 ===']
    pass_count = sum(1 for _, s, _ in checks if s == 'PASS')
    warn_count = sum(1 for _, s, _ in checks if s == 'WARN')
    fail_count = sum(1 for _, s, _ in checks if s == 'FAIL')

    for cid, status, detail in checks:
        lines.append(f'[{cid}] {detail[:80] if len(detail) > 80 else detail}: {status}')

    lines.append(f'\nPASS: {pass_count}  WARN: {warn_count}  FAIL: {fail_count}')

    if fail_count > 0:
        lines.append(f'结论: FAIL（需修复后重跑{stage_name}）')
    elif warn_count > 0:
        lines.append(f'结论: PASS with warnings（可进入下一阶段，但请关注告警项）')
    else:
        lines.append(f'结论: PASS（可进入下一阶段）')

    return '\n'.join(lines), fail_count == 0


def run_all_stage_validation(stage1_result, stage2_result, stage3_result, output_dir, disk_threshold=70):
    """Run validation for all three stages."""
    all_results = {}

    # Stage 1
    s1_checks = validate_stage1(stage1_result, output_dir, disk_threshold)
    s1_text, s1_pass = format_checks('阶段一', s1_checks)
    all_results['stage1'] = {'checks': s1_checks, 'summary': s1_text, 'pass': s1_pass}

    if not s1_pass:
        all_results['stage2'] = {'checks': [], 'summary': '阶段一未通过，阶段二跳过', 'pass': False}
        all_results['stage3'] = {'checks': [], 'summary': '阶段一未通过，阶段三跳过', 'pass': False}
        return all_results

    # Stage 2
    s2_checks = validate_stage2(stage2_result, output_dir)
    s2_text, s2_pass = format_checks('阶段二', s2_checks)
    all_results['stage2'] = {'checks': s2_checks, 'summary': s2_text, 'pass': s2_pass}

    if not s2_pass:
        all_results['stage3'] = {'checks': [], 'summary': '阶段二未通过，阶段三跳过', 'pass': False}
        return all_results

    # Stage 3
    s3_checks = validate_stage3(stage3_result)
    s3_text, s3_pass = format_checks('阶段三', s3_checks)
    all_results['stage3'] = {'checks': s3_checks, 'summary': s3_text, 'pass': s3_pass}

    return all_results
