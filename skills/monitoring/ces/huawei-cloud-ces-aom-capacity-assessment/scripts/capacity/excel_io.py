"""Excel read/write module: reads headers/row data, matches writes by header name, inserts date peak/valley
columns, atomic writes.

Boundary: only reads and writes, no computation, no data collection. Writes never generate backups;
temp file + atomic replace; the original file stays unchanged on exceptions.
(.bak-* cleanup is only handled by the cleanup subcommand calling _prune_backups for historical residue)

Header matching strategy: strip whitespace first, then remove parenthesized suffixes like "（必填）" to get
the "base name", match by base name.
Date peak/valley header format: M/D峰值 / M/D谷值, e.g. 7/1峰值.
"""
from __future__ import annotations

import glob
import json
import os
import re
from typing import Any, Optional

from openpyxl import load_workbook

DEFAULT_SHEET = "保障重点实例_容量管理模板"

# Required columns (base names). region and the Chinese names must match the template.
REQUIRED_COLUMNS = ["region", "实例类型", "实例ID", "关键指标", "入口实例ID"]
# 入口实例ID base name (anchor for date-column insertion)
ANCHOR_COLUMN = "入口实例ID"

# Full headers used when creating missing columns
CANONICAL_HEADERS: dict[str, str] = {
    "峰谷值倍数": "峰谷值倍数\n（工具可输出，选填）",
    "压力系数": "压力系数\n（工具可输出，选填）",
    "预计节日上限": "预计节日上限\n（工具可输出，选填）",
    "资源上限": "资源上限\n（选填）",
    "单位": "单位\n（工具可输出，选填）",
    "扩容建议": "扩容建议\n（工具可输出，选填）",
    "t-24峰值": "t-24峰值",
    "t-24谷值": "t-24谷值",
    "t-24峰谷值增长倍数": "t-24峰谷值增长倍数",
    "t-24压力系数": "t-24压力系数",
    "t-24预计节日上限": "t-24预计节日上限",
    "t-24是否需要扩容": "t-24是否需要扩容",
}

DATE_HEADER_RE = re.compile(r"^(\d{1,2})/(\d{1,2})(峰值|谷值)$")
KIND_ORDER = {"峰值": 0, "谷值": 1}


def norm_header(raw: Any) -> str:
    """Normalize a header: strip whitespace."""
    return re.sub(r"\s+", "", str(raw).strip())


def base_name(header: str) -> str:
    """Strip parenthesized suffixes like "（必填）" to get the base name."""
    s = norm_header(header)
    s = re.sub(r"（[^）]*）", "", s)
    return s.strip()


def parse_date_header(header: str) -> Optional[tuple[int, int, str]]:
    """Parse a date peak/valley header -> (month, day, kind); return None if not a date column."""
    m = DATE_HEADER_RE.match(base_name(header))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), m.group(3)


def _date_sort_key(entry: tuple[int, int, str]) -> tuple[int, int, int]:
    m, d, kind = entry
    return m, d, KIND_ORDER[kind]


def read_excel(path: str, sheet: Optional[str] = None) -> dict[str, Any]:
    """Read the sheet's headers and all data rows."""
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        if sheet is None:
            sheet = DEFAULT_SHEET if DEFAULT_SHEET in wb.sheetnames else wb.sheetnames[0]
        if sheet not in wb.sheetnames:
            raise ValueError(f"sheet not found: {sheet}, available: {wb.sheetnames}")
        ws = wb[sheet]
        rows = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()
    if not rows:
        return {"sheet": sheet, "columns": [], "rows": [], "valid": True}
    headers = rows[0]
    columns = []
    for i, h in enumerate(headers, start=1):
        columns.append({"name": norm_header(h) if h is not None else "",
                        "base": base_name(h) if h is not None else "",
                        "index": i})
    data_rows = []
    for ri, row in enumerate(rows[1:], start=2):
        if all(c is None or str(c).strip() == "" for c in row):
            continue
        cells = {}
        for ci, h in enumerate(headers):
            if ci < len(row):
                v = row[ci]
                if v is not None:
                    cells[norm_header(h)] = v
        data_rows.append({"row": ri, "cells": cells})
    # required-field validation (match by base name, compatible with "region（必填）" style headers)
    missing_rows = []
    for r in data_rows:
        by_base = {base_name(k): v for k, v in r["cells"].items()}
        miss = [c for c in REQUIRED_COLUMNS if not str(by_base.get(c, "") or "").strip()]
        if miss:
            missing_rows.append({"row": r["row"], "missing": miss})
    return {"sheet": sheet, "columns": columns, "rows": data_rows,
            "missing_rows": missing_rows,
            "valid": all(not m["missing"] for m in missing_rows)}


def _find_column(ws, base: str) -> Optional[int]:
    """Find a column index (1-based) by base name."""
    for i in range(1, ws.max_column + 1):
        h = ws.cell(row=1, column=i).value
        if h is not None and base_name(h) == base:
            return i
    return None


