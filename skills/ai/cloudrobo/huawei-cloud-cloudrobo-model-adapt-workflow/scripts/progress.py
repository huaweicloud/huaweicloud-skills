#!/usr/bin/env python3
from __future__ import annotations
"""
Issue-fix progress tracker.

Usage:
    python progress.py issues.json --summary
    python progress.py issues.json --next          # get all pending issues of the next pattern
    python progress.py issues.json --next --pattern P_RND  # get pending issues of a specific pattern
    python progress.py issues.json --pending       # list all pending issues
    python progress.py issues.json --fixed P_RND-003
    python progress.py issues.json --skip P_VEC-007 --reason "scanner false positive"
    python progress.py issues.json --check-complete
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import get_context_config


class ProgressTracker:
    def __init__(self, issues_file: Path):
        self.file_path = issues_file
        if not issues_file.exists():
            print(f"Error: {issues_file} does not exist. Run scan.py first to generate it.", file=sys.stderr)
            sys.exit(1)
        self.data = json.loads(self.file_path.read_text(encoding='utf-8'))
        self._validate()

    def _validate(self):
        total_count = self.data.get('count', 0)
        patterns = self.data.get('patterns', [])
        if total_count == 0 and not patterns:
            return
        if total_count > 0 and not patterns:
            print(f"Error: {self.file_path} reports count={total_count} but 'patterns' is empty. "
                  f"Scan output is corrupted — please re-run scan.py.", file=sys.stderr)
            sys.exit(1)

    def save(self) -> None:
        self.file_path.write_text(json.dumps(self.data, indent=2), encoding='utf-8')

    def _find_pattern_by_id(self, pattern_id: str) -> dict | None:
        for p in self.data.get('patterns', []):
            if p['pattern_id'] == pattern_id:
                return p
        return None

    def _find_occurrence_by_issue_id(self, pattern: dict, issue_id: str) -> dict | None:
        for occ in pattern.get('occurrences', []):
            if occ.get('issue_id') == issue_id:
                return occ
        return None

    def _find_by_issue_id(self, issue_id: str) -> tuple[dict | None, dict | None]:
        """Find the pattern and occurrence by issue_id. Returns (pattern,
        occ) or (None, None)."""
        if '-' not in issue_id:
            print(f"Error: invalid issue ID format '{issue_id}' (should be P_XXX-NNN)")
            return None, None
        pattern_id, _ = issue_id.rsplit('-', 1)
        pattern = self._find_pattern_by_id(pattern_id)
        if not pattern:
            return None, None
        occ = self._find_occurrence_by_issue_id(pattern, issue_id)
        return pattern, occ

    def _find_occurrence_by_location(self, pattern: dict, file: str, line: int) -> dict | None:
        normalized_file = str(Path(file))
        for occ in pattern.get('occurrences', []):
            if str(Path(occ['file'])) == normalized_file and occ['line'] == line:
                return occ
        return None

    def _update_counts(self, pattern: dict):
        fixed = sum(1 for o in pattern['occurrences'] if o.get('status') == 'fixed')
        skipped = sum(1 for o in pattern['occurrences'] if o.get('status') == 'skipped')
        pending = sum(1 for o in pattern['occurrences'] if o.get('status') == 'pending')
        pattern['fixed'] = fixed
        pattern['skipped'] = skipped
        pattern['pending'] = pending

    def mark_fixed(self, issue_id: str) -> bool:
        pattern, occ = self._find_by_issue_id(issue_id)
        if not pattern:
            print(f"Error: no Pattern found for {issue_id}")
            return False
        if not occ:
            print(f"Error: {issue_id} not found")
            return False

        occ['status'] = 'fixed'
        occ['fixed_at'] = datetime.now().isoformat()
        self._update_counts(pattern)
        self.save()
        print(f"Marked {issue_id} as fixed")
        return True

    def mark_skipped(self, issue_id: str, reason: str) -> bool:
        pattern, occ = self._find_by_issue_id(issue_id)
        if not pattern:
            print(f"Error: no Pattern found for {issue_id}")
            return False
        if not occ:
            print(f"Error: {issue_id} not found")
            return False

        occ['status'] = 'skipped'
        occ['skip_reason'] = reason
        occ['skipped_at'] = datetime.now().isoformat()
        self._update_counts(pattern)
        self.save()
        print(f"Marked {issue_id} as skipped: {reason}")
        return True

    def get_pending(self, pattern_id: str = None) -> list[dict]:
        pending = []
        for p in self.data.get('patterns', []):
            if pattern_id and p['pattern_id'] != pattern_id:
                continue
            for occ in p.get('occurrences', []):
                if occ.get('status') == 'pending':
                    pending.append({
                        'pattern': p['pattern_id'],
                        'file': occ['file'],
                        'line': occ['line'],
                        'issue_id': occ.get('issue_id'),
                    })
        return pending

    def summary(self) -> str:
        lines = []
        lines.append(f"Scan time: {self.data.get('scan_time', 'N/A')}")
        lines.append(f"Model path: {self.data.get('model_path', 'N/A')}")
        lines.append("")

        total = self.data.get('count', 0)
        total_fixed = sum(p.get('fixed', 0) for p in self.data.get('patterns', []))
        total_skipped = sum(p.get('skipped', 0) for p in self.data.get('patterns', []))
        total_pending = sum(p.get('pending', 0) for p in self.data.get('patterns', []))

        pct = (total_fixed / total * 100) if total > 0 else 0.0
        lines.append(f"Progress: {total_fixed}/{total} handled ({pct:.1f}%) — {total_fixed} fixed, {total_skipped} skipped, {total_pending} pending")
        lines.append("")

        lines.append("=" * 60)
        lines.append("Issue List")
        lines.append("=" * 60)
        for p in self.data.get('patterns', []):
            occurrences = p.get('occurrences', [])
            if not occurrences:
                continue
            pid = p['pattern_id']
            lines.append(f"\n[{pid}] {p.get('description', '')}")
            lines.append("-" * 40)
            for occ in occurrences:
                status = occ.get('status', 'pending')
                issue_id = occ.get('issue_id', '')
                file_line = f"{occ['file']}:{occ['line']}"
                label = f"{issue_id} {file_line}" if issue_id else file_line
                if status == 'pending':
                    lines.append(f"  [PENDING]   {label}")
                elif status == 'fixed':
                    lines.append(f"  [FIXED]     {label}")
                elif status == 'skipped':
                    reason = occ.get('skip_reason', 'no reason provided')
                    lines.append(f"  [SKIPPED]   {label}")
                    lines.append(f"              reason: {reason}")
        lines.append("\n" + "=" * 60)

        return '\n'.join(lines)

    def check_complete(self) -> bool:
        total_count = self.data.get('count', 0)
        total_fixed = sum(p.get('fixed', 0) for p in self.data.get('patterns', []))
        total_skipped = sum(p.get('skipped', 0) for p in self.data.get('patterns', []))
        total_pending = sum(p.get('pending', 0) for p in self.data.get('patterns', []))
        if total_count > 0 and total_fixed + total_skipped + total_pending != total_count:
            print(f"Warning: count({total_count}) != fixed({total_fixed})+skipped({total_skipped})+pending({total_pending}). "
                  f"Data may be corrupted.", file=sys.stderr)

        pending = self.get_pending()
        if pending:
            print(f"Error: {len(pending)} pending issue(s) remain")
            by_pattern = {}
            for p in pending:
                by_pattern.setdefault(p['pattern'], 0)
                by_pattern[p['pattern']] += 1
            for pid, count in sorted(by_pattern.items()):
                print(f"  {pid}: {count} pending")
            return False
        if total_count == 0:
            print("Pass: no issues found (scan reported 0 issues)")
        else:
            print(f"Pass: all {total_count} issues handled ({total_fixed} fixed, {total_skipped} skipped)")
        return True


def _handle_summary(tracker):
    """Handle the --summary subcommand."""
    print(tracker.summary())
    return 0


def _handle_next(tracker, args):
    """Handle the --next subcommand."""
    pending = tracker.get_pending(args.pattern)
    if not pending:
        total_count = tracker.data.get('count', 0)
        if args.pattern:
            print(f"{args.pattern} has no pending issues")
        elif total_count > 0:
            print(f"No pending issues (but the scan reported {total_count} total — all handled or data corrupted)")
        else:
            print("No pending issues")
        return 0

    first_pattern = pending[0]['pattern']
    same_pattern = [p for p in pending if p['pattern'] == first_pattern]
    ctx_config = get_context_config(first_pattern)
    before, after = ctx_config['before'], ctx_config['after']

    print(f"Pattern: {first_pattern} ({len(same_pattern)} pending)")
    for p in same_pattern:
        issue_id = p.get('issue_id', '')
        start = max(1, p['line'] - before)
        end = p['line'] + after
        label = f"{issue_id} " if issue_id else ""
        print(f"  {label}{p['file']}:{p['line']} (lines {start}-{end})")
        if args.show_context:
            model_path = tracker.data.get('model_path', '')
            abs_file = str(Path(model_path) / p['file']) if model_path else p['file']
            try:
                file_lines = Path(abs_file).read_text(encoding='utf-8', errors='ignore').split('\n')
                for ln in range(start - 1, min(end, len(file_lines))):
                    marker = '>>>' if ln + 1 == p['line'] else '   '
                    print(f"    {marker} {ln + 1:4d} | {file_lines[ln]}")
            except (OSError, UnicodeDecodeError):
                print(f"   (could not read the file)")

    return 0


def _handle_pending(tracker, args):
    """Handle the --pending subcommand."""
    pending = tracker.get_pending(args.pattern)
    if not pending:
        print("No pending issues")
    else:
        print(f"Pending issues ({len(pending)}):")
        for p in pending:
            issue_id = p.get('issue_id', '')
            label = f"{issue_id} " if issue_id else ""
            print(f"  [{p['pattern']}] {label}{p['file']}:{p['line']}")

    return 0


def _handle_fixed(tracker, args):
    """Handle the --fixed subcommand."""
    tracker.mark_fixed(args.fixed)
    return 0


def _handle_skip(tracker, args):
    """Handle the --skip subcommand."""
    if not args.reason:
        print("Error: --reason is required when using --skip")
        return 1
    tracker.mark_skipped(args.skip, args.reason)
    return 0


def _handle_check_complete(tracker):
    """Handle the --check-complete subcommand."""
    success = tracker.check_complete()
    return 0 if success else 1


def main() -> int:
    parser = argparse.ArgumentParser(description='Track issue-fix progress')
    parser.add_argument('issues_file', type=Path, help='path to issues.json')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--summary', action='store_true', help='show the progress summary')
    group.add_argument('--next', action='store_true',
                       help='get all pending issues of the next pattern')
    group.add_argument('--pending', action='store_true', help='list all pending issues')
    group.add_argument('--fixed', metavar='ISSUE_ID',
                       help='mark an issue as fixed (e.g. P_RND-003)')
    group.add_argument('--skip', metavar='ISSUE_ID',
                       help='mark an issue as skipped (e.g. P_VEC-007)')
    group.add_argument('--check-complete', action='store_true',
                       help='check whether all issues are handled')

    parser.add_argument('--reason', type=str, default=None,
                        help='skip reason (required when using --skip)')
    parser.add_argument('--pattern', type=str,
                        help='filter by Pattern ID (use with --pending and --next)')
    parser.add_argument('--show-context', action='store_true',
                        help='show code context around the issue (use with --next)')

    args = parser.parse_args()

    tracker = ProgressTracker(args.issues_file)

    if args.summary:
        return _handle_summary(tracker)

    if args.next:
        return _handle_next(tracker, args)

    if args.pending:
        return _handle_pending(tracker, args)

    if args.fixed:
        return _handle_fixed(tracker, args)

    if args.skip:
        return _handle_skip(tracker, args)

    if args.check_complete:
        return _handle_check_complete(tracker)

    return 0


if __name__ == '__main__':
    exit(main())
