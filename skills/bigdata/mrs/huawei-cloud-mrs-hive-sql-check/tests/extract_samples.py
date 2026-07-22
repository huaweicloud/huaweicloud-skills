# -*- coding: utf-8 -*-
"""Extract one full SQL example for each violation rule type."""
import sys
import os
import re
import random
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rules'))

from hive_sql_checker import check_sql

Q_DIR = r"D:\work\green_area\hive\870\Hive_Kernel\ql\src\test\queries\clientpositive"


def split_statements(sql_text):
    statements = []
    current = []
    i = 0
    in_string = False
    string_char = None
    in_line_comment = False
    in_block_comment = False

    while i < len(sql_text):
        ch = sql_text[i]
        nxt = sql_text[i + 1] if i + 1 < len(sql_text) else ''

        if in_line_comment:
            if ch == '\n':
                in_line_comment = False
            current.append(ch)
            i += 1
            continue
        if in_block_comment:
            if ch == '*' and nxt == '/':
                in_block_comment = False
                current.append('*/')
                i += 2
                continue
            current.append(ch)
            i += 1
            continue
        if in_string:
            if ch == string_char:
                in_string = False
            elif ch == '\\' and i + 1 < len(sql_text):
                current.append(ch)
                current.append(sql_text[i + 1])
                i += 2
                continue
            current.append(ch)
            i += 1
            continue
        if ch == '-' and nxt == '-':
            in_line_comment = True
            current.append('--')
            i += 2
            continue
        if ch == '/' and nxt == '*':
            in_block_comment = True
            current.append('/*')
            i += 2
            continue
        if ch in ("'", '"'):
            in_string = True
            string_char = ch
            current.append(ch)
            i += 1
            continue
        if ch == ';':
            stmt = ''.join(current).strip()
            if stmt:
                stmt = re.sub(r'^\s*--[^\n]*\n', '', stmt).strip()
                stmt = re.sub(r'^\s*/\*.*?\*/\s*', '', stmt, flags=re.DOTALL).strip()
                if stmt:
                    statements.append(stmt)
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1

    stmt = ''.join(current).strip()
    if stmt:
        statements.append(stmt)
    return statements


def main():
    random.seed(42)
    all_files = []
    for root, dirs, files in os.walk(Q_DIR):
        for f in files:
            if f.endswith('.q'):
                all_files.append(os.path.join(root, f))
    sample_files = sorted(random.sample(all_files, min(500, len(all_files))))

    # rule_id -> (filename, full_statement, level, message)
    samples = {}
    # Track how many we've found
    found_rules = set()

    for qfile in sample_files:
        try:
            with open(qfile, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception:
            continue

        statements = split_statements(content)
        for stmt in statements:
            if len(stmt) < 10:
                continue
            upper = stmt.upper().lstrip()
            if upper.startswith('SET ') or upper.startswith('ADD JAR') or upper.startswith('LIST '):
                continue

            try:
                result = check_sql(stmt)
            except Exception:
                continue

            for v in result.get("violations", []):
                rid = v.get("rule_id", "")
                level = v.get("level", "")
                msg = v.get("message", "")
                if level not in ("ERROR", "WARNING"):
                    continue
                key = f"{level}:{rid}"
                if key not in samples:
                    samples[key] = (os.path.basename(qfile), stmt, level, msg)

        # Check if we have all rules we care about
        # We want at least one sample for each rule type found in the full test
        target_rules = {
            "WARNING:SPEC002", "WARNING:SPEC021", "WARNING:SPEC024",
            "WARNING:SPEC005", "ERROR:SYN003", "ERROR:SPEC017",
            "ERROR:SPEC004", "WARNING:SPEC005",
            "ERROR:SPEC016", "ERROR:SPEC003",
            "ERROR:INTERCEPT001",
            "ERROR:SYN-ERR", "ERROR:SYN007",
            "WARNING:SPEC019", "WARNING:SPEC023",
            "WARNING:INTERCEPT006", "ERROR:INTERCEPT004",
            "WARNING:SPEC007", "ERROR:SPEC009",
        }
        if set(samples.keys()) >= target_rules:
            break

    # Print results
    for key in sorted(samples.keys()):
        fname, stmt, level, msg = samples[key]
        # Truncate very long statements
        display_stmt = stmt if len(stmt) <= 500 else stmt[:500] + " ..."
        # Clean up whitespace
        display_stmt = re.sub(r'\s+', ' ', display_stmt).strip()
        print(f"{'=' * 80}")
        print(f"[{key}]")
        print(f"  File: {fname}")
        print(f"  Message: {msg}")
        print(f"  SQL: {display_stmt}")
        print()


if __name__ == "__main__":
    main()
