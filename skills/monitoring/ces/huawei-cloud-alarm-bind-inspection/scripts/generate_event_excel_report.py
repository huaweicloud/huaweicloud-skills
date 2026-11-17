#!/usr/bin/env python3
import json
import argparse
import logging
from pathlib import Path
from collections import defaultdict
from workspace import WORKSPACE_DIR, INTERMEDIATE_DIR

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
except ImportError:
    print("Error: openpyxl is required. Install with: pip install openpyxl")
    raise

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("event-excel-report")

DEFAULT_INPUT = str(Path(INTERMEDIATE_DIR) / "event_bind_report.json")
DEFAULT_OUTPUT = str(Path(WORKSPACE_DIR) / "event_bind_report.xlsx")
DEFAULT_NOTIFICATION_RULES = str(Path(INTERMEDIATE_DIR) / "online_notification_rules.json")
DEFAULT_AOM_NOTIFICATION_RULES = str(Path(INTERMEDIATE_DIR) / "aom_notification_rules.json")
DEFAULT_AOM_EVENT_INPUT = str(Path(INTERMEDIATE_DIR) / "aom_event_bind_report.json")

HEADER_FONT = Font(bold=True, size=11)
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT_WHITE = Font(bold=True, size=11, color="FFFFFF")
RED_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
RED_FONT = Font(color="9C0006")
GREEN_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
GREEN_FONT = Font(color="006100")
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

HEADERS = [
    "监控体系",
    "云服务-维度",
    "实例ID",
    "Region",
    "底线事件配置百分比",
    "覆盖的事件",
    "未覆盖的事件",
    "通知规则名称",
    "优化建议",
]


