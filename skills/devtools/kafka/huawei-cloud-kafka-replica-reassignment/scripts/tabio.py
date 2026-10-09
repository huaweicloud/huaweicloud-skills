# AI-generated
#!/usr/bin/env python3
"""
Unified read/write layer for intermediate artifacts: all table artifacts of
Stage 1 -> Stage 2 -> Stage 3 flow through this module.

Naming convention (artifact names describe content, no cluster name — a hardcoded
cluster name in a file name would force editing code per cluster):
    topic.xlsx           original replica table    -- Stage 1 artifact
    topic_new.xlsx       new replicas              -- Stage 1 artifact
    broker_updated.xlsx  refreshed disk table      -- Stage 1 artifact
    topic_all.xlsx       merged master table       -- Stage 2 artifact
    json/*.json          reassignment JSON         -- Stage 3 artifact

Legacy compatibility: pre-upgrade dolce_main*.csv files can still be read — the
read side looks for the new name first and falls back to the legacy name, and
picks the xlsx / TSV parser by extension. Existing intermediate artifacts can
therefore continue through the pipeline without re-running Stage 1.
"""

import os
import sys

sys.dont_write_bytecode = True

MAIN_NAME = 'topic.xlsx'
NEW_NAME = 'topic_new.xlsx'
ALL_NAME = 'topic_all.xlsx'
BROKER_UPDATED_NAME = 'broker_updated.xlsx'

LEGACY_MAIN_NAME = 'dolce_main.csv'
LEGACY_NEW_NAME = 'dolce_main_new.csv'
LEGACY_ALL_NAME = 'dolce_main_all.csv'


def cell_to_str(value):
    """Convert a cell to a string, avoiding float-integer values like 3.0 / 3
    bouncing back and forth between the two formats."""
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer() and abs(value) < 1e15:
            return str(int(value))
        return format(value, '.15g')
    return str(value).strip()


def _coerce(text):
    """Restore a string to int / float / str.

    Only convert when the shape is unambiguous: values with leading zeros like
    '01' stay strings, otherwise partition IDs and broker numbers would be
    silently rewritten.
    """
    if text == '':
        return ''
    body = text.lstrip('-').lstrip('+')
    if body.isdigit() and not (body.startswith('0') and len(body) > 1):
        try:
            return int(text)
        except ValueError:
            pass
    try:
        return float(text)
    except ValueError:
        return text


def read_table(path):
    """Read a table -> (headers, rows).

    rows is a string matrix (cells normalized); numeric semantics are decided by
    the caller per column name — the read layer should not decide which column
    is numeric for a stage.
    """
    if path.lower().endswith('.xlsx'):
        return _read_xlsx(path)
    return _read_tsv(path)


def read_records(path):
    """Read a table -> list[dict], keyed by header; numeric-shaped values are
    converted to int / float."""
    headers, rows = read_table(path)
    records = []
    for row in rows:
        if not any(cell for cell in row):
            continue
        records.append({h: _coerce(row[i] if i < len(row) else '')
                        for i, h in enumerate(headers)})
    return records


def write_table(path, headers, rows):
    """Write a table: .xlsx via openpyxl, everything else as TAB-separated text
    (keeps legacy format compatibility)."""
    if path.lower().endswith('.xlsx'):
        _write_xlsx(path, headers, rows)
    else:
        _write_tsv(path, headers, rows)


def artifact_path(output_dir, name, legacy_name=None):
    """Locate an artifact: prefer the new name; fall back to the legacy file if
    the new name is missing but the legacy one exists."""
    path = os.path.join(output_dir, name)
    if legacy_name and not os.path.exists(path):
        legacy = os.path.join(output_dir, legacy_name)
        if os.path.exists(legacy):
            return legacy
    return path


def same_file(path_a, path_b):
    """Decide whether two paths point at the same file (case and relative-path
    differences normalized)."""
    return os.path.normcase(os.path.abspath(path_a)) == os.path.normcase(os.path.abspath(path_b))


def _read_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    raw = list(ws.iter_rows(values_only=True))
    wb.close()
    if not raw:
        return [], []
    headers = [cell_to_str(h) for h in raw[0]]
    rows = [[cell_to_str(c) for c in row] for row in raw[1:] if row is not None]
    return headers, rows


def _read_tsv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
    if not lines:
        return [], []
    sep = '\t' if '\t' in lines[0] else ','
    headers = [h.strip() for h in lines[0].strip().split(sep)]
    rows = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        rows.append([c.strip() for c in line.split(sep)])
    return headers, rows


def _write_xlsx(path, headers, rows):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Sheet1'
    ws.append(list(headers))
    for row in rows:
        ws.append([cell_to_str(v) if isinstance(v, str) else v for v in row])
    wb.save(path)


def _write_tsv(path, headers, rows):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\t'.join(str(h) for h in headers) + '\n')
        for row in rows:
            f.write('\t'.join(cell_to_str(v) for v in row) + '\n')