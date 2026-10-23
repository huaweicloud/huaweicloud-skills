#!/usr/bin/env python3
import json
import argparse
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime

from suggestion_data import (
    DEFAULT_AOM_INDICATOR_REPORT,
    DEFAULT_AOM_EVENT_REPORT,
    load_json,
    convert_svc_summary_to_stat_data,
    process_report_instances,
    build_svc_summary,
    METRIC_DETAIL_COLUMNS,
    EVENT_DETAIL_COLUMNS,
    DEFAULT_BIND_REPORT,
    DEFAULT_BASELINE,
    DEFAULT_RULES,
    DEFAULT_EVENT_REPORT,
    DEFAULT_EVENT_BASELINE,
    DEFAULT_OUTPUT,
)
from suggestion_html import build_event_section, build_html
from workspace import INTERMEDIATE_DIR


def _build_svc_options(by_service_dimension):
    svc_options_data = [{"value": "", "label": "全部服务"}]
    for svc_dim_key in sorted(by_service_dimension.keys()):
        if svc_dim_key.endswith("|无指标基线"):
            continue
        display_name = svc_dim_key.replace("|", " - ") if "|" in svc_dim_key else svc_dim_key
        svc_options_data.append({"value": svc_dim_key, "label": display_name})
    return svc_options_data


def _build_event_svc_options(event_svc_stat_data):
    event_svc_options_data = [{"value": "", "label": "全部服务"}]
    seen = set()
    for item in event_svc_stat_data:
        s = item.get("svc", "")
        if s and s not in seen:
            seen.add(s)
            event_svc_options_data.append({"value": s, "label": s})
    return event_svc_options_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("suggestion")



def _build_aom_indicator_html(aom_indicator_report):
    """Build AOM indicator bind analysis HTML card for the metric tab."""
    if not aom_indicator_report:
        return ""
    summary = aom_indicator_report.get("summary", {})
    items = aom_indicator_report.get("items", [])

    parts = ['<div class="card" style="margin-top:20px;">']
    parts.append('<h2 class="card-header">概览</h2>')
    parts.append(f'<div class="stat-grid" style="margin-bottom:16px;">'
                 f'<div class="stat-item"><div class="value">{summary.get("total_baseline_metrics", 0)}</div><div class="label">AOM底线指标总数</div></div>'
                 f'<div class="stat-item"><div class="value danger">{summary.get("total_covered", 0)}</div><div class="label">已覆盖</div></div>'
                 f'<div class="stat-item"><div class="value">{summary.get("overall_coverage", "N/A")}</div><div class="label">覆盖率</div></div>'
                 f'</div>')

    parts.append('<div class="tab-label primary">AOM指标绑定明细</div>')
    parts.append('<div class="tab-table-wrap"><table class="svc-summary-table">')
    parts.append('<thead><tr><th>云服务</th><th>指标维度</th><th>底线数</th><th>覆盖数</th><th>绑定率</th><th>实例数</th><th>状态</th></tr></thead><tbody>')
    for item in items:
        parts.append(f'<tr>'
                     f'<td>{item.get("云服务简称", "")}</td>'
                     f'<td>{item.get("指标维度-中文", "")}</td>'
                     f'<td>{item.get("baseline_count", 0)}</td>'
                     f'<td>{item.get("covered_count", 0)}</td>'
                     f'<td>{item.get("bind_rate", "N/A")}</td>'
                     f'<td>{item.get("instance_count", 0)}</td>'
                     f'<td>{item.get("status", "")}</td>'
                     f'</tr>')
    parts.append('</tbody></table></div>')
    parts.append('</div>')
    return "\n".join(parts)