BASELINE_TO_RULE_SVC = {
    "RDS": "RDS", "GeminiDB": "NoSQL", "ECS": "ECS", "BMS": "BMS",
    "DDS": "DDS", "GAUSSDB": "GAUSSDB", "DCS": "DCS", "TaurusDB": "GAUSSDBV5",
    "DDM": "DMS", "OBS": "OBS", "EIP": "EIP", "GEIP": "EIP",
    "CBR": "CBR", "GA": "GA", "HSS": "HSS", "ELB": "ELB",
    "SecMaster": "SecMaster", "CSMS": "CSMS", "modelarts": "ModelArts",
    "SFSTurbo": "EFS",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_event_to_rule_names(notification_rules_path):
    rules_data = load_json(notification_rules_path)
    mapping = defaultdict(set)
    for rule in rules_data.get("rules", []):
        rule_name = rule.get("name", "")
        if not rule_name:
            continue
        svc = rule.get("service", "")
        region = rule.get("region", "")
        for eid in rule.get("event_ids", []):
            if svc and eid:
                mapping[(svc, eid, region)].add(rule_name)
    return {k: sorted(v) for k, v in mapping.items()}


def _build_aom_event_to_rule_names(aom_rules_path):
    """Build (service, event_id, region) -> alarm_rule_name mapping for AOM rules.

    Uses the same service extraction as event_bind_analysis._extract_aom_rule_service.
    Event IDs are extracted from multiple sources:
    1. monitor_objects[].event_name (format: "displayName##eventId", ";"-separated)
    2. trigger_conditions[].event_name (same format)
    3. alias field (fallback when event_name is empty)
    """
    rules_data = load_json(aom_rules_path)
    mapping = defaultdict(set)
    for rule in rules_data.get("rules", []):
        rule_name = rule.get("alarm_rule_name", "")
        if not rule_name:
            continue
        spec = rule.get("event_alarm_spec", {})
        # Service extraction (same logic as _extract_aom_rule_service)
        alarm_source = spec.get("alarm_source", "")
        event_source = spec.get("event_source", "")
        if alarm_source == "CCE":
            svc = "CCE"
        elif alarm_source == "systemEvent" and event_source:
            svc = "Modelarts" if event_source.lower() == "modelarts" else event_source
        else:
            svc = alarm_source or event_source
        if not svc:
            continue
        region = rule.get("region", "")
        # Event ID extraction from multiple sources
        event_ids = set()

        def _parse_event_name(en):
            if not en:
                return
            for part in en.split(";"):
                part = part.strip()
                if not part:
                    continue
                if "##" in part:
                    eid = part.split("##")[-1].strip()
                else:
                    eid = part
                if eid:
                    event_ids.add(eid)

        for o in spec.get("monitor_objects", []):
            _parse_event_name(o.get("event_name", ""))
        for tc in spec.get("trigger_conditions", []):
            _parse_event_name(tc.get("event_name", ""))
        # Fallback: alias field
        if not event_ids:
            alias = rule.get("alias", "")
            if alias:
                event_ids.add(alias)
        for eid in event_ids:
            mapping[(svc, eid, region)].add(rule_name)
    return {k: sorted(v) for k, v in mapping.items()}


AOM_EVENT_HEADERS = [
    "云服务类型", "底线事件数", "已覆盖数",
    "绑定率", "覆盖的事件", "未覆盖的事件",
    "核心实例数", "状态", "优化建议",
]


def _write_aom_event_sheet(ws, aom_report):
    """Write AOM event bind analysis as a separate sheet."""
    items = aom_report.get("items", [])
    summary = aom_report.get("summary", {})

    # Summary row
    ws.cell(row=1, column=1, value=f"AOM事件基线绑定率汇总："
            f"总底线事件 {summary.get('total_baseline_events', 0)}，"
            f"已覆盖 {summary.get('total_covered', 0)}，"
            f"覆盖率 {summary.get('overall_coverage', 'N/A')}").font = Font(bold=True, size=12)

    # Headers
    for col, h in enumerate(AOM_EVENT_HEADERS, 1):
        cell = ws.cell(row=3, column=col, value=h)
        cell.font = HEADER_FONT_WHITE
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    for row_idx, item in enumerate(items, 4):
        covered_names = "、".join(
            item.get("event_names", {}).get(eid, eid)
            for eid in item.get("covered_events", [])
        )
        uncovered_names = "、".join(
            item.get("event_names", {}).get(eid, eid)
            for eid in item.get("uncovered_events", [])
        )

        status = item.get("status", "")
        if status == "no_core_instances":
            suggestion = "该服务无核心实例，暂不评估"
        elif status == "no_online_rules":
            suggestion = "需先创建AOM事件告警规则"
        elif item.get("bind_rate") == "100.0%":
            suggestion = "已达标"
        else:
            suggestion = "人工复核"

        values = [
            item.get("云服务简称", ""),
            item.get("baseline_count", 0),
            item.get("covered_count", 0),
            item.get("bind_rate", "N/A"),
            covered_names,
            uncovered_names,
            item.get("instance_count", 0),
            status,
            suggestion,
        ]

        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=(col >= 5))

    widths = [14, 12, 10, 12, 50, 50, 12, 18, 20]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    ws.auto_filter.ref = f"A3:{openpyxl.utils.get_column_letter(len(AOM_EVENT_HEADERS))}{3 + len(items)}"




def _write_aom_event_rows(ws, aom_report, start_row):
    """Append AOM event rows to the main sheet, skipping instance_count=0."""
    items = aom_report.get("items", [])
    aom_items = [item for item in items if item.get("instance_count", 0) > 0]

    for offset, item in enumerate(aom_items):
        row_idx = start_row + offset
        covered_names = "、".join(
            item.get("event_names", {}).get(eid, eid)
            for eid in item.get("covered_events", [])
        )
        uncovered_names = "、".join(
            item.get("event_names", {}).get(eid, eid)
            for eid in item.get("uncovered_events", [])
        )

        status = item.get("status", "")
        if status == "no_online_rules":
            suggestion = "需先创建AOM事件告警规则"
        elif item.get("bind_rate") == "100.0%":
            suggestion = "已达标"
        else:
            suggestion = "人工复核"

        values = [
            "AOM",
            item.get("云服务简称", ""),
            "(服务级)",
            "",
            item.get("bind_rate", "N/A"),
            covered_names,
            uncovered_names,
            "",
            suggestion,
        ]

        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=(col >= 5))

        rate_str = item.get("bind_rate", "")
        rate_cell = ws.cell(row=row_idx, column=5)
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

