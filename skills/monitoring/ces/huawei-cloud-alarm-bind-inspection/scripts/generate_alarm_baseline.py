#!/usr/bin/env python3
"""
Read alarm baseline xlsx and generate JSON config for alarm bind inspection.

Reads CES指标基线 sheet, filters by 指标级别=底线指标,
then extracts specified columns (B/C/D/E/F/G/H/I/K/L/M/P/Q/R/S/T/U/V/AC/AD/AE/AF/AH/AI).

Usage:
    python generate_alarm_baseline.py [--input <xlsx_path>] [--output <json_path>]
"""

import argparse
import json
import sys
from pathlib import Path

from resource_type import SOURCE_TYPE_EVENTS
from workspace import INTERMEDIATE_DIR

try:
    import openpyxl
except ImportError:
    print("Error: openpyxl is required. Install with: pip install openpyxl")
    sys.exit(1)

DEFAULT_INPUT = str(Path(__file__).parent.parent / "assets" / "华为云租户面监控告警基线-V26.01-beta.xlsx")
DEFAULT_OUTPUT = str(Path(INTERMEDIATE_DIR) / "indicator_baseline.json")
DEFAULT_EVENT_OUTPUT = str(Path(INTERMEDIATE_DIR) / "event_baseline.json")

SHEET_NAME = "CES指标基线"
EVENT_SHEET_NAME = "CES事件基线"

FILTER_COLUMNS = {
    "指标级别": "底线指标",
}

EVENT_FILTER_COLUMNS = {
    "事件级别": "底线事件",
}

EXCLUDE_SERVICES = {"Modelarts"}

EXCLUDE_METRICS = {
    ("ELB", "m1_cps"),
    ("ELB", "m4_ncps"),
}

ECS_SPECIAL_EVENT_IDS = {
    "RoCELinkStatusDown",
    "gpuDRAMUncorrectableEccError",
    "DAVPSMICardNotFound",
    "DAVPLspciCardNotFound",
    "TemperatureOverSdLimit",
    "DeviceCoreAbnormal",
    "gpuDriverLinkFailureAlarm",
    "gpuPcieLinkFailureAlarm",
    "vmLostGpuAlarm",
    "FPGALinkFault",
    "UncorrectableEccErrorCount",
}

DEFAULT_ECS_SPECIAL_OUTPUT = str(Path(INTERMEDIATE_DIR) / "ecs_special_events.json")

# AOM sheet names
AOM_CCE_SHEET = "AOM指标基线-CCE"
AOM_OTHER_INDICATOR_SHEET = "AOM指标基线-其他服务"
AOM_MODELARTS_EVENT_SHEET = "AOM-Modelarts事件"
AOM_OTHER_EVENT_SHEET = "AOM事件基线-其他服务"

# AOM output paths
DEFAULT_AOM_INDICATOR_OUTPUT = str(Path(INTERMEDIATE_DIR) / "aom_indicator_baseline.json")
DEFAULT_AOM_EVENT_OUTPUT = str(Path(INTERMEDIATE_DIR) / "aom_event_baseline.json")

OUTPUT_COLUMNS = [
    ("B", "云服务中文名称"),
    ("C", "命名空间"),
    ("D", "云服务简称"),
    ("E", "指标维度-中文"),
    ("F", "指标维度"),
    ("G", "指标名称"),
    ("H", "指标ID"),
    ("I", "指标描述"),
    ("K", "采集周期（秒）"),
    ("L", "上报数据类型"),
    ("M", "默认单位"),
    ("P", "指标值类型"),
    ("Q", "连续触发次数"),
    ("R", "比较关系"),
    ("S", "重要告警阈值"),
    ("T", "紧急告警阈值"),
    ("U", "单位"),
    ("V", "告警频率"),
    ("AG", "备注"),
]

EVENT_OUTPUT_COLUMNS = [
    ("B", "云服务中文名称"),
    ("C", "命名空间"),
    ("D", "云服务简称"),
    ("E", "事件名称"),
    ("F", "事件ID"),
    ("G", "事件说明"),
    ("H", "处理建议"),
    ("I", "事件影响"),
]