def _build_aom_event_html(aom_event_report):
    """Build AOM event bind analysis HTML card for the event tab."""
    if not aom_event_report:
        return ""
    summary = aom_event_report.get("summary", {})
    items = aom_event_report.get("items", [])

    parts = ['<div class="card" style="margin-top:20px;">']
    parts.append('<h2 class="card-header">概览</h2>')
    parts.append(f'<div class="stat-grid" style="margin-bottom:16px;">'
                 f'<div class="stat-item"><div class="value">{summary.get("total_baseline_events", 0)}</div><div class="label">AOM底线事件总数</div></div>'
                 f'<div class="stat-item"><div class="value danger">{summary.get("total_covered", 0)}</div><div class="label">已覆盖</div></div>'
                 f'<div class="stat-item"><div class="value">{summary.get("overall_coverage", "N/A")}</div><div class="label">覆盖率</div></div>'
                 f'</div>')

    parts.append('<div class="tab-label primary">AOM事件绑定明细</div>')
    parts.append('<div class="tab-table-wrap"><table class="svc-summary-table">')
    parts.append('<thead><tr><th>云服务</th><th>底线数</th><th>覆盖数</th><th>绑定率</th><th>实例数</th><th>状态</th></tr></thead><tbody>')
    for item in items:
        parts.append(f'<tr>'
                     f'<td>{item.get("云服务简称", "")}</td>'
                     f'<td>{item.get("baseline_count", 0)}</td>'
                     f'<td>{item.get("covered_count", 0)}</td>'
                     f'<td>{item.get("bind_rate", "N/A")}</td>'
                     f'<td>{item.get("instance_count", 0)}</td>'
                     f'<td>{item.get("status", "")}</td>'
                     f'</tr>')
    parts.append('</tbody></table></div>')
    parts.append('</div>')
    return "\n".join(parts)



