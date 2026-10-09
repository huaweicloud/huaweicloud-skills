#!/usr/bin/env python3
"""
Stage 2: original replica table topic.xlsx + new replica table topic_new.xlsx
         -> merged master table topic_all.xlsx.

Sorts by topic total capacity ascending, groups same topic together,
partitions sorted within topic.
"""

import argparse
import json
import os
import sys

from collections import defaultdict

# The skill package may be read-only after install, and no compile cache belongs in it:
# disable bytecode writing so execution never creates __pycache__ under scripts/.
sys.dont_write_bytecode = True

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tabio   # noqa: E402  same-dir module; must import after sys.path fix


def read_tsv(path):
    """Read a table (xlsx / TSV) into list[dict]; numeric-looking values become int / float.

    The name stays read_tsv to keep validate.py's existing import; the implementation goes
    through the unified I/O layer and reads both xlsx and legacy TSV intermediate files.
    """
    return tabio.read_records(path)


def merge_records(main_records, new_records, replica_count=2):
    """
    Merge original and new replica records by (Topic, Partition).

    For replica_count=2, each output row has:
      Topic, PartitionCount, Partition, Original Broker ID, Path,
      Allocation Broker ID, Path, Size(bytes), Size(GB)

    For replica_count>2, extends with Allocation Broker ID 2, Path 2, etc.
    """
    # Group new records by (Topic, Partition)
    new_by_key = defaultdict(list)
    for rec in new_records:
        key = (rec['Topic'], rec['Partition'])
        new_by_key[key].append(rec)

    merged = []
    for rec in main_records:
        key = (rec['Topic'], rec['Partition'])
        new_recs = new_by_key.get(key, [])

        row = {
            'Topic': rec['Topic'],
            'PartitionCount': rec['PartitionCount'],
            'Partition': rec['Partition'],
            'Original Broker ID': rec['Broker ID'],
            'Original Path': rec['Path'],
            'Size(bytes)': rec.get('Size(bytes)', 0),
            'Size(GB)': rec.get('Size(GB)', 0.0),
            'degradation': '',
        }

        # Add allocation columns
        for i, nr in enumerate(new_recs):
            suffix = '' if i == 0 and replica_count == 2 else f' {i+1}'
            if replica_count == 2:
                row['Allocation Broker ID'] = nr['Broker ID']
                row['Allocation Path'] = nr['Path']
            else:
                row[f'Allocation Broker ID{suffix}'] = nr['Broker ID']
                row[f'Allocation Path{suffix}'] = nr['Path']
            # The degradation marker must follow the data: this version only admits L0
            # (degradation is always empty), but the column is kept for old artifacts; if a
            # legacy L2 marker is read, Stage 3's duplicate-broker hard check rejects it.
            deg = str(nr.get('degradation', '') or '')
            if deg and deg > row['degradation']:
                row['degradation'] = deg

        merged.append(row)

    return merged


def sort_by_topic_size(merged, replica_count=2):
    """
    Sort by topic total capacity ascending.
    topic_total = sum(all partitions × all replicas Size(GB))
    Within same topic, sort by Partition ascending.
    """
    # Calculate topic total size
    topic_sizes = defaultdict(float)
    for row in merged:
        topic = row['Topic']
        size_gb = row.get('Size(GB)', 0.0)
        # Total = original + all allocations = replica_count × size
        topic_sizes[topic] += size_gb * replica_count

    # Sort: by topic_size ascending, then by partition ascending
    merged.sort(key=lambda r: (
        topic_sizes[r['Topic']],
        r['Topic'],
        r['Partition']
    ))

    return merged, dict(topic_sizes)


def build_headers(replica_count=2):
    # The merged table column names. Originals are explicitly named Original Broker ID /
    # Original Path: an old version had two same-named Path columns and downstream name-based
    # lookups read the wrong value, which could only be guessed positionally, so the names
    # are disambiguated here. degradation sits last so the marker never breaks the chain at
    # Stage 2.
    headers = ['Topic', 'PartitionCount', 'Partition',
               'Original Broker ID', 'Original Path']
    if replica_count == 2:
        headers += ['Allocation Broker ID', 'Allocation Path']
    else:
        for i in range(1, replica_count):
            headers += [f'Allocation Broker ID {i}', f'Allocation Path {i}']
    headers += ['Size(bytes)', 'Size(GB)', 'degradation']
    return headers