def find_column_index(header_row, column_name):
    for i, val in enumerate(header_row):
        if val is not None and str(val).strip() == column_name:
            return i
    return None


def col_letter_to_index(letter):
    result = 0
    for ch in letter.upper():
        result = result * 26 + (ord(ch) - ord('A') + 1)
    return result - 1


def read_ces_sheet(ws, filter_columns, output_columns, exclude_services=None, exclude_metrics=None):
    header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))

    filter_indices = {}
    for col_name in filter_columns:
        idx = find_column_index(header_row, col_name)
        if idx is None:
            print(f"  Warning: filter column '{col_name}' not found, skipping sheet")
            return []
        filter_indices[col_name] = idx

    output_indices = {}
    for col_letter, col_name in output_columns:
        idx = col_letter_to_index(col_letter)
        if idx < len(header_row):
            actual = str(header_row[idx]).strip() if header_row[idx] is not None else ""
            if actual != col_name:
                print(f"  Warning: column at {col_letter} is '{actual}', expected '{col_name}', using letter index anyway")
        else:
            print(f"  Warning: column {col_letter} out of range, skipping")
            continue
        output_indices[col_name] = idx

    if not output_indices:
        print(f"  Warning: no output columns found, skipping sheet")
        return []

    max_col = max(
        max(filter_indices.values()),
        max(output_indices.values()),
    ) + 1

    total_rows = 0
    filter_stats = {col: 0 for col in filter_columns}
    results = []

    for row in ws.iter_rows(min_row=2, max_col=max_col, values_only=True):
        skip = False
        for col_name, expected in filter_columns.items():
            val = str(row[filter_indices[col_name]]).strip() if row[filter_indices[col_name]] is not None else ""
            if val != expected:
                filter_stats[col_name] += 1
                skip = True
                break
        if skip:
            continue

        record = {}
        for col_name, idx in output_indices.items():
            val = row[idx]
            record[col_name] = str(val).strip() if val is not None else ""

        if exclude_services and record.get("云服务简称") in exclude_services:
            continue

        if exclude_metrics and (record.get("云服务简称"), record.get("指标ID")) in exclude_metrics:
            continue

        if "环比" in record.get("比较关系", ""):
            continue

        results.append(record)
        total_rows += 1

    print(f"    Filtered stats: {filter_stats}")
    return results



# ---------------------------------------------------------------------------
# AOM baseline parsing (4 sheets, each with different column structure)
# ---------------------------------------------------------------------------

def _read_sheet_header(ws):
    """Read header row as list."""
    return list(next(ws.iter_rows(min_row=1, max_row=1, values_only=True)))


def _find_col(header, name):
    """Find column index by header name (fuzzy match)."""
    for i, val in enumerate(header):
        if val is not None and name in str(val).strip():
            return i
    return None


def _cell_str(val):
    return str(val).strip() if val is not None else ""


def read_aom_cce_indicator(ws):
    """Parse AOM指标基线-CCE sheet (18 cols, PromQL structure).

    Columns: 云服务(0), 指标维度(1), 指标名称(2), 指标ID(3), 指标描述(4),
    采集周期(5), 数据类型(6), 单位(7), 指标级别(8), 规则名称(9), PromQL语句(10),
    告警级别(11), 持续时间(12), 检查频率(13), 通知频率(14), 通知内容(15), 备注(16), 支柱-维度(17)
    """
    header = _read_sheet_header(ws)
    level_idx = _find_col(header, "指标级别")

    results = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        level = _cell_str(row[level_idx]) if level_idx is not None else ""
        if level != "底线指标":
            continue
        results.append({
            "source_sheet": "AOM指标基线-CCE",
            "云服务简称": "CCE",
            "命名空间": "CCE",
            "指标维度-中文": _cell_str(row[1]),
            "指标维度": _cell_str(row[1]),  # CCE uses Chinese dimension description
            "指标名称": _cell_str(row[2]),
            "指标ID": _cell_str(row[3]).strip(),  # note: has leading space in Excel
            "指标描述": _cell_str(row[4]),
            "采集周期": _cell_str(row[5]),
            "数据类型": _cell_str(row[6]),
            "单位": _cell_str(row[7]),
            "规则名称": _cell_str(row[9]),
            "PromQL": _cell_str(row[10]),
            "告警级别": _cell_str(row[11]),
            "备注": _cell_str(row[16]) if len(row) > 16 else "",
            "支柱-维度": _cell_str(row[17]) if len(row) > 17 else "",
        })
    return results