def merge_aom_into_ces(metric_overview, metric_svc_stat_data, rows_data,
                       aom_indicator_report, aom_baseline_records, core_instances):
    """Merge AOM indicator bind report data into CES data structures.

    (a) Overview: unified coverage rate (CES baseline + AOM baseline, CES covered + AOM covered)
    (b) Service stats: derive fully/partially/unbound from covered_count vs baseline_count
    (c) Detail rows: map AOM baseline fields to CES METRIC_DETAIL_COLUMNS
    """
    if not aom_indicator_report:
        return metric_overview, metric_svc_stat_data, rows_data

    aom_summary = aom_indicator_report.get("summary", {})
    aom_items = aom_indicator_report.get("items", [])

    # --- (a) Merge overview ---
    ces_total_baseline = metric_overview.get("total_baseline_metrics", 0)
    ces_total_covered = metric_overview.get("total_covered", 0)
    aom_total_baseline = aom_summary.get("total_baseline_metrics", 0)
    aom_total_covered = aom_summary.get("total_covered", 0)

    unified_baseline = ces_total_baseline + aom_total_baseline
    unified_covered = ces_total_covered + aom_total_covered
    unified_rate = f"{unified_covered / unified_baseline * 100:.1f}%" if unified_baseline > 0 else "N/A"

    # Count AOM instances needing action (items with uncovered metrics and core instances)
    aom_needing = 0
    aom_missing = 0
    for item in aom_items:
        if item.get("instance_count", 0) > 0 and item.get("uncovered_metrics"):
            aom_needing += item["instance_count"]
            aom_missing += len(item["uncovered_metrics"])

    merged_overview = {
        "total_instances": metric_overview.get("total_instances", 0),
        "instances_needing_action": metric_overview.get("instances_needing_action", 0) + aom_needing,
        "total_missing": metric_overview.get("total_missing", 0) + aom_missing,
        "coverage_rate": unified_rate,
        "total_baseline_metrics": unified_baseline,
        "total_covered": unified_covered,
    }

    # --- (b) Merge service stats ---
    for item in aom_items:
        if item.get("instance_count", 0) == 0:
            continue  # skip services without core instances
        svc = item.get("云服务简称", "")
        dim_cn = item.get("指标维度-中文", item.get("指标维度", ""))
        baseline_count = item.get("baseline_count", 0)
        covered_count = item.get("covered_count", 0)
        instance_count = item.get("instance_count", 0)
        status = item.get("status", "")
        bind_rate = item.get("bind_rate", "N/A")

        # Derive fully/partially/unbound
        if status == "no_core_instances" or instance_count == 0:
            fully, partially, unbound = 0, 0, 0
        elif covered_count == baseline_count and baseline_count > 0:
            fully, partially, unbound = instance_count, 0, 0
        elif covered_count == 0:
            fully, partially, unbound = 0, 0, instance_count
        else:
            fully, partially, unbound = 0, instance_count, 0

        svc_dim_display = f"{svc} - {dim_cn}" if dim_cn else svc
        is_no_rules = (status == "no_online_rules")

        metric_svc_stat_data.append({
            "svc_dim": svc_dim_display,
            "total_inst": instance_count,
            "baseline_metrics_count": baseline_count,
            "fully": fully,
            "partially": partially,
            "unbound": unbound,
            "bind_rate": bind_rate,
            "missing_metrics": len(item.get("uncovered_metrics", [])),
            "is_no_rules": False,
            "is_no_baseline": False,
            "bound_baseline": covered_count,
            "total_baseline": baseline_count,
            "monitor_system": "AOM",
        })

    # --- (c) Merge detail rows ---
    # Build lookup: (云服务简称, 指标ID) -> baseline record
    baseline_lookup = {}
    for rec in aom_baseline_records:
        svc = rec.get("云服务简称", "")
        mid = rec.get("指标ID", "").strip()
        if mid:
            baseline_lookup[(svc, mid)] = rec

    for item in aom_items:
        if item.get("instance_count", 0) == 0:
            continue  # skip services without core instances
        svc = item.get("云服务简称", "")
        dim = item.get("指标维度", "")
        dim_cn = item.get("指标维度-中文", dim)
        uncovered = item.get("uncovered_metrics", [])
        if not uncovered:
            continue

        # Get instance info
        insts = core_instances.get(svc, [])
        if insts:
            inst_id = insts[0].get("instance_id", "")
            region = insts[0].get("region", "")
        else:
            inst_id = "服务级"
            region = ""

        for mid in uncovered:
            rec = baseline_lookup.get((svc, mid.strip()))
            if not rec:
                # Fallback: create minimal row
                row = {
                    "instance_id": inst_id, "region": region,
                    "service": svc, "metric_dimension": dim,
                    "metric_dimension_cn": dim_cn, "monitor_system": "AOM",
                }
                for _, col_key in METRIC_DETAIL_COLUMNS:
                    row[col_key] = mid if col_key == "指标ID" else ""
                rows_data.append(row)
                continue

            # Map AOM fields to CES METRIC_DETAIL_COLUMNS
            source_sheet = rec.get("source_sheet", "")
            row = {
                "instance_id": inst_id, "region": region,
                "service": svc, "metric_dimension": dim,
                "metric_dimension_cn": dim_cn, "monitor_system": "AOM",
            }

            for col_label, col_key in METRIC_DETAIL_COLUMNS:
                if col_key == "指标ID":
                    row[col_key] = rec.get("指标ID", mid)
                elif col_key == "指标名称":
                    row[col_key] = rec.get("指标名称", "")
                elif col_key == "命名空间":
                    row[col_key] = rec.get("命名空间", "")
                elif col_key == "重要告警阈值":
                    row[col_key] = rec.get("重要告警阈值", "")
                elif col_key == "紧急告警阈值":
                    row[col_key] = rec.get("紧急告警阈值", "")
                elif col_key == "告警频率":
                    row[col_key] = ""
                elif col_key == "采集周期（秒）":
                    # CCE has 采集周期, 其他服务 has 统计周期
                    row[col_key] = rec.get("采集周期", rec.get("统计周期", ""))
                elif col_key == "比较关系":
                    # 其他服务 has 运算符
                    row[col_key] = rec.get("运算符", "")
                elif col_key == "连续触发次数":
                    # 其他服务 has 连续周期
                    row[col_key] = rec.get("连续周期", "")
                elif col_key == "默认单位":
                    # CCE has 单位, 其他服务 has 默认单位
                    row[col_key] = rec.get("默认单位", rec.get("单位", ""))
                elif col_key == "备注":
                    row[col_key] = rec.get("备注", "")
                else:
                    row[col_key] = ""

            rows_data.append(row)

    return merged_overview, metric_svc_stat_data, rows_data