def write_merged_table(merged, output_path, replica_count=2):
    # Column names map one-to-one to row keys; no duplicate column names, so lookups no
    # longer depend on column position.
    headers = build_headers(replica_count)
    rows = [[row.get(h, '') for h in headers] for row in merged]
    tabio.write_table(output_path, headers, rows)


def run(main_csv_path, new_csv_path, output_dir, replica_count=2):
    """Main entry point for stage 2."""
    os.makedirs(output_dir, exist_ok=True)

    main_records = read_tsv(main_csv_path)
    new_records = read_tsv(new_csv_path)

    if not main_records:
        return {'status': 'FAIL', 'error': f'No records in {main_csv_path}'}

    # Merge
    merged = merge_records(main_records, new_records, replica_count)

    # Sort
    merged, topic_sizes = sort_by_topic_size(merged, replica_count)

    # Write output
    output_path = os.path.join(output_dir, tabio.ALL_NAME)
    write_merged_table(merged, output_path, replica_count)

    # Validation stats
    expected_rows = len(main_records)
    actual_rows = len(merged)

    # Check for missing partitions
    main_keys = set((r['Topic'], r['Partition']) for r in main_records)
    merged_keys = set((r['Topic'], r['Partition']) for r in merged)
    missing = main_keys - merged_keys
    duplicates = len(merged) - len(merged_keys)

    # Allocation-column completeness: every partition must carry replica_count-1 non-empty
    # Allocation columns. Stage 1 artifacts are complete in normal operation; once upstream
    # data is hand-edited or an intermediate is misaligned, empty Allocation rows silently
    # pierce the old Stage 2 and become an obscure log_dirs validation failure at Stage 3.
    # This check stops the "missing new replica" bad row at the source with the exact
    # topic/partition named.
    incomplete = []
    for row in merged:
        if replica_count == 2:
            pairs = [(row.get('Allocation Broker ID'), row.get('Allocation Path'))]
        else:
            pairs = [(row.get('Allocation Broker ID %d' % i), row.get('Allocation Path %d' % i))
                     for i in range(1, replica_count)]
        bad_idx = [i for i, (bid, path) in enumerate(pairs, 1)
                   if bid in (None, '') or path in (None, '')]
        if bad_idx:
            incomplete.append('%s/p%s: 缺 Allocation #%s'
                              % (row['Topic'], row['Partition'], '/'.join(map(str, bad_idx))))
    alloc_ok = not incomplete

    result = {
        'status': ('PASS' if actual_rows == expected_rows and not missing
                   and duplicates == 0 and alloc_ok else 'FAIL'),
        'stage': 2,
        'inputs': [main_csv_path, new_csv_path],
        'outputs': [output_path],
        'params': {'replica_count': replica_count},
        'stats': {
            'main_rows': len(main_records),
            'new_rows': len(new_records),
            'merged_rows': actual_rows,
            'expected_rows': expected_rows,
            'missing_partitions': len(missing),
            'duplicate_rows': duplicates,
            'incomplete_allocations': incomplete,
            'topic_count': len(topic_sizes),
            'degradation_count': sum(1 for r in merged if r.get('degradation')),
            'topic_sizes': {k: round(v, 2) for k, v in sorted(topic_sizes.items(), key=lambda x: x[1])},
        },
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Stage 2: 原副本表 + 新增副本表 -> topic_all.xlsx（合并总表）')
    parser.add_argument('--main', required=True, help='Path to topic.xlsx（阶段一原副本表）')
    parser.add_argument('--new', required=True, help='Path to topic_new.xlsx（阶段一新增副本表）')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    parser.add_argument('--replica-count', type=int, default=2, help='Target replica count')
    args = parser.parse_args(argv)

    result = run(args.main, args.new, args.output_dir, args.replica_count)

    # run() self-PASS only says row counts match; hard checks like column names / sort /
    # missing partitions must run again. Headless (agent / CI) does not go through the Web
    # UI, so if the gate is not in the CLI it does not exist.
    if result.get('status') == 'PASS':
        try:
            from validate import validate_stage2, format_checks
            checks = validate_stage2(result, args.output_dir)
            text, passed = format_checks('阶段二', checks)
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
            sys.stderr.write('阶段二校验器异常：%s: %s\n' % (type(exc).__name__, exc))

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