def read_aom_other_indicator(ws):
    """Parse AOM指标基线-其他服务 sheet (22 cols).

    Columns: NO.(0), 云服务简称(1), 命名空间(2), 指标维度-中文(3), 指标维度(4),
    指标名称(5), 指标ID(6), 默认单位(7), 是否评审(8), 指标级别(9), 统计周期(10),
    值类型(11), 运算符(12), 重要告警阈值(13), 紧急告警阈值(14), 连续周期(15),
    检查频率(16), 固定间隔时间(17), 告警恢复-连续周期(18), 无数据处理-连续周期(19),
    无数据处理-处理操作(20), 支柱-维度(21)
    """
    header = _read_sheet_header(ws)
    level_idx = _find_col(header, "指标级别")

    results = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        level = _cell_str(row[level_idx]) if level_idx is not None else ""
        if level != "底线指标":
            continue
        results.append({
            "source_sheet": "AOM指标基线-其他服务",
            "云服务简称": _cell_str(row[1]),
            "命名空间": _cell_str(row[2]),
            "指标维度-中文": _cell_str(row[3]),
            "指标维度": _cell_str(row[4]),
            "指标名称": _cell_str(row[5]),
            "指标ID": _cell_str(row[6]).strip(),
            "默认单位": _cell_str(row[7]),
            "统计周期": _cell_str(row[10]),
            "值类型": _cell_str(row[11]),
            "运算符": _cell_str(row[12]),
            "重要告警阈值": _cell_str(row[13]),
            "紧急告警阈值": _cell_str(row[14]),
            "连续周期": _cell_str(row[15]),
            "支柱-维度": _cell_str(row[21]) if len(row) > 21 else "",
        })
    return results


def read_aom_modelarts_event(ws):
    """Parse AOM-Modelarts事件 sheet (15 cols, PromQL event structure).

    Columns: 云服务(0), 指标维度(1), 指标名称(2), 指标ID(3), 指标描述(4),
    采集周期(5), 指标级别(6), 规则名称(7), PromQL语句(8), 告警级别(9),
    持续时间(10), 检查频率(11), 通知频率(12), 通知内容(13), 告警误报可能性(14)
    """
    header = _read_sheet_header(ws)
    level_idx = _find_col(header, "指标级别")

    results = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        level = _cell_str(row[level_idx]) if level_idx is not None else ""
        if level != "底线指标":
            continue
        results.append({
            "source_sheet": "AOM-Modelarts事件",
            "云服务简称": "Modelarts",
            "命名空间": "Modelarts",
            "事件ID": _cell_str(row[3]).strip(),
            "事件名称": _cell_str(row[2]),
            "event_name": _cell_str(row[2]),
            "指标维度": _cell_str(row[1]),
            "事件说明": _cell_str(row[4]),
            "采集周期": _cell_str(row[5]),
            "规则名称": _cell_str(row[7]),
            "PromQL": _cell_str(row[8]),
            "告警级别": _cell_str(row[9]),
            "告警误报可能性": _cell_str(row[14]) if len(row) > 14 else "",
        })
    return results


def read_aom_other_event(ws):
    """Parse AOM事件基线-其他服务 sheet (13 cols).

    Columns: 序号(0), 云服务简称(1), 事件ID(2), 事件名称(3), event_name(4),
    是否评审(5), 事件级别(6), 触发方式(7), 监控周期(8), 累计次数(9),
    频率(10), 告警级别(11), 支柱-维度(12)
    """
    header = _read_sheet_header(ws)
    level_idx = _find_col(header, "事件级别")

    results = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        level = _cell_str(row[level_idx]) if level_idx is not None else ""
        if level != "底线事件":
            continue
        results.append({
            "source_sheet": "AOM事件基线-其他服务",
            "云服务简称": _cell_str(row[1]),
            "命名空间": _cell_str(row[1]),
            "事件ID": _cell_str(row[2]),
            "事件名称": _cell_str(row[3]),
            "event_name": _cell_str(row[4]),
            "触发方式": _cell_str(row[7]),
            "监控周期": _cell_str(row[8]),
            "告警级别": _cell_str(row[11]) if len(row) > 11 else "",
            "支柱-维度": _cell_str(row[12]) if len(row) > 12 else "",
        })
    return results


