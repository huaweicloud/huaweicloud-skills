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
REQUIRED_COLUMNS = ["region", "实例类型", "实例ID", "入口实例ID"]
# Full required columns for assess-all (after expand has filled in 关键指标)
REQUIRED_COLUMNS_ASSESS = ["region", "实例类型", "实例ID", "关键指标", "入口实例ID"]
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
}

DATE_HEADER_RE = re.compile(r"^(\d{1,2})/(\d{1,2})(峰值|谷值)$")
KIND_ORDER = {"峰值": 0, "谷值": 1}


def norm_header(raw: Any) -> str:
    """Normalize a header: strip whitespace."""
    return re.sub(r"\s+", "", str(raw).strip())


def base_name(header: str) -> str:
    """Strip parenthesized suffixes like "（必填）" to get the base name.

    Both full-width "（）" and ASCII "()" are stripped, so a header written as
    "近一天(t-24)峰值" normalizes the same way as "近一天（t-24）峰值".
    """
    s = norm_header(header)
    s = re.sub(r"（[^）]*）", "", s)
    s = re.sub(r"\([^)]*\)", "", s)
    return s.strip()


# Column spelling aliases. The workbook template ships the t-24 output columns as
# "t-24峰值"/"t-24谷值"/…, while the writer emits "近一天（t-24）峰值"/…. Both spellings
# must resolve to the same physical column: a mismatch used to append a second copy of
# every t-24 column and write nothing into the template's own columns.
COLUMN_ALIASES: dict[str, str] = {
    "近一天峰值": "t-24峰值",
    "近一天谷值": "t-24谷值",
    "近一天峰谷值增长倍数": "t-24峰谷值增长倍数",
    "近一天压力系数": "t-24压力系数",
    "近一天预计节日上限": "t-24预计节日上限",
    "近一天是否需要扩容": "t-24是否需要扩容",
}


def canonical_name(header: Any) -> str:
    """Return the canonical key for a header: base name unified across known alias spellings."""
    b = base_name(header)
    return COLUMN_ALIASES.get(b, b)


def cell_get(cells: dict[str, Any], *names: str) -> Any:
    """Look up a cell value by header name, tolerating alias spellings.

    `cells` is keyed by normalized header (as returned in read_excel rows). Returns the
    first non-empty match, or None.
    """
    by_canonical: dict[str, Any] = {}
    for k, v in (cells or {}).items():
        c = canonical_name(k)
        if c and (c not in by_canonical or by_canonical[c] in (None, "")):
            by_canonical[c] = v
    for n in names:
        v = by_canonical.get(canonical_name(n))
        if v is not None and str(v).strip() != "":
            return v
    return None


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
    """Find a column index (1-based) by header name, normalizing both sides.

    Both the workbook header and the requested name are reduced to their canonical
    form, so "t-24峰值" (template) and "近一天（t-24）峰值" (writer) resolve to the
    same column.
    """
    target = canonical_name(base)
    for i in range(1, ws.max_column + 1):
        h = ws.cell(row=1, column=i).value
        if h is not None and canonical_name(h) == target:
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

    updates: [{"row": int, "column": "峰谷值倍数"|"近一天（t-24）峰值"|"7/1峰值", "value": any}, ...]
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
                # Prefer the template spelling of a known canonical column
                # (e.g. "近一天（t-24）峰值" -> "t-24峰值"), then look it up again
                # with the canonical name so the newly created column is found.
                canonical = CANONICAL_HEADERS.get(col) or canonical_name(col) or col
                ws.cell(row=1, column=ws.max_column + 1, value=canonical)
                idx = _find_column(ws, canonical)
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

# ---------------------------------------------------------------------------
# Row expansion (since v3.5)
# ---------------------------------------------------------------------------
# Columns to copy from the original row to inserted rows
COPY_COLUMNS_BASE = ["region", "实例类型", "实例ID", "入口实例ID", "活动增长倍数", "资源上限"]


def expand_excel(path: str,
                 expansions: list[dict[str, Any]],
                 sheet: Optional[str] = None) -> dict[str, Any]:
    """Expand rows: for each original row, fill in 关键指标/云服务维度/云服务维度资源ID
    on the original row (first metric), then insert N-1 new rows below with copied base
    info and each subsequent metric's three-column values.

    expansions: [{
        "row": int,               # original Excel row number
        "instance_id": str,
        "metrics": [              # ordered list of metrics to expand into
            {
                "关键指标": str,
                "云服务维度": str,
                "云服务维度资源ID": str,   # empty string if not needed
            }, ...
        ],
    }, ...]

    Returns: {ok, expanded_rows, inserted_rows, errors}
    """
    wb = load_workbook(path)
    try:
        if sheet is None:
            sheet = DEFAULT_SHEET if DEFAULT_SHEET in wb.sheetnames else wb.sheetnames[0]
        ws = wb[sheet]

        # Build column index map (canonical name -> 1-based column index)
        col_map: dict[str, int] = {}
        for i in range(1, ws.max_column + 1):
            h = ws.cell(row=1, column=i).value
            if h is not None:
                col_map[canonical_name(h)] = i

        # Ensure the three target columns exist
        for needed in ["关键指标", "云服务维度", "云服务维度资源ID"]:
            if needed not in col_map:
                ws.cell(row=1, column=ws.max_column + 1, value=needed)
                col_map[needed] = ws.max_column

        # Sort expansions by row number descending so insertions don't shift
        # earlier rows' positions
        expansions_sorted = sorted(expansions, key=lambda e: e["row"], reverse=True)

        total_inserted = 0
        errors = []
        expanded_count = 0

        for exp in expansions_sorted:
            orig_row = exp["row"]
            metrics = exp["metrics"]
            instance_id = exp.get("instance_id", "")
            if not metrics:
                errors.append({"row": orig_row, "error": "no metrics to expand"})
                continue

            # Fill in the first metric on the original row
            first = metrics[0]
            ws.cell(row=orig_row, column=col_map["关键指标"], value=first["关键指标"])
            ws.cell(row=orig_row, column=col_map["云服务维度"], value=first["云服务维度"])
            ws.cell(row=orig_row, column=col_map["云服务维度资源ID"], value=first["云服务维度资源ID"])

            # Insert N-1 rows for the remaining metrics
            remaining = metrics[1:]
            if remaining:
                ws.insert_rows(orig_row + 1, amount=len(remaining))

                # Copy base columns from original row to inserted rows
                copy_cols = []
                for base in COPY_COLUMNS_BASE:
                    if base in col_map:
                        copy_cols.append((base, col_map[base]))

                for offset, metric in enumerate(remaining):
                    new_row = orig_row + 1 + offset
                    # Copy base info from original row
                    for base, ci in copy_cols:
                        val = ws.cell(row=orig_row, column=ci).value
                        ws.cell(row=new_row, column=ci, value=val)
                    # Fill in the three columns
                    ws.cell(row=new_row, column=col_map["关键指标"], value=metric["关键指标"])
                    ws.cell(row=new_row, column=col_map["云服务维度"], value=metric["云服务维度"])
                    ws.cell(row=new_row, column=col_map["云服务维度资源ID"], value=metric["云服务维度资源ID"])

                total_inserted += len(remaining)

            expanded_count += 1

        # Atomic save
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
    return {"ok": True, "expanded_rows": expanded_count,
            "inserted_rows": total_inserted, "errors": errors}
