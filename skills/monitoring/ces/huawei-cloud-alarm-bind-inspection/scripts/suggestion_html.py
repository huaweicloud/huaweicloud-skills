#!/usr/bin/env python3
import json
from collections import defaultdict
from datetime import datetime

from suggestion_data import (
    convert_svc_summary_to_stat_data,
    METRIC_DETAIL_COLUMNS,
    EVENT_DETAIL_COLUMNS,
)
from suggestion_template import CSS_TEMPLATE, get_html_body, get_js_script


def build_event_section(event_report, event_baseline):
    if not event_report:
        return "", "[]", "[]", "[]", "[]", "[]"

    summary = event_report.get("summary", {}) or event_report.get("overall_summary", {})

    total_instances = summary.get("total_instances", 0)
    no_rules_instances = summary.get("no_rules_instances", 0)
    missing_events_total = summary.get("missing_events_total", 0)
    no_baseline_instances = summary.get("no_baseline_instances", 0)
    overall_rate = summary.get("overall_rate", "N/A")

    by_service = event_report.get("by_service", {})
    by_instance = event_report.get("by_instance", [])

    instances_needing_action = 0
    if by_service:
        for svc, svc_info in by_service.items():
            instances_needing_action += svc_info.get("partially_bound", 0)
            instances_needing_action += svc_info.get("unbound", 0)
            instances_needing_action += svc_info.get("no_online_rules", 0)
    else:
        instances_needing_action = total_instances - summary.get("bound_instances", 0)

    svc_stat_data = []
    event_no_baseline_data = []
    event_non_exist_data = []
    for svc_dim_key, svc_info in sorted(by_service.items()):
        display_name = svc_dim_key.replace("|", " - ") if "|" in svc_dim_key else svc_dim_key
        no_bl = svc_info.get("no_baseline", 0)
        if no_bl > 0 and no_bl == svc_info.get("total_instances", 0):
            no_bl_insts = []
            for inst in by_instance:
                if inst.get("svc_dim", inst.get("service", "")) == display_name and inst.get("bound_status") == "no_baseline":
                    no_bl_insts.append(inst.get("instance_id", ""))
            event_no_baseline_data.append({
                "service": display_name,
                "instance_count": no_bl,
                "instance_ids": no_bl_insts,
            })
        else:
            svc_stat_data.append({
                "svc": display_name,
                "total_instances": svc_info.get("total_instances", 0),
                "fully_bound": svc_info.get("fully_bound", 0),
                "partially_bound": svc_info.get("partially_bound", 0),
                "unbound": svc_info.get("unbound", 0),
                "no_online_rules": svc_info.get("no_online_rules", 0),
                "baseline_event_count": svc_info.get("baseline_event_count", 0),
                "covered_baseline": svc_info.get("covered_baseline", 0),
                "total_baseline": svc_info.get("total_baseline", 0),
                "bind_rate": svc_info.get("bind_rate", "N/A"),
            })

    for inst in by_instance:
        if inst.get("bound_status") == "instance_non_exist":
            event_non_exist_data.append({
                "instance_id": inst.get("instance_id", ""),
                "service": inst.get("service", ""),
                "region": inst.get("region", ""),
            })

    event_rows_data = []

    for inst in by_instance:
        if inst.get("bound_status") == "no_baseline":
            continue
        inst_id = inst.get("instance_id", "")
        inst_region = inst.get("region", "")
        svc = inst.get("svc_dim", inst.get("service", ""))
        missing_events = inst.get("missing_events", [])
        if missing_events:
            for ev in missing_events:
                row = {"instance_id": inst_id, "region": inst_region, "svc": svc}
                for col in EVENT_DETAIL_COLUMNS:
                    row[col] = str(ev.get(col, ""))
                event_rows_data.append(row)

    svc_stat_json = json.dumps(svc_stat_data, ensure_ascii=False)
    event_rows_json = json.dumps(event_rows_data, ensure_ascii=False)
    event_no_baseline_json = json.dumps(event_no_baseline_data, ensure_ascii=False)
    event_non_exist_json = json.dumps(event_non_exist_data, ensure_ascii=False)



    event_col_headers = "".join("<th>" + col + "</th>" for col in EVENT_DETAIL_COLUMNS)
    event_col_keys_json = json.dumps(EVENT_DETAIL_COLUMNS, ensure_ascii=False)

    section = """
        <div class="card" id="event-overview">
            <h2 class="card-header">概览</h2>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="value" id="event-stat-instances">""" + str(total_instances) + """</div>
                    <div class="label">核心实例总数</div>
                </div>
                <div class="stat-item">
                    <div class="value danger" id="event-stat-needing">""" + str(instances_needing_action) + """</div>
                    <div class="label">需补齐实例数</div>
                </div>
                <div class="stat-item">
                    <div class="value danger" id="event-stat-no-rules">""" + str(missing_events_total) + """</div>
                    <div class="label">缺失事件总数</div>
                </div>
                <div class="stat-item">
                    <div class="value" id="event-stat-rate">""" + overall_rate + """</div>
                    <div class="label">事件覆盖率<i class="tooltip-icon" data-tip="已覆盖底线事件数 / 总底线事件数">ⓘ</i></div>
                </div>
            </div>
        </div>

        <div class="card" id="event-svc-stats">
            <h2 class="card-header">按服务统计</h2>
            <div class="tab-label primary">有事件基线的核心实例</div>
            <div class="tab-table-wrap">
                <table class="svc-summary-table">
                    <thead>
                         <tr><th>监控体系</th><th>云服务-维度</th><th>实例总数</th><th>完全配置</th><th>部分配置</th><th>未配置</th><th>建议事件数</th><th>总体配置率</th></tr>
                    </thead>
                    <tbody id="svc-stat-tbody"></tbody>
                </table>
            </div>
            <div id="event-no-baseline-section" style="display:none;">
                <div class="tab-label secondary">无事件基线的核心实例</div>
                <div class="tab-table-wrap">
                    <table class="svc-summary-table">
                        <thead>
                            <tr><th>云服务</th><th>实例数量</th><th>实例ID列表</th></tr>
                        </thead>
                        <tbody id="event-no-baseline-tbody"></tbody>
                    </table>
                </div>
            </div>
            <div id="event-non-exist-section" style="display:none;">
                <div class="tab-label" style="background:var(--semi-color-danger);">不存在的实例</div>
                <span style="font-size:12px;color:var(--semi-color-text-2);margin-left:12px;">1. 请前往OA-监控告警-资源分组-新建-添加资源中验证是否存在该实例。&nbsp;&nbsp;2. 请确认【核心实例清单】中region是否填对。</span>
                <div class="tab-table-wrap">
                    <table class="svc-summary-table">
                        <thead>
                            <tr><th>云服务</th><th>实例数量</th><th>实例ID列表</th></tr>
                        </thead>
                        <tbody id="event-non-exist-tbody"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="card" id="event-detail" style="min-height:500px;">
            <h2 class="card-header">补齐明细</h2>
            <div class="filter-bar">
                <label for="event-svc-filter">服务筛选：</label>
                <div class="svc-select" id="event-svc-select">
                    <div class="svc-select-trigger" id="event-svc-select-trigger">
                        <span class="svc-select-text placeholder" id="event-svc-select-text">全部服务</span>
                        <span class="svc-select-arrow">▼</span>
                    </div>
                    <div class="svc-select-dropdown" id="event-svc-select-dropdown">
                        <div class="svc-select-search-wrap">
                            <input type="text" class="svc-select-search" id="event-svc-search" placeholder="搜索服务" autocomplete="off" />
                            <button type="button" class="svc-select-clear" id="event-svc-search-clear">&times;</button>
                        </div>
                        <div class="svc-select-options" id="event-svc-select-options"></div>
                    </div>
                </div>
            </div>
            <table id="event-detail-table" style="table-layout:fixed;">
                <colgroup>
                    <col style="width:25%"><col style="width:12%">
                    <col style="width:10%"><col style="width:25%"><col style="width:28%">
                </colgroup>
                <thead>
                    <tr>
                        <th>监控体系</th>
                        <th>实例ID</th>
                        <th>Region</th>
                        <th>云服务</th>
                        """ + event_col_headers + """
                    </tr>
                </thead>
                <tbody id="event-tbody"></tbody>
            </table>
            <div class="pagination" id="event-pagination"></div>
        </div>
"""

    return section, event_rows_json, event_col_keys_json, svc_stat_json, event_no_baseline_json, event_non_exist_json