def generate(report_path, output_path, notification_rules_path=None, aom_notification_rules_path=None):
    report = load_json(report_path)
    by_instance_all = report.get("by_instance", [])

    event_to_rules = {}
    if notification_rules_path:
        try:
            event_to_rules = _build_event_to_rule_names(notification_rules_path)
        except Exception as e:
            logger.warning(f"Failed to load notification rules for rule name mapping: {e}")

    aom_event_to_rules = {}
    if aom_notification_rules_path:
        try:
            aom_event_to_rules = _build_aom_event_to_rule_names(aom_notification_rules_path)
        except Exception as e:
            logger.warning(f"Failed to load AOM notification rules for rule name mapping: {e}")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "事件基线绑定率"

    for col_idx, header in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT_WHITE
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    row_idx = 2
    for inst in by_instance_all:
            covered_names = ", ".join(ev.get("事件ID", "") for ev in inst.get("covered_events", []))
            missing_names = ", ".join(ev.get("事件ID", "") for ev in inst.get("missing_events", []))

            rule_names_set = set()
            inst_ms = inst.get("monitor_system", "CES")
            rule_map = aom_event_to_rules if inst_ms == "AOM" else event_to_rules
            inst_region = inst.get("region", "")
            for ev in inst.get("covered_events", []):
                svc = ev.get("云服务简称", "")
                eid = ev.get("事件ID", "")
                if svc and eid:
                    rule_svc = BASELINE_TO_RULE_SVC.get(svc, svc)
                    matched = rule_map.get((rule_svc, eid, inst_region), [])
                    rule_names_set.update(matched)
            rule_names_str = ", ".join(sorted(rule_names_set))

            if inst.get("bound_status") == "no_baseline":
                suggestion = "该服务无事件基线"
            elif inst.get("bind_rate") == "100.0%":
                suggestion = "已达标"
            else:
                suggestion = "人工复核"

            row_data = [
                inst.get("monitor_system", "CES"),
                inst.get("svc_dim", inst.get("service", "")),
                inst.get("instance_id", ""),
                inst.get("region", ""),
                inst.get("bind_rate", "N/A"),
                covered_names,
                missing_names,
                rule_names_str,
                suggestion,
            ]

            for col_idx, val in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.border = THIN_BORDER
                cell.alignment = Alignment(vertical="center", wrap_text=(col_idx >= 5))

            # Style "该服务无事件基线" suggestion cell with red fill + red font
            if suggestion == "该服务无事件基线":
                suggestion_cell = ws.cell(row=row_idx, column=9)
                suggestion_cell.fill = RED_FILL
                suggestion_cell.font = RED_FONT

            row_idx += 1

    col_widths = [10, 14, 40, 18, 18, 50, 50, 30, 20]
    for i, width in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width

    ws.auto_filter.ref = ws.dimensions

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    logger.info(f"Event Excel report saved to {output_path}")
    logger.info(f"Total rows: {row_idx - 2}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate event baseline binding rate Excel report")
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--notification-rules", default=DEFAULT_NOTIFICATION_RULES, help="Path to online_notification_rules.json for rule name mapping")
    parser.add_argument("--aom-notification-rules", default=DEFAULT_AOM_NOTIFICATION_RULES, help="Path to aom_notification_rules.json for AOM rule name mapping")
    args = parser.parse_args()
    generate(args.input, args.output, notification_rules_path=args.notification_rules, aom_notification_rules_path=args.aom_notification_rules)
