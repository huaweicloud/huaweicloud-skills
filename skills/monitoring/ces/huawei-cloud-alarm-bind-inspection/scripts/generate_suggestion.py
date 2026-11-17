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




def generate(bind_report_path, baseline_path, output_path, rules_path=None, event_report_path=None, event_baseline_path=None):
    report = load_json(bind_report_path)
    baseline = load_json(baseline_path)

    baseline_by_svc_dim = defaultdict(dict)
    for rec in baseline["records"]:
        svc = rec["云服务简称"]
        dim = rec.get("指标维度", "")
        baseline_by_svc_dim[(svc, dim)][rec["指标ID"]] = rec

    # Merge AOM indicator baseline into baseline_by_svc_dim BEFORE process_report_instances
    # so that AOM services (CCE/CCI/IoTDA/Modelarts) can look up metric details
    _intermediate_dir = Path(bind_report_path).parent
    try:
        aom_bl_path = str(_intermediate_dir / "aom_indicator_baseline.json")
        aom_bl_data = load_json(aom_bl_path)
        if aom_bl_data:
            for rec in aom_bl_data.get("records", []):
                svc = rec.get("云服务简称", "")
                dim = rec.get("指标维度", "")
                mid = rec.get("指标ID", "").strip()
                if svc and dim and mid:
                    mapped = {
                        "指标ID": mid,
                        "指标名称": rec.get("指标名称", ""),
                        "命名空间": rec.get("命名空间", ""),
                        "指标维度-中文": rec.get("指标维度-中文", dim),
                        "重要告警阈值": rec.get("重要告警阈值", ""),
                        "紧急告警阈值": rec.get("紧急告警阈值", ""),
                        "告警频率": "",
                        "采集周期（秒）": rec.get("采集周期", rec.get("统计周期", "")),
                        "比较关系": rec.get("运算符", ""),
                        "连续触发次数": rec.get("连续周期", ""),
                        "默认单位": rec.get("默认单位", rec.get("单位", "")),
                        "备注": rec.get("备注", ""),
                    }
                    baseline_by_svc_dim[(svc, dim)][mid] = mapped
            logger.info(f"AOM baseline merged: {len(aom_bl_data.get('records', []))} records")
    except Exception as e:
        logger.warning(f"Failed to load AOM indicator baseline: {e}")

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
            event_overview = event_report.get("summary", {})
            event_svc_stat_data = json.loads(svc_stat_json) if svc_stat_json != "[]" else []
            # Compute instances_needing_action from svc stat data and inject into overview
            # so JS renderEventOverview() doesn't overwrite with undefined||0
            event_instances_needing_action = sum(
                item.get("partially_bound", 0) + item.get("unbound", 0) + item.get("no_online_rules", 0)
                for item in event_svc_stat_data
            )
            event_overview["instances_needing_action"] = event_instances_needing_action
            event_overview_json = json.dumps(event_overview, ensure_ascii=False)
            event_rows_data = json.loads(event_rows_json) if event_rows_json != "[]" else []
            event_no_baseline_data = json.loads(event_no_baseline_json) if event_no_baseline_json != "[]" else []
            event_non_exist_data = json.loads(event_non_exist_json) if event_non_exist_json != "[]" else []
            logger.info("Event baseline section added to HTML report")
        except Exception as e:
            logger.warning(f"Failed to load event report: {e}")

    # AOM baseline already merged above before process_report_instances

    no_baseline_json_data = sorted(no_baseline_instances, key=lambda x: x["service"])
    no_baseline_json = json.dumps(no_baseline_json_data, ensure_ascii=False)
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
                row = {"instance_id": s["instance_id"], "region": s.get("region", ""), "service": s["service"], "metric_dimension": s.get("metric_dimension", ""), "metric_dimension_cn": dim_cn, "monitor_system": s.get("monitor_system", "CES")}
                for col_label, col_key in METRIC_DETAIL_COLUMNS:
                    row[col_key] = str(m.get(col_key, ""))
                rows_data.append(row)
        else:
            row = {"instance_id": s["instance_id"], "region": s.get("region", ""), "service": s["service"], "metric_dimension": s.get("metric_dimension", ""), "metric_dimension_cn": dim_cn, "monitor_system": s.get("monitor_system", "CES")}
            for col_label, col_key in METRIC_DETAIL_COLUMNS:
                row[col_key] = ""
            row["_no_missing"] = True
            rows_data.append(row)
    rows_json = json.dumps(rows_data, ensure_ascii=False)

    # Unified report already has CES + AOM data — no merge needed
    logger.info(f"Unified report: {len(metric_svc_stat_data)} svc stat rows, {len(rows_data)} detail rows")
    logger.info(f"Unified event report: {len(event_svc_stat_data)} event svc stat rows, {len(event_rows_data)} event detail rows")

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