def parse_aom_baselines(wb, input_path_name):
    """Parse all 4 AOM sheets and return (indicator_records, event_records)."""
    indicator_records = []
    event_records = []

    # AOM指标基线-CCE
    if AOM_CCE_SHEET in wb.sheetnames:
        print(f"  Processing sheet: {AOM_CCE_SHEET}")
        ws = wb[AOM_CCE_SHEET]
        records = read_aom_cce_indicator(ws)
        print(f"    Found {len(records)} records (底线指标)")
        indicator_records.extend(records)
    else:
        print(f"  Warning: sheet '{AOM_CCE_SHEET}' not found")

    # AOM指标基线-其他服务
    if AOM_OTHER_INDICATOR_SHEET in wb.sheetnames:
        print(f"  Processing sheet: {AOM_OTHER_INDICATOR_SHEET}")
        ws = wb[AOM_OTHER_INDICATOR_SHEET]
        records = read_aom_other_indicator(ws)
        print(f"    Found {len(records)} records (底线指标)")
        indicator_records.extend(records)
    else:
        print(f"  Warning: sheet '{AOM_OTHER_INDICATOR_SHEET}' not found")

    # AOM-Modelarts事件
    if AOM_MODELARTS_EVENT_SHEET in wb.sheetnames:
        print(f"  Processing sheet: {AOM_MODELARTS_EVENT_SHEET}")
        ws = wb[AOM_MODELARTS_EVENT_SHEET]
        records = read_aom_modelarts_event(ws)
        print(f"    Found {len(records)} records (底线指标)")
        event_records.extend(records)
    else:
        print(f"  Warning: sheet '{AOM_MODELARTS_EVENT_SHEET}' not found")

    # AOM事件基线-其他服务
    if AOM_OTHER_EVENT_SHEET in wb.sheetnames:
        print(f"  Processing sheet: {AOM_OTHER_EVENT_SHEET}")
        ws = wb[AOM_OTHER_EVENT_SHEET]
        records = read_aom_other_event(ws)
        print(f"    Found {len(records)} records (底线事件)")
        event_records.extend(records)
    else:
        print(f"  Warning: sheet '{AOM_OTHER_EVENT_SHEET}' not found")

    return indicator_records, event_records