def merge_aom_event_into_ces(event_overview_json, event_svc_stat_data, event_rows_data,
                             aom_event_report, aom_event_baseline_records, core_instances):
    """Merge AOM event bind report data into CES event data structures.

    (a) Overview: unified event coverage (CES + AOM baseline events, CES + AOM covered)
    (b) Service stats: convert AOM event items to CES event svc stat format, skip instance_count=0
    (c) Detail rows: map AOM uncovered_events to CES event detail format (事件ID, 事件名称)
    """
    if not aom_event_report:
        return event_overview_json, event_svc_stat_data, event_rows_data

    aom_summary = aom_event_report.get("summary", {})
    aom_items = aom_event_report.get("items", [])

    # --- (a) Merge overview ---
    ces_overview = json.loads(event_overview_json) if event_overview_json and event_overview_json != "{}" else {}
    ces_total_baseline = ces_overview.get("total_baseline_events", 0)
    ces_total_covered = ces_overview.get("total_covered_events", 0)
    aom_total_baseline = aom_summary.get("total_baseline_events", 0)
    aom_total_covered = aom_summary.get("total_covered", 0)

    unified_baseline = ces_total_baseline + aom_total_baseline
    unified_covered = ces_total_covered + aom_total_covered
    unified_rate = f"{unified_covered / unified_baseline * 100:.1f}%" if unified_baseline > 0 else "N/A"

    # Count AOM instances needing action (only items with instances)
    aom_needing = 0
    aom_missing = 0
    for item in aom_items:
        if item.get("instance_count", 0) > 0 and item.get("uncovered_events"):
            aom_needing += item["instance_count"]
            aom_missing += len(item["uncovered_events"])

    merged_overview = {
        "total_instances": ces_overview.get("total_instances", 0),
        "bound_instances": ces_overview.get("bound_instances", 0),
        "overall_rate": unified_rate,
        "total_covered_events": unified_covered,
        "total_baseline_events": unified_baseline,
        "missing_events_total": ces_overview.get("missing_events_total", 0) + aom_missing,
        "no_rules_instances": ces_overview.get("no_rules_instances", 0),
        "no_baseline_instances": ces_overview.get("no_baseline_instances", 0),
    }
    merged_overview_json = json.dumps(merged_overview, ensure_ascii=False)

    # --- (b) Merge service stats ---
    for item in aom_items:
        if item.get("instance_count", 0) == 0:
            continue  # skip services without core instances
        svc = item.get("云服务简称", "")
        baseline_count = item.get("baseline_count", 0)
        covered_count = item.get("covered_count", 0)
        instance_count = item.get("instance_count", 0)
        bind_rate = item.get("bind_rate", "N/A")

        # Derive fully/partially/unbound
        if covered_count == baseline_count and baseline_count > 0:
            fully, partially, unbound = instance_count, 0, 0
        elif covered_count == 0:
            fully, partially, unbound = 0, 0, instance_count
        else:
            fully, partially, unbound = 0, instance_count, 0

        event_svc_stat_data.append({
            "svc": svc,
            "total_instances": instance_count,
            "fully_bound": fully,
            "partially_bound": partially,
            "unbound": unbound,
            "no_online_rules": 0,
            "baseline_event_count": baseline_count,
            "covered_baseline": covered_count,
            "total_baseline": baseline_count,
            "bind_rate": bind_rate,
            "monitor_system": "AOM",
        })

    # --- (c) Merge detail rows ---
    # Build lookup: (云服务简称, 事件ID) -> baseline record
    baseline_lookup = {}
    for rec in aom_event_baseline_records:
        svc = rec.get("云服务简称", "")
        eid = rec.get("事件ID", "").strip()
        if eid:
            baseline_lookup[(svc, eid)] = rec

    for item in aom_items:
        if item.get("instance_count", 0) == 0:
            continue  # skip services without core instances
        svc = item.get("云服务简称", "")
        uncovered = item.get("uncovered_events", [])
        event_names = item.get("event_names", {})
        if not uncovered:
            continue

        # Get instance info
        insts = core_instances.get(svc, [])
        if insts:
            inst_id = insts[0].get("instance_id", "")
            region = insts[0].get("region", "")
        else:
            inst_id = "服务级"
            region = ""

        for eid in uncovered:
            row = {
                "instance_id": inst_id,
                "region": region,
                "svc": svc,
                "monitor_system": "AOM",
                "事件ID": eid,
                "事件名称": event_names.get(eid, ""),
            }
            event_rows_data.append(row)

    return merged_overview_json, event_svc_stat_data, event_rows_data


