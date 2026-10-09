#!/usr/bin/env python3
"""
Stage 3: convert the merged master table topic_all.xlsx to Kafka partition reassignment JSON.

Supports multiple splitting strategies:
  - size_10g: >threshold per-topic files, rest in common file
  - topic_count: batch N topics per file
  - single_file: everything in one file
  - per_topic: one file per topic
  - custom: user-defined combination strategy (JSON config)
"""

import argparse
import json
import os
import re
import sys

from collections import defaultdict

# The skill package may be read-only after install, and no compile cache belongs in it:
# disable bytecode writing so execution never creates __pycache__ under scripts/.
sys.dont_write_bytecode = True

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tabio   # noqa: E402  same-dir module; must import after sys.path fix


def read_tsv(path):
    """Read a table (xlsx / TSV) into list[dict]; numeric-looking values become int / float."""
    return tabio.read_records(path)


def detect_replica_count(headers):
    """Detect replica count from CSV headers."""
    alloc_count = 0
    for h in headers:
        if h.startswith('Allocation Broker ID') or (h == 'Allocation Broker ID'):
            alloc_count += 1
    return 1 + alloc_count  # original + allocations


def row_to_partition_entry(row, replica_count):
    """Convert a CSV row to a JSON partition entry."""
    # Original broker
    original_broker = row.get('Original Broker ID', 0)

    # Get allocation brokers and paths
    alloc_brokers = []
    alloc_paths = []

    if replica_count == 2:
        alloc_brokers.append(row.get('Allocation Broker ID', 0))
        alloc_paths.append(row.get('Path', ''))  # Second Path column
        # In our CSV format for replica_count=2:
        # columns: Original Broker ID, Path, Allocation Broker ID, Path
        # The second 'Path' is the allocation path
        # We need to handle this carefully - read by position
    else:
        for i in range(1, replica_count):
            bid = row.get(f'Allocation Broker ID {i}', 0)
            path = row.get(f'Allocation Path {i}', '')
            alloc_brokers.append(bid)
            alloc_paths.append(path)

    # Build replicas list: [original, alloc1, alloc2, ...]
    replicas = [original_broker] + alloc_brokers

    # Build log_dirs: ["any", path1+/kafka-logs, path2+/kafka-logs, ...]
    log_dirs = ['any']
    for p in alloc_paths:
        if p and not p.endswith('/kafka-logs'):
            log_dirs.append(p.rstrip('/') + '/kafka-logs')
        else:
            log_dirs.append(p)

    return {
        'topic': str(row.get('Topic', '')),
        'partition': int(row.get('Partition', 0)),
        'replicas': replicas,
        'log_dirs': log_dirs,
    }


def row_to_partition_entry_v2(row, headers, replica_count):
    """Convert a CSV row to a JSON partition entry using positional headers."""
    # For replica_count=2:
    # headers: Topic, PartitionCount, Partition, Original Broker ID, Path,
    #          Allocation Broker ID, Path, Size(bytes), Size(GB)
    # Original broker is at index 3, original path at 4
    # Allocation broker at 5, allocation path at 6

    original_broker = 0
    alloc_brokers = []
    alloc_paths = []

    if replica_count == 2:
        original_broker = row.get('Original Broker ID', 0)
        # Find the allocation columns - they might be named differently
        # Try 'Allocation Broker ID' and the second 'Path'
        alloc_brokers.append(row.get('Allocation Broker ID', 0))
        # The second Path column - we need to find it by position
        # Since dict keys are unique, the second 'Path' overwrites the first
        # So 'Path' in row actually holds the LAST Path value = allocation path
        alloc_paths.append(row.get('Path', ''))
        # But wait - the original path is also 'Path'. We need to handle this.
        # In read_tsv, duplicate headers cause the later one to overwrite.
        # So 'Path' = allocation path (the last one).
        # We need the original path too. Let's handle this in the caller.
    else:
        original_broker = row.get('Original Broker ID', 0)
        for i in range(1, replica_count):
            alloc_brokers.append(row.get(f'Allocation Broker ID {i}', 0))
            alloc_paths.append(row.get(f'Allocation Path {i}', ''))

    replicas = [original_broker] + alloc_brokers

    log_dirs = ['any']
    for p in alloc_paths:
        if p and not p.endswith('/kafka-logs'):
            log_dirs.append(p.rstrip('/') + '/kafka-logs')
        else:
            log_dirs.append(p)

    return {
        'topic': str(row.get('Topic', '')),
        'partition': int(row.get('Partition', 0)),
        'replicas': [int(r) for r in replicas],
        'log_dirs': log_dirs,
    }