def build_html(suggestions, svc_summary, all_services, total_instances, total_missing, instances_needing_action, username="", metric_coverage_rate="", event_section="", event_rows_json="[]", event_col_keys_json="[]", svc_stat_json="[]", svc_options_json="[]", no_baseline_json="[]", metric_overview_json="{}", event_overview_json="{}", event_no_baseline_json="[]", event_non_exist_json="[]", event_svc_options_json="[]", non_exist_json="[]", merged_metric_svc_stat_json=None, merged_rows_json=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    svc_stat_data = convert_svc_summary_to_stat_data(svc_summary)
    metric_svc_stat_json = json.dumps(svc_stat_data, ensure_ascii=False)
    if merged_metric_svc_stat_json is not None:
        metric_svc_stat_json = merged_metric_svc_stat_json

    if event_svc_options_json == "[]":
        event_svc_options_data = [{"value": "", "label": "全部服务"}]
        seen = set()
        for item in json.loads(svc_stat_json):
            s = item.get("svc", "")
            if s and s not in seen:
                seen.add(s)
                event_svc_options_data.append({"value": s, "label": s})
        event_svc_options_json = json.dumps(event_svc_options_data, ensure_ascii=False)

    rows_data = []
    for s in suggestions:
        metrics = s["missing_metrics"]
        dim_cn = s.get("metric_dimension_cn", s.get("metric_dimension", ""))
        if metrics:
            for m in metrics:
                row = {"instance_id": s["instance_id"], "service": s["service"], "metric_dimension": s.get("metric_dimension", ""), "metric_dimension_cn": dim_cn }
                for col_label, col_key in METRIC_DETAIL_COLUMNS:
                    row[col_key] = str(m.get(col_key, ""))
                rows_data.append(row)
        else:
            row = {"instance_id": s["instance_id"], "service": s["service"], "metric_dimension": s.get("metric_dimension", ""), "metric_dimension_cn": dim_cn }
            for col_label, col_key in METRIC_DETAIL_COLUMNS:
                row[col_key] = ""
            row["_no_missing"] = True
            rows_data.append(row)

    rows_json = json.dumps(rows_data, ensure_ascii=False)
    if merged_rows_json is not None:
        rows_json = merged_rows_json

    detail_col_headers = "".join("<th>" + col[0] + "</th>" for col in METRIC_DETAIL_COLUMNS)
    col_keys_json = json.dumps([col[1] for col in METRIC_DETAIL_COLUMNS], ensure_ascii=False)

    svc_options_data = [{"value": "", "label": "全部服务"}]
    for svc_dim_key in sorted(all_services.keys()):
        if svc_dim_key.endswith("|无指标基线"):
            continue
        display_name = svc_dim_key.replace("|", " - ") if "|" in svc_dim_key else svc_dim_key
        svc_options_data.append({"value": svc_dim_key, "label": display_name})
    svc_options_json = json.dumps(svc_options_data, ensure_ascii=False)

    html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>监控告警底线指标补齐建议书</title>
""" + CSS_TEMPLATE + """
</head>
""" + get_html_body(now, total_instances, instances_needing_action, total_missing, metric_coverage_rate, detail_col_headers, event_section) + """
""" + get_js_script(
        metric_overview_json,
        metric_svc_stat_json,
        no_baseline_json,
        non_exist_json,
        rows_json,
        event_overview_json,
        svc_stat_json,
        event_rows_json,
        event_no_baseline_json,
        event_non_exist_json,
        svc_options_json,
        col_keys_json,
        event_col_keys_json,
        event_svc_options_json,
    ) + """
</body>
</html>"""
    return html_template
