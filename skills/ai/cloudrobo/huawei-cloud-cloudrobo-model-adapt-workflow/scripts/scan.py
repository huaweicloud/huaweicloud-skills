#!/usr/bin/env python3
"""
NPU Patcher scan — scans for VLA migration issues.

Usage:
    python scan.py /path/to/model --output ./issues
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from scanners import group_issues_for_agent, PY_SCANNERS
from config import get_config
from patterns import check_integrity, PATTERNS, Issue
from utils import deduplicate_issues, collect_py_files


def get_category(pattern_id: str) -> str:
    info = PATTERNS.get(pattern_id)
    return info.category.value if info else 'UNKNOWN'


def _make_relative(file_path: str, root: Path) -> str:
    try:
        return str(Path(file_path).relative_to(root))
    except ValueError:
        return file_path


def _issue_to_minimal(issue: Issue, root: Path) -> dict:
    d = {
        'pattern_id': issue.pattern_id,
        'file': _make_relative(issue.file, root),
        'line': issue.line,
    }
    if issue.issue_id is not None:
        d['issue_id'] = issue.issue_id
    return d


def _occurrence_with_status(occ: dict, root: Path) -> dict:
    d = {
        'file': _make_relative(occ['file'], root),
        'line': occ['line'],
        'status': 'pending',
    }
    if 'issue_id' in occ and occ['issue_id'] is not None:
        d['issue_id'] = occ['issue_id']
    return d


def _assign_issue_ids(issues: list[Issue]) -> None:
    counters: dict[str, int] = {}
    for issue in issues:
        pid = issue.pattern_id
        counters[pid] = counters.get(pid, 0) + 1
        issue.issue_id = f"{pid}-{counters[pid]:03d}"


def scan_directory(root: Path) -> dict:
    cfg = get_config()
    py_files = collect_py_files(root)
    issues = []

    for scanner in PY_SCANNERS:
        for issue in scanner(py_files):
            issues.append(issue)

    issues = deduplicate_issues(issues)
    _assign_issue_ids(issues)

    groups = group_issues_for_agent(issues)

    return {
        'issues': [_issue_to_minimal(i, root) for i in issues],
        'groups': groups,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Scan for VLA NPU migration issues')
    parser.add_argument('path', type=Path)
    parser.add_argument('--output', '-o', type=Path, default=Path('.'),
                        help='output directory (default: current directory)')
    parser.add_argument('--check-integrity', action='store_true',
                        help='check Pattern registry integrity before scanning')
    args = parser.parse_args()

    if args.check_integrity:
        integrity_issues = check_integrity(verbose=True)
        if integrity_issues:
            print(f"\n  Pattern registry has {len(integrity_issues)} issue(s)")
            print("Please fix the above issues before scanning.")
            return 1

    if not args.path.exists():
        print(f"Error: {args.path} does not exist")
        return 1

    print(f"Scanning {args.path}...")
    results = scan_directory(args.path)

    n_issues = len(results['issues'])
    print(f"Found: {n_issues} issue(s) to analyze/fix")

    groups = results['groups']

    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    issues_data = {
        'scan_time': datetime.now().isoformat(),
        'model_path': str(args.path.resolve()),
        'count': n_issues,
        'patterns': []
    }
    for g in groups:
        pattern_data = {
            'pattern_id': g.pattern_id,
            'category': get_category(g.pattern_id),
            'count': g.count,
            'fixed': 0,
            'skipped': 0,
            'pending': g.count,
            'occurrences': [_occurrence_with_status(occ, args.path) for occ in g.occurrences]
        }
        issues_data['patterns'].append(pattern_data)

    (output_dir / 'issues.json').write_text(json.dumps(issues_data, indent=2))

    print(f"\nOutput:")
    print(f"  {output_dir / 'issues.json'} - for Agent review")

    return 0


if __name__ == '__main__':
    exit(main())