def read_tsv_with_positions(path):
    """Read a table and keep column positions (xlsx / TSV both go through tabio; legacy duplicate-header fallback parsing lives in rows_to_entries)."""
    return tabio.read_table(path)


def rows_to_entries(headers, rows, replica_count):
    """Convert positional rows to partition entries."""
    # Resolve column positions by name: prefer explicit names (Original Path / Allocation
    # Path N); a legacy merged table has two same-named Path columns that can only be paired
    # by occurrence order, which the new headers no longer require.
    idx = {'topic': None, 'partition': None, 'original_broker': None,
           'original_path': None, 'size_gb': None, 'degradation': None}
    alloc_cols = []          # [[broker column, path column], ...]
    for i, h in enumerate(headers):
        if h == 'Topic' and idx['topic'] is None:
            idx['topic'] = i
        elif h == 'Partition' and idx['partition'] is None:
            idx['partition'] = i
        elif h == 'Original Broker ID':
            idx['original_broker'] = i
        elif h == 'Original Path':
            idx['original_path'] = i
        elif h == 'degradation':
            idx['degradation'] = i
        elif h == 'Size(GB)':
            idx['size_gb'] = i
        elif h.startswith('Allocation Broker ID'):
            alloc_cols.append([i, None])
        elif h.startswith('Allocation Path'):
            if alloc_cols and alloc_cols[-1][1] is None:
                alloc_cols[-1][1] = i
        elif h == 'Path':
            # Legacy headers: the first Path is the original replica dir; the rest are paired to Allocation Broker ID by occurrence order
            if idx['original_path'] is None:
                idx['original_path'] = i
            elif alloc_cols and alloc_cols[-1][1] is None:
                alloc_cols[-1][1] = i

    def cell(row, col):
        return row[col] if col is not None and col < len(row) else ''

    entries = []
    for row in rows:
        topic = cell(row, idx['topic'])
        partition = int(cell(row, idx['partition']) or 0)
        original_broker = int(cell(row, idx['original_broker']) or 0)
        original_path = cell(row, idx['original_path'])

        alloc_brokers = []
        alloc_paths = []
        for bid_idx, path_idx in alloc_cols:
            alloc_brokers.append(int(cell(row, bid_idx) or 0))
            alloc_paths.append(cell(row, path_idx))

        replicas = [original_broker] + alloc_brokers

        log_dirs = ['any']
        for p in alloc_paths:
            if p and not p.endswith('/kafka-logs'):
                log_dirs.append(p.rstrip('/') + '/kafka-logs')
            else:
                log_dirs.append(p)

        try:
            size_gb = float(cell(row, idx['size_gb']) or 0)
        except (ValueError, TypeError):
            size_gb = 0.0

        entries.append({
            'topic': str(topic),
            'partition': partition,
            'replicas': replicas,
            'log_dirs': log_dirs,
            '_size_gb': size_gb,
            '_original_path': original_path,
            '_degradation': cell(row, idx['degradation']).strip(),
        })

    return entries

def _num(value, default):
    # CLI passes strings, programmatic callers may pass numbers, and the custom strategy is
    # a dict. Normalize to numbers here before comparing: otherwise float > str raises, or a
    # string comparison silently produces the wrong grouping.
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)