def _existing_date_columns(ws) -> list[tuple[int, int, int, str, int]]:
    """Return [(pos, month, day, kind, raw_header)] in position order."""
    out = []
    for i in range(1, ws.max_column + 1):
        h = ws.cell(row=1, column=i).value
        if h is None:
            continue
        p = parse_date_header(norm_header(h))
        if p:
            out.append((i, p[0], p[1], p[2], norm_header(h)))
    return out


def insert_date_columns(ws, new_headers: list[str]) -> list[str]:
    """Insert missing date columns in time order right after the 【入口实例ID】 column; return the headers
    actually inserted this call."""
    anchor = _find_column(ws, ANCHOR_COLUMN)
    existing = _existing_date_columns(ws)
    existing_set = {(m, d, k) for _, m, d, k, _ in existing}
    inserted: list[str] = []
    for h in new_headers:
        p = parse_date_header(h)
        if not p:
            continue
        if p in existing_set:
            continue
        # compute insertion position: anchor + 1 + number of date columns sorted before this date
        existing_sorted = sorted([(m, d, k) for _, m, d, k, _ in existing], key=_date_sort_key)
        before = [e for e in existing_sorted if _date_sort_key(e) < _date_sort_key(p)]
        pos = (anchor + 1 + len(before)) if anchor else (ws.max_column + 1)
        ws.insert_cols(pos, 1)
        ws.cell(row=1, column=pos, value=h)
        existing = _existing_date_columns(ws)
        inserted.append(h)
    return inserted


def write_updates(
    path: str,
    updates: list[dict[str, Any]],
    sheet: Optional[str] = None,
    create_missing: bool = True,
) -> dict[str, Any]:
    """Write cells by header name.

    updates: [{"row": int, "column": "峰谷值倍数"|"t-24峰值"|"7/1峰值", "value": any}, ...]
    column is the base name; date columns are auto-detected and inserted.
    Returns: {ok, written, created_columns, errors}
    """
    wb = load_workbook(path)
    try:
        if sheet is None:
            sheet = DEFAULT_SHEET if DEFAULT_SHEET in wb.sheetnames else wb.sheetnames[0]
        ws = wb[sheet]

        # classify: normal columns vs date columns
        normal: dict[str, list[dict]] = {}
        date_headers: list[str] = []
        for u in updates:
            col = str(u.get("column", "")).strip()
            if not col:
                continue
            if parse_date_header(col):
                if col not in date_headers:
                    date_headers.append(col)
            else:
                normal.setdefault(col, []).append(u)

        # Insert date columns first, then locate normal columns: insert_date_columns shifts all later
        # columns right, so recording normal column indexes before insertion would misalign on write
        # (bug found in practice).
        inserted = insert_date_columns(ws, date_headers)

        # record normal columns to create (those not found)
        created_cols = []
        col_index: dict[str, int] = {}
        for col in normal:
            idx = _find_column(ws, col)
            if idx is None:
                if not create_missing:
                    continue
                canonical = CANONICAL_HEADERS.get(col, col)
                # append to the end
                ws.cell(row=1, column=ws.max_column + 1, value=canonical)
                idx = _find_column(ws, col)
                created_cols.append(canonical)
            col_index[col] = idx

        # write values
        errors = []
        written = 0
        for col, us in normal.items():
            idx = col_index.get(col)
            if idx is None:
                for u in us:
                    errors.append({"row": u.get("row"), "column": col, "error": "column not created"})
                continue
            for u in us:
                ws.cell(row=int(u["row"]), column=idx, value=u.get("value"))
                written += 1
        for u in updates:
            col = str(u.get("column", "")).strip()
            if parse_date_header(col):
                idx = _find_column(ws, col)
                if idx is None:
                    errors.append({"row": u.get("row"), "column": col, "error": "date column not created"})
                    continue
                ws.cell(row=int(u["row"]), column=idx, value=u.get("value"))
                written += 1

        # atomic save (no backups; clean .tmp residue on save failure)
        tmp = path + ".tmp"
        try:
            wb.save(tmp)
            os.replace(tmp, path)
        except Exception:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        try:
            wb.close()
        except Exception:
            pass
    return {"ok": True, "written": written,
            "created_columns": created_cols + inserted, "errors": errors}


KEEP_BACKUPS = 0  # keep no .bak-* backups (historical records and invalid files are all cleaned)


def _prune_backups(path: str, keep: int = KEEP_BACKUPS) -> list[str]:
    """Delete old .bak-* backups for path, keeping only the most recent `keep`; return deleted files.

    Backup file names are <path>.bak-<YYYYmmddHHMMSS>; sorting by file name desc equals newest->oldest.
    We do not sort by mtime because multiple writes in the same second share the mtime, making the order unstable.
    """
    pattern = path + ".bak-*"
    files = sorted(glob.glob(pattern), reverse=True)
    removed = []
    for f in files[keep:]:
        try:
            os.remove(f)
            removed.append(f)
        except OSError:
            pass
    return removed


def dump_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)