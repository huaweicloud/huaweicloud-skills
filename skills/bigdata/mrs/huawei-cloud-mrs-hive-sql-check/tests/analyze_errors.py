# -*- coding: utf-8 -*-
"""Detailed error analysis: print full violation messages for SYN-ERR/SYN003."""
import sys
import os
import re
import random

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
    sample_files = sorted(random.sample(all_files, min(20, len(all_files))))

    # Collect detailed errors for SYN-ERR and SYN003
    syn_err_samples = []
    syn003_samples = []
    other_syn_samples = []

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
            except Exception as e:
                print(f"CRASH on {os.path.basename(qfile)}: {e}")
                print(f"  Statement: {stmt[:200]}")
                continue

            for v in result.get("violations", []):
                rid = v.get("rule_id", "")
                level = v.get("level", "")
                msg = v.get("message", "")
                if level not in ("ERROR", "WARNING"):
                    continue
                entry = (os.path.basename(qfile), rid, level, msg, stmt[:300])
                if rid == "SYN-ERR" and len(syn_err_samples) < 15:
                    syn_err_samples.append(entry)
                elif rid == "SYN003" and len(syn003_samples) < 15:
                    syn003_samples.append(entry)
                elif rid.startswith("SYN") and len(other_syn_samples) < 10:
                    other_syn_samples.append(entry)

    print("=" * 80)
    print("SYN-ERR samples (词法错误)")
    print("=" * 80)
    for fname, rid, level, msg, stmt in syn_err_samples:
        print(f"\n[{fname}] {rid}: {msg}")
        print(f"  SQL: {stmt[:250]}")

    print("\n" + "=" * 80)
    print("SYN003 samples (语法结构错误)")
    print("=" * 80)
    for fname, rid, level, msg, stmt in syn003_samples:
        print(f"\n[{fname}] {rid}: {msg}")
        print(f"  SQL: {stmt[:250]}")

    print("\n" + "=" * 80)
    print("Other SYN samples")
    print("=" * 80)
    for fname, rid, level, msg, stmt in other_syn_samples:
        print(f"\n[{fname}] {rid}: {msg}")
        print(f"  SQL: {stmt[:250]}")


if __name__ == "__main__":
    main()