def split_entries(entries, strategy, strategy_param, replica_count):
    """
    Split entries into groups based on the strategy.

    Returns: list of (filename, entries_list) tuples.
    """
    # Group entries by topic
    topics = defaultdict(list)
    topic_order = []
    for e in entries:
        t = e['topic']
        if t not in topics:
            topic_order.append(t)
        topics[t].append(e)

    # Calculate per-topic max single-partition size
    topic_max_size = {}
    for t, ents in topics.items():
        topic_max_size[t] = max(e['_size_gb'] for e in ents)

    result = []  # list of (filename, entries)

    if strategy == 'single_file':
        result.append(('all_partitions.json', entries))

    elif strategy == 'per_topic':
        for t in topic_order:
            result.append((f'{t}.json', topics[t]))

    elif strategy == 'size_10g':
        threshold = _num(strategy_param, 10)
        big_topics = []
        small_entries = []
        seq = 2
        for t in topic_order:
            if topic_max_size[t] > threshold:
                fname = f'{seq}{t}.json'
                result.append((fname, topics[t]))
                big_topics.append(t)
                seq += 1
            else:
                small_entries.extend(topics[t])
        if small_entries:
            result.append(('1common.json', small_entries))

    elif strategy == 'topic_count':
        n = int(_num(strategy_param, 10))
        batch = []
        batch_num = 1
        for i, t in enumerate(topic_order):
            batch.extend(topics[t])
            if (i + 1) % n == 0:
                result.append((f'batch_{batch_num}.json', batch))
                batch = []
                batch_num += 1
        if batch:
            result.append((f'batch_{batch_num}.json', batch))

    elif strategy == 'custom':
        # Custom strategy: strategy_param is a JSON dict with rules
        # Example: {"big_size": 10, "big_per_file": "per_topic", "small_batch": 10}
        config = strategy_param if isinstance(strategy_param, dict) else json.loads(strategy_param)
        big_size = config.get('big_size', 10)
        small_batch = config.get('small_batch', 10)

        big_topics = []
        small_entries = []
        seq = 2
        for t in topic_order:
            if topic_max_size[t] > big_size:
                result.append((f'{seq}{t}.json', topics[t]))
                seq += 1
            else:
                small_entries.extend(topics[t])

        # Batch small entries by topic_count
        if small_entries:
            small_topics = [t for t in topic_order if topic_max_size[t] <= big_size]
            batch = []
            batch_num = 1
            for i, t in enumerate(small_topics):
                batch.extend(topics[t])
                if (i + 1) % small_batch == 0:
                    result.append((f'small_batch_{batch_num}.json', batch))
                    batch = []
                    batch_num += 1
            if batch:
                result.append((f'small_batch_{batch_num}.json', batch))

    else:
        # Default to size_10g
        return split_entries(entries, 'size_10g', strategy_param, replica_count)

    return result