def main():
    parser = argparse.ArgumentParser(description="Generate alarm bind inspection JSON from baseline xlsx")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to input xlsx file")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Path to output json file")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}")
        sys.exit(1)

    print(f"Reading: {input_path}")
    wb = openpyxl.load_workbook(str(input_path), data_only=True)

    if SHEET_NAME not in wb.sheetnames:
        print(f"Error: sheet '{SHEET_NAME}' not found in workbook")
        sys.exit(1)

    print(f"  Processing sheet: {SHEET_NAME}")
    print(f"  Filters: 指标级别=底线指标")
    ws = wb[SHEET_NAME]
    records = read_ces_sheet(ws, FILTER_COLUMNS, OUTPUT_COLUMNS, EXCLUDE_SERVICES, EXCLUDE_METRICS)
    print(f"    Found {len(records)} records after filtering")

    event_records = []
    ecs_special_events = []
    if EVENT_SHEET_NAME in wb.sheetnames:
        print(f"  Processing sheet: {EVENT_SHEET_NAME}")
        print(f"  Filters: 事件级别=底线事件")
        ws_event = wb[EVENT_SHEET_NAME]
        event_records = read_ces_sheet(ws_event, EVENT_FILTER_COLUMNS, EVENT_OUTPUT_COLUMNS)
        print(f"    Found {len(event_records)} records after filtering")

        ecs_special_events = [r for r in event_records if r.get("云服务简称") == "ECS" and r.get("事件ID") in ECS_SPECIAL_EVENT_IDS]
        before_count = len(event_records)
        event_records = [r for r in event_records if not (r.get("云服务简称") == "ECS" and r.get("事件ID") in ECS_SPECIAL_EVENT_IDS)]
        filtered_count = before_count - len(event_records)
        if filtered_count > 0:
            print(f"    Filtered {filtered_count} ECS special events (智算场景)")
        print(f"    Remaining event records: {len(event_records)}")
    else:
        print(f"  Warning: sheet '{EVENT_SHEET_NAME}' not found in workbook, skipping")

    event_dim_map = {}
    for item in SOURCE_TYPE_EVENTS:
        key = (item["namespace"], item["eventId"])
        if key not in event_dim_map:
            event_dim_map[key] = []
        event_dim_map[key].append(item["dimension"])

    matched_count = 0
    for record in event_records:
        key = (record.get("命名空间", ""), record.get("事件ID", ""))
        if key in event_dim_map:
            record["维度"] = event_dim_map[key]
            matched_count += 1
    print(f"    Added dimensions to {matched_count} event records")

    output_data = {
        "source": input_path.name,
        "sheet": SHEET_NAME,
        "filters": FILTER_COLUMNS,
        "total_records": len(records),
        "records": records,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\nGenerated: {output_path}")
    print(f"Total records: {len(records)}")

    event_output_path = Path(DEFAULT_EVENT_OUTPUT)
    event_output_data = {
        "source": input_path.name,
        "sheet": EVENT_SHEET_NAME,
        "filters": EVENT_FILTER_COLUMNS,
        "total_records": len(event_records),
        "records": event_records,
    }

    event_output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(event_output_path, "w", encoding="utf-8") as f:
        json.dump(event_output_data, f, ensure_ascii=False, indent=2)

    print(f"Generated: {event_output_path}")
    print(f"Total event records: {len(event_records)}")

    ecs_special_output_path = Path(DEFAULT_ECS_SPECIAL_OUTPUT)
    ecs_special_output_data = {
        "source": input_path.name,
        "description": "ECS智算场景特殊事件（已从事件基线中过滤）",
        "total_records": len(ecs_special_events),
        "records": ecs_special_events,
    }
    with open(ecs_special_output_path, "w", encoding="utf-8") as f:
        json.dump(ecs_special_output_data, f, ensure_ascii=False, indent=2)
    print(f"Generated: {ecs_special_output_path}")
    print(f"ECS special events: {len(ecs_special_events)}")

    # ---- AOM baseline parsing ----
    print(f"\n  --- AOM baseline ---")
    aom_indicator_records, aom_event_records = parse_aom_baselines(wb, input_path.name)

    aom_indicator_output = {
        "source": input_path.name,
        "sheets": [AOM_CCE_SHEET, AOM_OTHER_INDICATOR_SHEET],
        "total_records": len(aom_indicator_records),
        "records": aom_indicator_records,
    }
    aom_indicator_path = Path(DEFAULT_AOM_INDICATOR_OUTPUT)
    with open(aom_indicator_path, "w", encoding="utf-8") as f:
        json.dump(aom_indicator_output, f, ensure_ascii=False, indent=2)
    print(f"\nGenerated: {aom_indicator_path}")
    print(f"Total AOM indicator records: {len(aom_indicator_records)}")
    # Show breakdown by service
    from collections import Counter
    aom_svc = Counter(r.get("云服务简称", "") for r in aom_indicator_records)
    for k, v in sorted(aom_svc.items()):
        print(f"  {k}: {v}")

    aom_event_output = {
        "source": input_path.name,
        "sheets": [AOM_MODELARTS_EVENT_SHEET, AOM_OTHER_EVENT_SHEET],
        "total_records": len(aom_event_records),
        "records": aom_event_records,
    }
    aom_event_path = Path(DEFAULT_AOM_EVENT_OUTPUT)
    with open(aom_event_path, "w", encoding="utf-8") as f:
        json.dump(aom_event_output, f, ensure_ascii=False, indent=2)
    print(f"\nGenerated: {aom_event_path}")
    print(f"Total AOM event records: {len(aom_event_records)}")
    aom_evt_svc = Counter(r.get("云服务简称", "") for r in aom_event_records)
    for k, v in sorted(aom_evt_svc.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