def generate(bind_report_path, baseline_path, output_path, rules_path=None, event_report_path=None, event_baseline_path=None):
    report = load_json(bind_report_path)
    baseline = load_json(baseline_path)

    baseline_by_svc_dim = defaultdict(dict)
    for rec in baseline["records"]:
        svc = rec["云服务简称"]
        dim = rec.get("指标维度", "")
        baseline_by_svc_dim[(svc, dim)][rec["指标ID"]] = rec

    logger.info("Generating suggestion report")
    suggestions, total_missing_metrics, instances_needing_action_ids, total_bound_all, total_baseline_all, no_baseline_instances, non_exist_instances = \
        process_report_instances(report, baseline_by_svc_dim)

    suggestions.sort(key=lambda x: (x["service"], x.get("metric_dimension", ""), x["baseline_metrics_missing"]), reverse=False)

    svc_summary = build_svc_summary(suggestions, report.get("by_service_dimension", {}))

    if total_baseline_all > 0:
        metric_coverage_rate = f"{total_bound_all / total_baseline_all * 100:.1f}%"
    else:
        metric_coverage_rate = "N/A"

    # Event section
    event_section = ""
    event_rows_json = "[]"
    event_col_keys_json = "[]"
    svc_stat_json = "[]"
    event_no_baseline_json = "[]"
    event_non_exist_json = "[]"
    event_overview_json = "{}"
    event_svc_stat_data = []
    event_rows_data = []
    event_no_baseline_data = []
    event_non_exist_data = []

    if event_report_path:
        try:
            event_report = load_json(event_report_path)
            event_baseline = load_json(event_baseline_path) if event_baseline_path else {}
            event_section, event_rows_json, event_col_keys_json, svc_stat_json, event_no_baseline_json, event_non_exist_json = build_event_section(event_report, event_baseline)
            event_overview_json = json.dumps(event_report.get("summary", {}), ensure_ascii=False)
            event_svc_stat_data = json.loads(svc_stat_json) if svc_stat_json != "[]" else []
            event_rows_data = json.loads(event_rows_json) if event_rows_json != "[]" else []
            event_no_baseline_data = json.loads(event_no_baseline_json) if event_no_baseline_json != "[]" else []
            event_non_exist_data = json.loads(event_non_exist_json) if event_non_exist_json != "[]" else []
            logger.info("Event baseline section added to HTML report")
        except Exception as e:
            logger.warning(f"Failed to load event report: {e}")

    # AOM sections
    aom_indicator_report = None
    aom_event_report = None
    _intermediate_dir = Path(bind_report_path).parent
    try:
        aom_indicator_report = load_json(str(_intermediate_dir / "aom_indicator_bind_report.json"))
        logger.info("AOM indicator report loaded")
    except Exception:
        pass
    try:
        aom_event_report = load_json(str(_intermediate_dir / "aom_event_bind_report.json"))
        logger.info("AOM event report loaded")
    except Exception:
        pass

    # No baseline instances — exclude AOM services (they are handled in the merged indicator section)
    aom_services = set()
    if aom_indicator_report:
        for item in aom_indicator_report.get("items", []):
            aom_services.add(item.get("云服务简称", ""))
    no_baseline_json_data = sorted(
        [inst for inst in no_baseline_instances if inst.get("service") not in aom_services],
        key=lambda x: x["service"],
    )
    no_baseline_json = json.dumps(no_baseline_json_data, ensure_ascii=False)

    # Filter AOM event services from event no-baseline instances
    aom_event_services = set()
    if aom_event_report:
        for item in aom_event_report.get("items", []):
            aom_event_services.add(item.get("云服务简称", ""))
    event_no_baseline_data = [
        inst for inst in event_no_baseline_data if inst.get("service") not in aom_event_services
    ]
    event_no_baseline_json = json.dumps(event_no_baseline_data, ensure_ascii=False)

    # Non-exist instances
    non_exist_json = json.dumps(non_exist_instances, ensure_ascii=False)

    # Metric overview
    metric_overview_json = json.dumps({
        "total_instances": report["summary"]["total_instances"],
        "instances_needing_action": len(instances_needing_action_ids),
        "total_missing": total_missing_metrics,
        "coverage_rate": metric_coverage_rate
    }, ensure_ascii=False)

    # Metric svc stat
    metric_svc_stat_data = convert_svc_summary_to_stat_data(svc_summary)
    metric_svc_stat_json = json.dumps(metric_svc_stat_data, ensure_ascii=False)

    # Rows data for detail table
    rows_data = []
    for s in suggestions:
        metrics = s["missing_metrics"]
        dim_cn = s.get("metric_dimension_cn", s.get("metric_dimension", ""))
        if metrics:
            for m in metrics:
                row = {"instance_id": s["instance_id"], "region": s.get("region", ""), "service": s["service"], "metric_dimension": s.get("metric_dimension", ""), "metric_dimension_cn": dim_cn}
                for col_label, col_key in METRIC_DETAIL_COLUMNS:
                    row[col_key] = str(m.get(col_key, ""))
                rows_data.append(row)
        else:
            row = {"instance_id": s["instance_id"], "region": s.get("region", ""), "service": s["service"], "metric_dimension": s.get("metric_dimension", ""), "metric_dimension_cn": dim_cn}
            for col_label, col_key in METRIC_DETAIL_COLUMNS:
                row[col_key] = ""
            row["_no_missing"] = True
            rows_data.append(row)
    rows_json = json.dumps(rows_data, ensure_ascii=False)

    # --- Merge AOM indicator data into CES structures ---
    aom_baseline_records = []
    try:
        aom_baseline_path = str(Path(bind_report_path).parent / "aom_indicator_baseline.json")
        aom_baseline_data = load_json(aom_baseline_path)
        aom_baseline_records = aom_baseline_data.get("records", []) if aom_baseline_data else []
    except Exception as e:
        logger.warning(f"Failed to load AOM indicator baseline: {e}")

    core_instances = {}
    try:
        core_path = str(Path(bind_report_path).parent / "core_instances.json")
        core_data = load_json(core_path)
        core_instances = core_data.get("instances", {}) if core_data else {}
    except Exception as e:
        logger.warning(f"Failed to load core instances: {e}")

    # Build CES overview dict for merge
    ces_overview = {
        "total_instances": report["summary"]["total_instances"],
        "instances_needing_action": len(instances_needing_action_ids),
        "total_missing": total_missing_metrics,
        "coverage_rate": metric_coverage_rate,
        "total_baseline_metrics": total_baseline_all,
        "total_covered": total_bound_all,
    }

    merged_overview, metric_svc_stat_data, rows_data = merge_aom_into_ces(
        ces_overview, metric_svc_stat_data, rows_data,
        aom_indicator_report, aom_baseline_records, core_instances,
    )

    # Re-serialize merged data
    metric_overview_json = json.dumps(merged_overview, ensure_ascii=False)
    metric_svc_stat_json = json.dumps(metric_svc_stat_data, ensure_ascii=False)
    rows_json = json.dumps(rows_data, ensure_ascii=False)
    logger.info(f"After AOM merge: {len(metric_svc_stat_data)} svc stat rows, {len(rows_data)} detail rows")

    # --- Merge AOM event data into CES event structures ---
    aom_event_baseline_records = []
    try:
        aom_event_baseline_path = str(Path(bind_report_path).parent / "aom_event_baseline.json")
        aom_event_baseline_data = load_json(aom_event_baseline_path)
        aom_event_baseline_records = aom_event_baseline_data.get("records", []) if aom_event_baseline_data else []
    except Exception as e:
        logger.warning(f"Failed to load AOM event baseline: {e}")

    event_overview_json, event_svc_stat_data, event_rows_data = merge_aom_event_into_ces(
        event_overview_json, event_svc_stat_data, event_rows_data,
        aom_event_report, aom_event_baseline_records, core_instances,
    )
    svc_stat_json = json.dumps(event_svc_stat_data, ensure_ascii=False)
    event_rows_json = json.dumps(event_rows_data, ensure_ascii=False)
    logger.info(f"After AOM event merge: {len(event_svc_stat_data)} event svc stat rows, {len(event_rows_data)} event detail rows")

    # Service options
    svc_options_data = _build_svc_options(report.get("by_service_dimension", {}))
    svc_options_json = json.dumps(svc_options_data, ensure_ascii=False)

    # Event service options
    event_svc_options_data = _build_event_svc_options(event_svc_stat_data)
    event_svc_options_json = json.dumps(event_svc_options_data, ensure_ascii=False)

    html = build_html(
        suggestions,
        svc_summary,
        report.get("by_service_dimension", {}),
        report["summary"]["total_instances"],
        total_missing_metrics,
        len(instances_needing_action_ids),
        metric_coverage_rate=metric_coverage_rate,
        event_section=event_section,
        event_rows_json=event_rows_json,
        event_col_keys_json=event_col_keys_json,
        svc_stat_json=svc_stat_json,
        svc_options_json=svc_options_json,
        no_baseline_json=no_baseline_json,
        metric_overview_json=metric_overview_json,
        event_overview_json=event_overview_json,
        event_no_baseline_json=event_no_baseline_json,
        event_non_exist_json=event_non_exist_json,
        event_svc_options_json=event_svc_options_json,
        non_exist_json=non_exist_json,
        merged_metric_svc_stat_json=metric_svc_stat_json,
        merged_rows_json=rows_json,
    )

    # Inject AOM event section into the event tab via placeholder
    # AOM indicator data has been merged into CES indicator tab, so placeholder is empty
    html = html.replace("<!--AOM_INDICATOR_PLACEHOLDER-->", "")

    # AOM event data has been merged into CES event tab, so placeholder is empty
    html = html.replace("<!--AOM_EVENT_PLACEHOLDER-->", "")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"Suggestion report saved to {output_path}")
    logger.info(f"Total: {len(instances_needing_action_ids)} instances need action, {total_missing_metrics} metrics to add")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate alarm binding suggestion report (HTML)")
    parser.add_argument("--bind-report", default=DEFAULT_BIND_REPORT)
    parser.add_argument("--baseline", default=DEFAULT_BASELINE)
    parser.add_argument("--rules", default=DEFAULT_RULES, help="Path to online_alarm_rules.json")
    parser.add_argument("--event-report", default=DEFAULT_EVENT_REPORT, help="Path to event_bind_report.json")
    parser.add_argument("--event-baseline", default=DEFAULT_EVENT_BASELINE, help="Path to event_baseline.json")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    generate(args.bind_report, args.baseline, args.output, rules_path=args.rules, event_report_path=args.event_report, event_baseline_path=args.event_baseline)
