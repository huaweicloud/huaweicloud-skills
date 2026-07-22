# -*- coding: utf-8 -*-
"""Batch test: run the MRS Hive SQL checker on real .q test files from the
Hive kernel test suite. These files contain syntactically valid Hive SQL,
so the checker should produce zero ERROR-level violations (false positives).

Usage:
    python test_q_files.py [sample_size]
    sample_size: number of .q files to sample (default 50)
"""
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
    """Split .q file content into individual SQL statements by semicolon.
    Handles strings and comments."""
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

        # Handle line comments
        if in_line_comment:
            if ch == '\n':
                in_line_comment = False
            current.append(ch)
            i += 1
            continue

        # Handle block comments
        if in_block_comment:
            if ch == '*' and nxt == '/':
                in_block_comment = False
                current.append('*/')
                i += 2
                continue
            current.append(ch)
            i += 1
            continue

        # Handle strings
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

        # Detect line comment
        if ch == '-' and nxt == '-':
            in_line_comment = True
            current.append('--')
            i += 2
            continue

        # Detect block comment
        if ch == '/' and nxt == '*':
            in_block_comment = True
            current.append('/*')
            i += 2
            continue

        # Detect string start
        if ch in ("'", '"'):
            in_string = True
            string_char = ch
            current.append(ch)
            i += 1
            continue

        # Detect statement separator
        if ch == ';':
            stmt = ''.join(current).strip()
            if stmt:
                # Remove ALL leading line comments (one or more, with or without trailing newline)
                stmt = re.sub(r'^(?:\s*--[^\n]*\n?)+', '', stmt).strip()
                # Remove leading block comments
                stmt = re.sub(r'^\s*/\*.*?\*/\s*', '', stmt, flags=re.DOTALL).strip()
                # Remove leading line comments again (after block comment removal)
                stmt = re.sub(r'^(?:\s*--[^\n]*\n?)+', '', stmt).strip()
                if stmt:
                    statements.append(stmt)
            current = []
            i += 1
            continue

        current.append(ch)
        i += 1

    # Last statement without semicolon
    stmt = ''.join(current).strip()
    if stmt:
        # Apply same comment stripping as semicolon-terminated statements
        stmt = re.sub(r'^(?:\s*--[^\n]*\n?)+', '', stmt).strip()
        stmt = re.sub(r'^\s*/\*.*?\*/\s*', '', stmt, flags=re.DOTALL).strip()
        stmt = re.sub(r'^(?:\s*--[^\n]*\n?)+', '', stmt).strip()
        if stmt:
            statements.append(stmt)

    return statements


def main():
    sample_size = int(sys.argv[1]) if len(sys.argv) > 1 else 50

    # Collect all .q files
    all_files = []
    for root, dirs, files in os.walk(Q_DIR):
        for f in files:
            if f.endswith('.q'):
                all_files.append(os.path.join(root, f))

    print(f"Total .q files found: {len(all_files)}")
    print(f"Sampling {sample_size} files for testing...\n")

    # Sample randomly but with a fixed seed for reproducibility
    random.seed(42)
    sample_files = sorted(random.sample(all_files, min(sample_size, len(all_files))))

    total_statements = 0
    stmts_with_errors = 0
    stmts_with_warnings = 0
    violation_counts = defaultdict(int)
    error_samples = defaultdict(list)  # rule_id -> [(file, statement_preview)]

    for qfile in sample_files:
        try:
            with open(qfile, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            print(f"  SKIP (read error): {os.path.basename(qfile)}: {e}")
            continue

        statements = split_statements(content)
        for stmt in statements:
            # Skip very short or non-SQL lines
            if len(stmt) < 10:
                continue
            # Skip lines that are just comments or set commands
            upper = stmt.upper().lstrip()
            if upper.startswith('SET ') or upper.startswith('ADD JAR') or \
               upper.startswith('LIST ') or upper.startswith('DELETE JAR') or \
               upper.startswith('DFS ') or upper.startswith('SOURCE '):
                continue
            # Skip Java code blocks embedded in .q files (UDF source code)
            if upper.startswith('PUBLIC CLASS') or upper.startswith('IMPORT ') or \
               upper.startswith('PACKAGE ') or upper.startswith('PUBLIC ') or \
               upper.startswith('CLASS ') or 'EXTENDS UDF' in upper or \
               'PUBLIC STATIC VOID MAIN' in upper:
                continue

            total_statements += 1
            try:
                result = check_sql(stmt)
            except Exception as e:
                # If the checker itself crashes, report it
                print(f"  CRASH on {os.path.basename(qfile)}: {e}")
                print(f"    Statement: {stmt[:100]}...")
                continue

            violations = result.get("violations", [])
            errors = [v for v in violations if v.get("level") == "ERROR"]
            warnings = [v for v in violations if v.get("level") == "WARNING"]

            if errors:
                stmts_with_errors += 1
            if warnings:
                stmts_with_warnings += 1

            for v in violations:
                rid = v.get("rule_id", "UNKNOWN")
                level = v.get("level", "ERROR")
                if level in ("ERROR", "WARNING"):
                    violation_counts[f"{level}:{rid}"] += 1
                    if len(error_samples[f"{level}:{rid}"]) < 3:
                        error_samples[f"{level}:{rid}"].append(
                            (os.path.basename(qfile), stmt[:120].replace('\n', ' '))
                        )

    # Report
    print("=" * 70)
    print("BATCH TEST RESULTS")
    print("=" * 70)
    print(f"Files sampled:      {len(sample_files)}")
    print(f"Statements tested:  {total_statements}")
    print(f"Statements with ERROR violations:   {stmts_with_errors} "
          f"({stmts_with_errors/max(total_statements,1)*100:.1f}%)")
    print(f"Statements with WARNING violations: {stmts_with_warnings} "
          f"({stmts_with_warnings/max(total_statements,1)*100:.1f}%)")
    print()

    if violation_counts:
        print("Violation breakdown (ERROR/WARNING only):")
        for key, count in sorted(violation_counts.items(), key=lambda x: -x[1]):
            print(f"  {key:30s}  count={count}")
            for fname, preview in error_samples[key]:
                print(f"      [{fname}] {preview}...")
    else:
        print("No ERROR/WARNING violations detected! (zero false positives)")

    print()
    print("=" * 70)
    fp_rate = (stmts_with_errors + stmts_with_warnings) / max(total_statements, 1) * 100
    print(f"Overall false-positive rate: {fp_rate:.1f}%")
    print("=" * 70)


if __name__ == "__main__":
    main()
