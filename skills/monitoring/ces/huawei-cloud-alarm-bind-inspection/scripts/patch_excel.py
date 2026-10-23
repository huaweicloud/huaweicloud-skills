#!/usr/bin/env python3
"""Merge AOM indicator sheet into the main CES sheet in generate_excel_report.py."""

with open("generate_excel_report.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add 监控体系 to HEADERS_NO_CUST
old_headers = '''HEADERS_NO_CUST = [
    "云服务类型", "核心实例ID", "Region", "指标维度", "底线指标配置百分比",
    "覆盖的指标", "未覆盖的指标",
    "告警规则名称", "模板名称", "模板类型", "模板是否与基线匹配", "优化建议",
]'''

new_headers = '''HEADERS_NO_CUST = [
    "监控体系", "云服务类型", "核心实例ID", "Region", "指标维度", "底线指标配置百分比",
    "覆盖的指标", "未覆盖的指标",
    "告警规则名称", "模板名称", "模板类型", "模板是否与基线匹配", "优化建议",
]'''

assert old_headers in content, "Could not find HEADERS_NO_CUST"
content = content.replace(old_headers, new_headers)

# 2. Update _write_report_sheet to prepend CES to every row
# The function builds `values` lists in 3 places. We need to prepend "CES" to each.
# Easiest: after the header loop, change all `values = [` to `values = ["CES",`
# But there are 3 `values = [` blocks. Let's replace each.

old_v1 = '''        values = [
                inst["service"],
                inst["instance_id"],
                inst.get("region", ""),
                dim_cn,
                inst["bind_rate"],
                "",
                uncovered_str,
                "",
                "",
                "",
                "",
                "需先创建告警规则",
            ]'''
new_v1 = '''        values = [
                "CES",
                inst["service"],
                inst["instance_id"],
                inst.get("region", ""),
                dim_cn,
                inst["bind_rate"],
                "",
                uncovered_str,
                "",
                "",
                "",
                "",
                "需先创建告警规则",
            ]'''
assert old_v1 in content, "Could not find values block 1 (no_rules)"
content = content.replace(old_v1, new_v1)

old_v2 = '''        values = [
                inst["service"],
                inst["instance_id"],
                inst.get("region", ""),
                dim_cn,
                inst["bind_rate"],
                "",
                "",
                "",
                "",
                "",
                "",
                "该服务无指标基线定义",
            ]'''
new_v2 = '''        values = [
                "CES",
                inst["service"],
                inst["instance_id"],
                inst.get("region", ""),
                dim_cn,
                inst["bind_rate"],
                "",
                "",
                "",
                "",
                "",
                "",
                "该服务无指标基线定义",
            ]'''
assert old_v2 in content, "Could not find values block 2 (no_baseline)"
content = content.replace(old_v2, new_v2)

old_v3 = '''        values = [
            inst["service"],
            inst["instance_id"],
            inst.get("region", ""),
            dim_display,
            inst["bind_rate"],
            "、".join(covered) if covered else "",
            "、".join(uncovered) if uncovered else "",
            rule_name_val,
            tpl_name_val,
            tpl_type_val,
            match_val,
            suggestion_val,
        ]'''
new_v3 = '''        values = [
            "CES",
            inst["service"],
            inst["instance_id"],
            inst.get("region", ""),
            dim_display,
            inst["bind_rate"],
            "、".join(covered) if covered else "",
            "、".join(uncovered) if uncovered else "",
            rule_name_val,
            tpl_name_val,
            tpl_type_val,
            match_val,
            suggestion_val,
        ]'''
assert old_v3 in content, "Could not find values block 3 (normal)"
content = content.replace(old_v3, new_v3)

# 3. Update _set_column_widths to add a column for 监控体系
old_widths = '''def _set_column_widths(ws):
    widths = [14, 36, 12, 20, 14, 40, 40, 30, 20, 14, 30, 30]'''
new_widths = '''def _set_column_widths(ws):
    widths = [10, 14, 36, 12, 20, 14, 40, 40, 30, 20, 14, 30, 30]'''
assert old_widths in content, "Could not find _set_column_widths"
content = content.replace(old_widths, new_widths)

# 4. Add _write_aom_rows function before generate()
aom_rows_func = '''

def _write_aom_rows(ws, aom_report, start_row):
    """Append AOM indicator rows to the main sheet, skipping instance_count=0."""
    items = aom_report.get("items", [])
    aom_items = [item for item in items if item.get("instance_count", 0) > 0]

    for offset, item in enumerate(aom_items):
        row_idx = start_row + offset
        covered_names = "、".join(
            item.get("metric_names", {}).get(mid, mid)
            for mid in item.get("covered_metrics", [])
        )
        uncovered_names = "、".join(
            item.get("metric_names", {}).get(mid, mid)
            for mid in item.get("uncovered_metrics", [])
        )

        status = item.get("status", "")
        if status == "no_online_rules":
            suggestion = "需先创建AOM告警规则"
        elif item.get("bind_rate") == "100.0%":
            suggestion = "已达标"
        else:
            suggestion = "人工复核"

        values = [
            "AOM",
            item.get("云服务简称", ""),
            "(服务级)",
            "",
            item.get("指标维度-中文", item.get("指标维度", "")),
            item.get("bind_rate", "N/A"),
            covered_names,
            uncovered_names,
            "",
            "",
            "",
            "",
            suggestion,
        ]

        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=(col >= 6))

        # Color bind rate (column 6)
        rate_str = item.get("bind_rate", "")
        rate_cell = ws.cell(row=row_idx, column=6)
        if rate_str and rate_str != "N/A":
            try:
                rate_val = float(rate_str.rstrip("%"))
                if rate_val < 100:
                    rate_cell.fill = RED_FILL
                    rate_cell.font = RED_FONT
                else:
                    rate_cell.fill = GREEN_FILL
                    rate_cell.font = GREEN_FONT
            except ValueError:
                pass

    return len(aom_items)

'''

# Insert before generate() function
old_generate_start = "def generate(input_path, output_path, rules_path, baseline_path):"
assert old_generate_start in content, "Could not find generate() function"
content = content.replace(old_generate_start, aom_rows_func + old_generate_start)

# 5. Update generate() to use merged sheet instead of separate AOM sheet
old_aom_sheet = '''    # Add AOM indicator sheet if available
    try:
        aom_report = load_json(DEFAULT_AOM_INPUT)
        if aom_report and aom_report.get("items"):
            ws_aom = wb.create_sheet(title="AOM指标绑定率")
            _write_aom_sheet(ws_aom, aom_report)
            logger.info(f"AOM indicator sheet added: {len(aom_report['items'])} rows")
    except Exception as e:
        logger.warning(f"Failed to add AOM sheet: {e}")'''

new_aom_sheet = '''    # Merge AOM indicator rows into the main sheet
    try:
        aom_report = load_json(DEFAULT_AOM_INPUT)
        if aom_report and aom_report.get("items"):
            aom_count = _write_aom_rows(ws, aom_report, len(instances) + 2)
            logger.info(f"AOM indicator rows merged: {aom_count} rows")
    except Exception as e:
        logger.warning(f"Failed to merge AOM rows: {e}")'''

assert old_aom_sheet in content, "Could not find AOM sheet block in generate()"
content = content.replace(old_aom_sheet, new_aom_sheet)

# 6. Rename sheet title
old_title = 'ws.title = "底线指标绑定率"'
new_title = 'ws.title = "指标基线绑定率"'
assert old_title in content, "Could not find sheet title"
content = content.replace(old_title, new_title)

# 7. Update auto_filter in _write_report_sheet to include 监控体系 column
# The filter ref is set in _set_column_widths or at the end of _write_report_sheet
# Let's check if there's an auto_filter in _write_report_sheet
# Actually, looking at the code, _write_report_sheet calls _set_column_widths at the end
# and there's no auto_filter set for the main sheet. So no change needed.

with open("generate_excel_report.py", "w", encoding="utf-8") as f:
    f.write(content)

print("generate_excel_report.py updated: AOM merged into main sheet with 监控体系 column")