def write_json_files(file_groups, output_dir):
    """Write each group to a JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    written = []
    for filename, ents in file_groups:
        # Defense in depth: even if the pre-check slipped, never write outside the output directory; a slip is a hard failure.
        if not _path_inside(output_dir, filename):
            raise ValueError('refusing to write outside output dir: %r' % filename)
        # Clean entries (remove internal _size_gb field)
        clean = []
        for e in ents:
            clean_e = {
                'topic': e['topic'],
                'partition': e['partition'],
                'replicas': e['replicas'],
                'log_dirs': e['log_dirs'],
            }
            clean.append(clean_e)

        data = {'partitions': clean, 'version': 1}
        path = os.path.join(output_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        written.append(path)
    return written


# ---- Filename security boundary ----
# Topic names come from user-uploaded Excel files (untrusted input); per_topic / size_10g /
# custom embed topic names directly into file names. Kafka only allows [A-Za-z0-9._-] by
# default and forbids '.' / '..' as a complete topic name (max length 249), so validate
# against the same whitelist before writing, then run a realpath containment check to ensure
# the file stays inside the output directory. Invalid names fail the stage
# (INVALID_TOPIC_NAME) with no file written; names are never silently rewritten — rewriting
# would break the topic-to-file mapping and hide data problems.
TOPIC_NAME_MAX = 249
_TOPIC_NAME_RE = re.compile(r'^[A-Za-z0-9._-]+$')
_FILENAME_SAFE_RE = re.compile(r'^[A-Za-z0-9._-]+\.json$')


def safe_topic_name(topic):
    """Validate whether a topic name can safely be used as a file name. Returns (ok, reason)."""
    if not isinstance(topic, str) or not topic:
        return False, 'topic 名为空'
    if topic in ('.', '..'):
        return False, 'topic 名禁止为 . 或 ..'
    if len(topic) > TOPIC_NAME_MAX:
        return False, 'topic 名超过 Kafka 上限 %d 字符' % TOPIC_NAME_MAX
    if not _TOPIC_NAME_RE.match(topic):
        return False, 'topic 名含非法字符（仅允许 [A-Za-z0-9._-]）: %r' % (topic[:40],)
    return True, ''


def _path_inside(base_dir, filename):
    """realpath containment check: filename joined to base_dir must stay inside base_dir.

    The whitelist charset already blocks most path traversal (/ \\ .. are not allowed),
    so this layer is defense in depth: even if a future strategy builds an unexpected
    name, it can never be written outside the output directory.
    """
    base_real = os.path.realpath(base_dir)
    target_real = os.path.realpath(os.path.join(base_dir, filename))
    try:
        return os.path.commonpath([base_real, target_real]) == base_real
    except ValueError:   # different drives / no common path computable
        return False


def validate_json_files(file_paths, replica_count, expected_entries, l2_info=None):
    """Validate generated JSON files. Returns list of (check_id, status, detail)."""
    results = []
    all_entries = []
    total_partitions = 0

    for fp in file_paths:
        fname = os.path.basename(fp)
        # 3.1 JSON syntax
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            results.append(('3.1', 'FAIL', f'{fname}: JSON syntax error: {e}'))
            continue
        results.append(('3.1', 'PASS', f'{fname}: valid JSON'))

        # 3.2 Top-level structure
        if 'partitions' not in data or not isinstance(data['partitions'], list):
            results.append(('3.2', 'FAIL', f'{fname}: missing partitions array'))
            continue
        if data.get('version') != 1:
            results.append(('3.2', 'FAIL', f'{fname}: version != 1'))
            continue
        results.append(('3.2', 'PASS', f'{fname}: structure OK'))

        # 3.3-3.6 Check each partition entry
        for i, p in enumerate(data['partitions']):
            # 3.3 Required fields
            for field in ('topic', 'partition', 'replicas', 'log_dirs'):
                if field not in p:
                    results.append(('3.3', 'FAIL', f'{fname}[{i}]: missing field {field}'))
                    break
            else:
                results.append(('3.3', 'PASS', f'{fname}[{i}]: all fields present'))

            # 3.4 one partition's replicas must not contain duplicate broker IDs.
            # Kafka reassignment JSON cannot express "same broker, different mount point":
            # log_dirs can only name directories for existing replicas, and duplicate
            # brokers in replicas are rejected by Kafka. An older version granted an L2
            # exception (PASS(L2-EXCEPTION)), but such JSON fails on submission, i.e.
            # delivery of an unexecutable plan; this version fails them all, adding an
            # explanation when the entry carries a degradation marker.
            replicas = p.get('replicas', [])
            log_dirs = p.get('log_dirs', [])
            if len(replicas) != len(set(replicas)):
                dup = sorted({int(r) for r in set(replicas) if replicas.count(r) > 1})
                hint = ''
                if l2_info and (p.get('topic'), p.get('partition')) in l2_info:
                    hint = ('（该分区带 degradation=L2 标注：同 broker 不同挂载点无法在 '
                            'Kafka reassignment JSON 中表达，阶段一应对此场景阻断 '
                            'NO_OTHER_BROKER，请勿直接提交本 JSON）')
                results.append(('3.4', 'FAIL',
                                f'{fname}[{i}]: duplicate broker in replicas {replicas}'
                                f' (dup={dup}){hint}'))
            else:
                results.append(('3.4', 'PASS', f'{fname}[{i}]: no duplicate replicas'))

            # 3.5 replicas length
            if len(replicas) != replica_count:
                results.append(('3.5', 'FAIL', f'{fname}[{i}]: replicas len={len(replicas)}, expected={replica_count}'))
            else:
                results.append(('3.5', 'PASS', f'{fname}[{i}]: replicas length OK'))

            # 3.6 log_dirs length
            log_dirs = p.get('log_dirs', [])
            if len(log_dirs) != replica_count:
                results.append(('3.6', 'FAIL', f'{fname}[{i}]: log_dirs len={len(log_dirs)}, expected={replica_count}'))
            else:
                results.append(('3.6', 'PASS', f'{fname}[{i}]: log_dirs length OK'))

            # 3.10 log_dirs format
            if log_dirs and log_dirs[0] != 'any':
                results.append(('3.10', 'FAIL', f'{fname}[{i}]: log_dirs[0]={log_dirs[0]}, expected "any"'))
            else:
                ok = all(ld.endswith('/kafka-logs') or ld == 'any' for ld in log_dirs)
                if ok:
                    results.append(('3.10', 'PASS', f'{fname}[{i}]: log_dirs format OK'))
                else:
                    results.append(('3.10', 'FAIL', f'{fname}[{i}]: log_dirs format error: {log_dirs}'))

            all_entries.append((p.get('topic'), p.get('partition')))
            total_partitions += 1

    # 3.7 Total partition count
    if total_partitions != expected_entries:
        results.append(('3.7', 'FAIL', f'Total partitions={total_partitions}, expected={expected_entries}'))
    else:
        results.append(('3.7', 'PASS', f'Total partitions={total_partitions} matches expected'))

    # 3.8 No missing/duplicate
    unique_keys = set(all_entries)
    if len(unique_keys) != len(all_entries):
        results.append(('3.8', 'FAIL', f'Duplicate entries: {len(all_entries) - len(unique_keys)}'))
    elif len(unique_keys) != expected_entries:
        results.append(('3.8', 'FAIL', f'Missing entries: {expected_entries - len(unique_keys)}'))
    else:
        results.append(('3.8', 'PASS', f'All {len(unique_keys)} entries unique and complete'))

    # 3.9 File naming (basic check)
    for fp in file_paths:
        fname = os.path.basename(fp)
        if fname.endswith('.json'):
            results.append(('3.9', 'PASS', f'{fname}: .json extension OK'))
        else:
            results.append(('3.9', 'FAIL', f'{fname}: missing .json extension'))

    return results


def run(all_csv_path, output_dir, replica_count=2, strategy='size_10g', strategy_param=10):
    """Main entry point for stage 3."""
    os.makedirs(output_dir, exist_ok=True)

    headers, rows = read_tsv_with_positions(all_csv_path)
    if not rows:
        return {'status': 'FAIL', 'error': f'No data in {all_csv_path}'}

    # Auto-detect replica count if not specified
    if replica_count is None:
        replica_count = detect_replica_count(headers)

    # Convert rows to partition entries
    entries = rows_to_entries(headers, rows, replica_count)

    # Pre-check C: topic-name safety. per_topic / size_10g / custom embed topic names into
    # file names; topic names come from user-uploaded Excel (untrusted input), so validate
    # against the whitelist before writing (Kafka legal names [A-Za-z0-9._-], no . / ..,
    # max 249); invalid names fail immediately and no file is written.
    bad_topics = []
    seen_topic_order = []
    for e in entries:
        t = e['topic']
        if t in seen_topic_order:
            continue
        seen_topic_order.append(t)
        ok, reason = safe_topic_name(t)
        if not ok:
            bad_topics.append('%r: %s' % (t, reason))
    if bad_topics:
        return {
            'status': 'FAIL',
            'stage': 3,
            'reason': 'INVALID_TOPIC_NAME',
            'message': 'topic 名不能安全用作文件名（仅允许 [A-Za-z0-9._-]，禁 . / .. / 路径分隔符）：%s。'
                       '已停止，未写任何 JSON 文件。' % '; '.join(bad_topics[:10]),
            'inputs': [all_csv_path],
            'outputs': [],
            'params': {'replica_count': replica_count,
                       'json_strategy': strategy,
                       'json_strategy_param': strategy_param},
            'stats': {'total_entries': len(entries), 'files_generated': 0,
                      'validation_pass': 0, 'validation_fail': 1,
                      'unsafe_topic_names': bad_topics},
            'validation_details': [{'check': '3.9', 'status': 'FAIL',
                                    'detail': '不安全 topic 名: %s' % '; '.join(bad_topics[:10])}],
        }

    # Split into files based on strategy
    file_groups = split_entries(entries, strategy, strategy_param, replica_count)

    # Pre-check A: any partition missing a new-replica allocation (an empty string in
    # log_dirs) fails immediately with the partition named, instead of letting downstream
    # log_dirs validation report an obscure format error. An empty allocation means the
    # merged table was hand-edited or an intermediate was misaligned — data that must not
    # be delivered.
    blank = [f"{e['topic']}/p{e['partition']}" for e in entries
             if any(d == '' for d in e.get('log_dirs', []))]
    if blank:
        return {
            'status': 'FAIL',
            'stage': 3,
            'reason': 'INCOMPLETE_ALLOCATION',
            'message': '合并表存在缺少新增副本分配的分区（Allocation Broker ID/Path 为空），'
                       '无法生成 reassignment JSON: %s' % '; '.join(blank[:10]),
            'inputs': [all_csv_path],
            'outputs': [],
            'params': {'replica_count': replica_count,
                       'json_strategy': strategy,
                       'json_strategy_param': strategy_param},
            'stats': {'total_entries': len(entries), 'files_generated': 0,
                      'validation_pass': 0, 'validation_fail': 1,
                      'incomplete_allocations': blank},
            'validation_details': [{'check': '3.10', 'status': 'FAIL',
                                    'detail': '缺少新增副本分配: %s' % '; '.join(blank[:10])}],
        }

    # Pre-check B: output file-name collisions (per_topic / custom use topic names as file
    # names). Kafka topic names are case-sensitive; one table can legally contain both
    # ITDE_PROD_AD_DIM_LKP and ITDE_PROD_ad_dim_lkp. On a case-insensitive file system the
    # two names would silently overwrite each other and lose data. Deduplicate with
    # normcase; on a hit, do not hard-fail (legal data) — append a deterministic suffix to
    # the later name and record the renames in stats for the user.
    from os.path import normcase
    import hashlib as _hashlib
    seen_fnames = {}
    disambiguations = []
    disambiguated_groups = []
    for fname, ents in file_groups:
        key = normcase(fname)
        final_name = fname
        if key in seen_fnames:
            stem, _, ext = fname.rpartition('.')
            digest = _hashlib.sha1(fname.encode('utf-8')).hexdigest()[:8]
            final_name = f'{stem}__{digest}.{ext}'
            disambiguations.append(f'{fname} -> {final_name}（与 {seen_fnames[key]} 大小写冲突）')
        seen_fnames[key] = final_name
        disambiguated_groups.append((final_name, ents))
    if disambiguations:
        file_groups = disambiguated_groups

    # Pre-check D: final file name + realpath containment (defense in depth against a future strategy building an unexpected path).
    json_dir = os.path.join(output_dir, 'json')
    unsafe_files = []
    for fname, _ents in file_groups:
        if os.path.basename(fname) != fname or not _FILENAME_SAFE_RE.match(fname):
            unsafe_files.append(fname)
        elif not _path_inside(json_dir, fname):
            unsafe_files.append(fname)
    if unsafe_files:
        return {
            'status': 'FAIL',
            'stage': 3,
            'reason': 'INVALID_TOPIC_NAME',
            'message': '生成文件名不安全（须为 [A-Za-z0-9._-]+.json 且落在输出目录内）：%s。'
                       '已停止，未写任何 JSON 文件。' % '; '.join(unsafe_files[:10]),
            'inputs': [all_csv_path],
            'outputs': [],
            'params': {'replica_count': replica_count,
                       'json_strategy': strategy,
                       'json_strategy_param': strategy_param},
            'stats': {'total_entries': len(entries), 'files_generated': 0,
                      'validation_pass': 0, 'validation_fail': 1,
                      'unsafe_filenames': unsafe_files,
                      'filename_disambiguations': disambiguations},
            'validation_details': [{'check': '3.9', 'status': 'FAIL',
                                    'detail': '不安全文件名: %s' % '; '.join(unsafe_files[:10])}],
        }
    written_files = write_json_files(file_groups, json_dir)

    # Feed "which partitions carry a degradation marker" into the validator; it is only
    # used to enrich the 3.4 FAIL message. There is no L2-EXCEPTION pass-through anymore.
    l2_info = {(e['topic'], e['partition']): e.get('_original_path')
               for e in entries if e.get('_degradation')}
    validation_results = validate_json_files(written_files, replica_count, len(entries), l2_info)

    # Summary
    fail_count = sum(1 for _, s, _ in validation_results if s == 'FAIL')
    pass_count = sum(1 for _, s, _ in validation_results if s == 'PASS')

    result = {
        'status': 'PASS' if fail_count == 0 else 'FAIL',
        'stage': 3,
        'inputs': [all_csv_path],
        'outputs': written_files,
        'params': {
            'replica_count': replica_count,
            'json_strategy': strategy,
            'json_strategy_param': strategy_param,
        },
        'stats': {
            'total_entries': len(entries),
            'files_generated': len(written_files),
            'validation_pass': pass_count,
            'validation_fail': fail_count,
            'filename_disambiguations': disambiguations,
        },
        'validation_details': [
            {'check': cid, 'status': status, 'detail': detail}
            for cid, status, detail in validation_results
        ],
        'file_groups': [
            {'filename': os.path.basename(fp), 'partition_count': len(ents)}
            for fp, ents in zip(written_files, [g[1] for g in file_groups])
        ],
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Stage 3: 合并总表 -> Kafka 分区重分配 JSON（分组策略见 --strategy）')
    parser.add_argument('--input', required=True, help='Path to topic_all.xlsx（阶段二合并总表）')
    parser.add_argument('--output-dir', required=True, help='Output directory（JSON 落在 <dir>/json/）')
    parser.add_argument('--replica-count', type=int, default=2, help='Target replica count')
    parser.add_argument('--strategy', default='size_10g',
                        help='分组策略：size_10g（按 topic 分区大小阈值）/ topic_count（按每文件 topic 个数）'
                             ' / single_file / per_topic / custom')
    parser.add_argument('--strategy-param', default='10',
                        help='策略参数（分区大小阈值 GB 或 每文件 topic 个数）')
    args = parser.parse_args(argv)

    result = run(args.input, args.output_dir, args.replica_count, args.strategy, args.strategy_param)

    # Stage gate: run() self-PASS only says internal checks agree; the hard 3.1~3.10
    # validation must run again. Headless execution (agent / CI) does not go through the
    # Web UI, so if the gate is not in the CLI it does not exist.
    if result.get('status') == 'PASS':
        try:
            from validate import validate_stage3, format_checks
            checks = validate_stage3(result)
            text, passed = format_checks('阶段三', checks)
            sys.stderr.write(text + '\n')
            result['validation'] = {'passed': passed,
                                    'checks': [{'check': c[0], 'status': c[1], 'detail': c[2]} for c in checks]}
            if not passed:
                result['status'] = 'FAIL'
                result['reason'] = 'VALIDATION_FAIL'
        except Exception as exc:  # a validator exception must also block delivery, never pass silently
            result['status'] = 'FAIL'
            result['reason'] = 'VALIDATION_ERROR'
            result['validation_error'] = '%s: %s' % (type(exc).__name__, exc)
            sys.stderr.write('阶段三校验器异常：%s: %s\n' % (type(exc).__name__, exc))

    # stdout carries only JSON: callers (including the automated validator) do json.loads(stdout); the human-readable summary goes to stderr.
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')

    status = result.get('status')
    if status == 'PASS':
        return 0
    if status == 'L3_BLOCKED':
        return 2
    return 1


if __name__ == '__main__':
    sys.exit(main())
