#!/usr/bin/env python3
import os
"""HTML template and inline styles."""

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; padding: 20px; }
.report-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; border-radius: 12px; padding: 28px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
.report-header h1 { font-size: 24px; margin-bottom: 10px; }
.report-header .meta { font-size: 13px; opacity: 0.9; }
.report-header .meta span { margin-right: 20px; }
.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px; }
.summary-card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center; }
.summary-card .label { font-size: 12px; color: #999; margin-bottom: 8px; }
.summary-card .value { font-size: 28px; font-weight: 700; }
.summary-card .value.ok { color: #27ae60; }
.summary-card .value.warn { color: #f39c12; }
.summary-card .value.err { color: #e74c3c; }
.summary-card .sub { font-size: 12px; color: #999; margin-top: 4px; }
.section-title { font-size: 18px; font-weight: 700; color: #1a1a2e; margin: 24px 0 12px 0; padding-left: 12px; border-left: 4px solid #667eea; }
.instance-section { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 20px; }
.instance-section h2 { font-size: 16px; color: #333; margin-bottom: 8px; }
.instance-section .inst-meta { font-size: 13px; color: #888; margin-bottom: 16px; }
.instance-section .inst-meta span { margin-right: 16px; }
.chart-wrapper { position: relative; height: 450px; margin-bottom: 16px; }
.detail-box { background: #f8f9fa; border-radius: 8px; padding: 16px; margin-bottom: 12px; border-left: 4px solid; }
.detail-box.warn { border-color: #f39c12; }
.detail-box.ok { border-color: #27ae60; }
.detail-box.err { border-color: #e74c3c; }
.detail-box h3 { font-size: 14px; margin-bottom: 4px; word-break: break-all; }
.detail-box .indicators { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 16px; font-size: 13px; }
.detail-box .indicators .ok { color: #27ae60; }
.detail-box .indicators .err { color: #e74c3c; }
.summary-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 12px; }
.summary-table th { background: #f0f2f5; padding: 8px 12px; text-align: left; font-weight: 600; color: #333; border-bottom: 2px solid #e0e0e0; }
.summary-table td { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; color: #555; }
.status-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.status-badge.ok { background: #e8f8e8; color: #27ae60; }
.status-badge.warn { background: #fef9e7; color: #f39c12; }
.status-badge.err { background: #fadbd8; color: #e74c3c; }
.skip-note { font-size: 13px; color: #999; padding: 8px 16px; background: #f8f9fa; border-radius: 8px; margin-bottom: 12px; }
"""

VERDICT_TEXT = {"ok": "✅ 正常", "warn": "⚠️ 部分异常", "err": "❌ 异常"}
VERDICT_CLASS = {"ok": "ok", "warn": "warn", "err": "err"}

SERVICE_COLORS = {
    "ecs": "#667eea", "rds": "#9b59b6", "redis": "#e67e22",
    "elb": "#00b894", "eip": "#0984e3", "nat": "#fd79a8", "vpcep": "#a29bfe",
    "evs": "#636e72", "cce": "#d63031", "css": "#e17055", "dds": "#74b9ff",
    "dws": "#55efc4", "dc": "#b2bec3", "er": "#fab1a0", "efsturbo": "#76e0ff",
    "apig": "#81ecec", "taurusdb": "#6c5ce7", "geminidb": "#f368e0", "dms": "#ff7675",
}
SERVICE_LABEL = {
    "ecs": "ECS", "rds": "RDS", "redis": "Redis",
    "elb": "ELB", "eip": "EIP", "nat": "NAT", "vpcep": "VPCEP",
    "evs": "EVS", "cce": "CCE", "css": "CSS", "dds": "DDS",
    "dws": "DWS", "dc": "DC", "er": "ER", "efsturbo": "SFS Turbo",
    "apig": "APIG", "taurusdb": "TaurusDB", "geminidb": "GeminiDB", "dms": "DMS",
}

# Chart.js dataset color pool
CHART_COLORS = [
    "#e74c3c", "#3498db", "#95a5a6", "#2ecc71", "#9b59b6",
    "#f39c12", "#1abc9c", "#16a085", "#e67e22", "#34495e",
    "#2c3e50", "#f1c40f", "#c0392b", "#7f8c8d", "#27ae60",
]


def html_head():
    """Generate HTML head, inline Chart.js for self-contained offline-capable report."""
    chart_js_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "chart.umd.min.js")
    with open(chart_js_path, "r", encoding="utf-8") as f:
        chart_js_content = f.read()
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
<script>{chart_js_content}</script>
<style>{CSS}</style>"""


def html_footer():
    return "</body>\n</html>"


def render_header(drill_name, inspect_time, duration_s, total_items, fail_items):
    return f"""
<div class="report-header">
  <h1>🔥 {drill_name} - 稳态指标巡检报告</h1>
  <div class="meta">
    <span>⏰ 巡检时间: {inspect_time}</span>
    <span>⏱️ 耗时: {duration_s:.1f}s</span>
    <span>📊 TSC实时数据: {total_items} 项</span>
    <span>❌ 查询失败: {fail_items} 项</span>
  </div>
</div>"""


def render_summary_cards(judgment_result, instances_by_service):
    g = judgment_result["global"]
    total_instances = sum(len(v) for v in instances_by_service.values())
    ok_instances = sum(s["ok_count"] for s in judgment_result["services"].values())
    warn_instances = sum(s["warn_count"] for s in judgment_result["services"].values())

    cards = [
        f'<div class="summary-card"><div class="label">指标总数</div><div class="value">{g["total_checks"]}</div><div class="sub">正常 {g["ok_checks"]} / 异常 {g["fail_checks"]}</div></div>',
        f'<div class="summary-card"><div class="label">实例总数</div><div class="value">{total_instances}</div><div class="sub">正常 {ok_instances} / 部分异常 {warn_instances}</div></div>',
    ]
    for svc, svc_data in judgment_result["services"].items():
        label = SERVICE_LABEL.get(svc, svc)
        v = svc_data["verdict"]
        icon = VERDICT_TEXT.get(v, v)
        cls = VERDICT_CLASS.get(v, "")
        sub = f'{svc_data["ok_checks"]}/{svc_data["total_checks"]} 正常, {svc_data["instance_count"]} 实例'
        cards.append(
            f'<div class="summary-card"><div class="label">{label} 状态</div><div class="value {cls}">{icon}</div><div class="sub">{sub}</div></div>'
        )
    return '<div class="summary-grid">\n' + "\n".join(cards) + "\n</div>"


def render_topology(topology):
    legend = """<div style="display:flex;flex-wrap:wrap;gap:6px 16px;margin-bottom:16px;font-size:12px;color:#888;">
<span style="display:inline-flex;align-items:center;gap:6px;"><i style="width:8px;height:8px;border-radius:2px;background:#27ae60;display:inline-block;"></i>运行</span>
<span style="display:inline-flex;align-items:center;gap:6px;"><i style="width:8px;height:8px;border-radius:2px;background:#e74c3c;display:inline-block;"></i>异常/离线</span>
<span style="display:inline-flex;align-items:center;gap:6px;"><i style="width:8px;height:8px;border-radius:2px;background:#f39c12;display:inline-block;"></i>部分异常</span>
<span style="display:inline-flex;align-items:center;gap:6px;margin-left:12px;color:#aaa;font-size:11px;">主/备角色标注仅适用于跨AZ服务（如RDS）</span>
</div>"""
    region_html = []
    for region_data in topology:
        region = region_data["region"]
        region_html.append(
            f'<div style="font-size:15px;font-weight:700;color:#333;margin-bottom:10px;padding:6px 12px;background:linear-gradient(90deg,#667eea22,#667eea08);border-left:3px solid #667eea;border-radius:4px;">📍 {region}</div>'
        )
        az_cards = []
        for az_data in region_data["azs"]:
            az = az_data["az"]
            running = az_data["running_count"]
            abnormal = az_data["abnormal_count"]
            if abnormal == 0 and running > 0:
                top_color = "#27ae60"
            elif running == 0:
                top_color = "#e74c3c"
            else:
                top_color = "#f39c12"
            svc_parts = []
            for svc, svc_info in az_data["services"].items():
                color = SERVICE_COLORS.get(svc, "#999")
                label = SERVICE_LABEL.get(svc, svc)
                svc_running = svc_info["running"]
                svc_abnormal = svc_info["abnormal"]
                svc_parts.append(
                    f'<div style="font-size:11px;font-weight:600;color:{color};margin-bottom:4px;padding:2px 6px;border-left:2px solid {color};background:{color}11;border-radius:2px;">{label} <span style="font-weight:400;color:#aaa;">({svc_running}运行/{svc_abnormal}异常)</span></div>'
                )
                chips = []
                for inst in svc_info["instances"]:
                    verdict = inst["verdict"]
                    chip_map = {"ok": ("#e8f8e8", "#27ae60", "#27ae60"), "warn": ("#fef9e7", "#f39c12", "#f39c12"), "err": ("#fadbd8", "#e74c3c", "#e74c3c")}
                    chip_bg, chip_border, dot_color = chip_map.get(verdict, ("#f8f9fa", "#e0e0e0", "#999"))
                    role_tag = ""
                    if inst.get("role") == "master":
                        role_tag = '<span style="font-size:10px;padding:0 4px;border-radius:2px;background:#5AA9FF22;color:#5AA9FF;">主</span>'
                    elif inst.get("role") == "standby":
                        role_tag = f'<span style="font-size:10px;padding:0 4px;border-radius:2px;background:{color}22;color:{color};">备</span>'
                    chips.append(
                        f'<div style="display:inline-flex;align-items:center;gap:6px;padding:4px 8px;border-radius:4px;background:{chip_bg};border:1px solid {chip_border};font-size:12px;line-height:1.3;"><span style="width:8px;height:8px;border-radius:2px;background:{dot_color};flex:none;"></span><b style="font-weight:500;">{inst["name"]}</b>{role_tag}</div>'
                    )
                svc_parts.append(f'<div style="display:flex;flex-wrap:wrap;gap:6px;">{"".join(chips)}</div>')
            az_cards.append(
                f'<div style="background:#f8f9fa;border:1px solid #e0e0e0;border-radius:8px;padding:14px;min-height:120px;border-top:3px solid {top_color};">\n'
                f'<div style="font-size:13px;font-weight:600;color:#333;margin-bottom:10px;">{az} <span style="font-size:11px;color:#888;font-weight:400;">({running} 运行 / {abnormal} 异常)</span></div>\n'
                + "\n".join(svc_parts) + '\n</div>'
            )
        region_html.append(f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px;">{"".join(az_cards)}</div>')
    return f"""<div class="section-title">🗺️ AZ 资源拓扑图</div>
<div style="background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:20px;">
{legend}
<div style="margin-bottom:16px;">{"".join(region_html)}</div>
</div>"""


def render_status_tables(judgment_result):
    parts = ['<div class="section-title">📋 实例状态总览</div>']
    for svc, svc_data in judgment_result["services"].items():
        label = SERVICE_LABEL.get(svc, svc)
        ok_c = svc_data["ok_count"]
        warn_c = svc_data["warn_count"]
        err_c = svc_data["err_count"]
        total = svc_data["instance_count"]
        parts.append(
            f'<h3 style="font-size:15px;color:#333;margin:16px 0 8px;">【{label}】（{total} 个实例 | ✅ 正常 {ok_c} | ⚠️ 部分异常 {warn_c} | ❌ 异常 {err_c}）</h3>'
        )
        parts.append('<table class="summary-table" style="margin-bottom:16px;"><thead><tr><th>实例ID</th><th>名称</th><th>区域</th><th>可用区</th><th>运行状态</th><th>巡检结果</th><th>指标</th></tr></thead><tbody>')
        for item in svc_data["instances"]:
            inst = item["instance"]
            judgment = item["judgment"]
            inst_id = inst.get("instance_id", "")
            name = inst.get("name", "")
            region = inst.get("region", "")
            status = inst.get("status", "UNKNOWN")
            verdict = judgment["verdict"]
            if svc == "rds":
                primary_az = inst.get("primary_az", "")
                standby_az = inst.get("standby_az", "")
                az_str = f"主({primary_az}), 备({standby_az})" if primary_az else "—"
            else:
                az_str = inst.get("az", "—") or "—"
            status_cls = VERDICT_CLASS.get(verdict, "")
            verdict_text = VERDICT_TEXT.get(verdict, verdict)
            verdict_cls = VERDICT_CLASS.get(verdict, "")
            ok_n = judgment["ok_count"]
            total_n = judgment["total"]
            parts.append(
                f'<tr><td style="word-break:break-all;">{inst_id}</td><td>{name}</td><td>{region}</td><td>{az_str}</td>'
                f'<td><span class="status-badge {status_cls}">{status}</span></td>'
                f'<td><span class="status-badge {verdict_cls}">{verdict_text}</span></td>'
                f'<td>{ok_n}/{total_n}</td></tr>'
            )
        parts.append("</tbody></table>")
    total_all = sum(s["instance_count"] for s in judgment_result["services"].values())
    ok_all = sum(s["ok_count"] for s in judgment_result["services"].values())
    warn_all = sum(s["warn_count"] for s in judgment_result["services"].values())
    parts.append(f'<div style="text-align:center;font-size:13px;color:#666;margin:8px 0 24px;">实例总计：{total_all} 个 | ✅ 正常 {ok_all} | ⚠️ 部分异常 {warn_all}</div>')
    return "\n".join(parts)


def render_detail_boxes(judgment_result):
    parts = ['<div class="section-title">🔍 逐实例指标详情</div>']
    for svc, svc_data in judgment_result["services"].items():
        label = SERVICE_LABEL.get(svc, svc)
        v = svc_data["verdict"]
        verdict_text = VERDICT_TEXT.get(v, v)
        total_checks = svc_data["total_checks"]
        ok_checks = svc_data["ok_checks"]
        fail_checks = svc_data["fail_checks"]
        parts.append(
            f'<div class="instance-section"><h2>【{label}】{verdict_text}（正常 {ok_checks}/{total_checks}，异常 {fail_checks}，TSC实时 {total_checks}，查询失败 0）</h2>'
        )
        for item in svc_data["instances"]:
            inst = item["instance"]
            judgment = item["judgment"]
            inst_id = inst.get("instance_id", "")
            name = inst.get("name", "")
            region = inst.get("region", "")
            status = inst.get("status", "UNKNOWN")
            verdict = judgment["verdict"]
            verdict_text = VERDICT_TEXT.get(verdict, verdict)
            ok_n = judgment["ok_count"]
            total_n = judgment["total"]
            fail_n = judgment["fail_count"]
            cls = VERDICT_CLASS.get(verdict, "")
            parts.append(
                f'<div class="detail-box {cls}"><h3>┌─ 实例: {inst_id} | 名称: {name} | 区域: {region} | 当前状态: {status}</h3>\n'
                f'<div style="font-size:13px;color:#888;margin-bottom:6px;">巡检结果: {verdict_text}（正常 {ok_n}/{total_n}，异常 {fail_n}，数据来源: TSC实时）</div>\n'
                f'<div class="indicators">'
            )
            for check in judgment["checks"]:
                if check["ok"]:
                    parts.append(f'<div class="ok">✅ {check["name"]}</div>')
                else:
                    parts.append(f'<div class="err">❌ {check["name"]}</div>')
            parts.append('</div></div>')
        parts.append('</div>')
    return "\n".join(parts)


def render_charts_section(metrics_by_service, instances_by_service, drill_name, start, end,
                          duration_minutes=30, timezone_offset=8):
    """Render monitoring metric line chart section, returns (html, chart_scripts)."""
    import json as _json
    from datetime import datetime, timezone, timedelta

    tz_cn = timezone(timedelta(hours=timezone_offset))
    parts = [f'<div class="section-title">📈 监控指标折线图（{duration_minutes}分钟时序数据）</div>']
    scripts = []
    chart_idx = 0
    skipped = []

    for svc, metrics_list in metrics_by_service.items():
        label = SERVICE_LABEL.get(svc, svc)
        for m_item in metrics_list:
            inst_id = m_item["instance_id"]
            # Find instance name
            inst_name = inst_id
            region = ""
            for inst in instances_by_service.get(svc, []):
                if inst["instance_id"] == inst_id:
                    inst_name = inst.get("name", inst_id)
                    region = inst.get("region", "")
                    break

            metrics = m_item["metrics"]
            if not metrics:
                continue

            # Collect all timestamps
            all_ts = set()
            for m_name, m_data in metrics.items():
                for dp in m_data["datapoints"]:
                    all_ts.add(dp["timestamp"])
            if not all_ts:
                continue

            sorted_ts = sorted(all_ts)
            time_labels = [datetime.fromtimestamp(ts, tz=tz_cn).strftime("%H:%M:%S") for ts in sorted_ts]

            # Build datasets
            datasets = []
            summary_rows = []
            for i, (m_name, m_data) in enumerate(metrics.items()):
                display_name = m_data["display_name"]
                unit = m_data["unit"]
                color = CHART_COLORS[i % len(CHART_COLORS)]
                # Build data points
                ts_to_val = {dp["timestamp"]: dp["value"] for dp in m_data["datapoints"]}
                data = [ts_to_val.get(ts, None) for ts in sorted_ts]
                # Statistics
                valid = [v for v in data if v is not None]
                if valid:
                    min_v = min(valid)
                    max_v = max(valid)
                    avg_v = sum(valid) / len(valid)
                else:
                    min_v = max_v = avg_v = None
                count = len(valid)
                datasets.append({
                    "label": f"{display_name} ({unit})",
                    "data": data,
                    "borderColor": color,
                    "backgroundColor": color + "20",
                    "fill": False,
                    "tension": 0.3,
                    "spanGaps": True,
                    "pointRadius": 3,
                    "pointHoverRadius": 6,
                    "borderWidth": 2,
                })
                summary_rows.append({
                    "metric": f"{display_name} ({unit})",
                    "min": min_v, "max": max_v, "avg": avg_v, "count": count,
                })

            parts.append(f"""
<div class="instance-section">
  <h2>📈 {label} 监控指标 - {drill_name}</h2>
  <div class="inst-meta">
    <span>实例: <strong>{inst_name}</strong> ({region})</span>
    <span>时间: {start} ~ {end}</span>
    <span>数据点数: {len(sorted_ts)}</span>
  </div>
  <div class="chart-wrapper"><canvas id="chart_{chart_idx}"></canvas></div>
  <table class="summary-table"><thead><tr><th>指标</th><th>最小值</th><th>最大值</th><th>平均值</th><th>数据点数</th></tr></thead><tbody id="chart_{chart_idx}_summary"></tbody></table>
</div>""")

            scripts.append(_build_chart_script(chart_idx, time_labels, datasets, summary_rows))
            chart_idx += 1

    # Skipped abnormal instances
    for svc, instances in instances_by_service.items():
        for inst in instances:
            if not inst.get("_is_normal", True):
                skipped.append(f'{inst.get("name", inst.get("instance_id", ""))}（{inst.get("status", "UNKNOWN")}）')
    if skipped:
        parts.append(f'<div class="skip-note">⏭️ 以下实例因状态异常已跳过监控采集：{", ".join(skipped)}</div>')

    return "\n".join(parts), "\n".join(scripts)


def _build_chart_script(idx, time_labels, datasets, summary_rows):
    import json as _json
    return f"""
(function() {{
  const timeLabels = {_json.dumps(time_labels, ensure_ascii=False)};
  const datasets = {_json.dumps(datasets, ensure_ascii=False)};
  const summaryRows = {_json.dumps(summary_rows, ensure_ascii=False)};
  const ctx = document.getElementById('chart_{idx}').getContext('2d');
  new Chart(ctx, {{
    type: 'line',
    data: {{ labels: timeLabels, datasets: datasets }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{ legend: {{ position: 'top', labels: {{ boxWidth: 12, font: {{ size: 11 }}, padding: 10 }} }} }},
      scales: {{
        x: {{ title: {{ display: true, text: '时间' }}, ticks: {{ maxRotation: 45, autoSkip: true, maxTicksLimit: 15 }} }},
        y: {{ title: {{ display: true, text: '指标值' }}, beginAtZero: true }}
      }}
    }}
  }});
  const tbody = document.getElementById('chart_{idx}_summary');
  summaryRows.forEach(row => {{
    const tr = document.createElement('tr');
    const fmtVal = v => v !== null ? (typeof v === 'number' ? v.toFixed(2) : v) : '<span style="color:#ccc">无数据</span>';
    tr.innerHTML = `<td>${{row.metric}}</td><td>${{fmtVal(row.min)}}</td><td>${{fmtVal(row.max)}}</td><td>${{fmtVal(row.avg)}}</td><td>${{row.count}}</td>`;
    tbody.appendChild(tr);
  }});
}})();"""


def render_conclusion(judgment_result):
    g = judgment_result["global"]
    color = "#27ae60" if g["verdict"] == "ok" else "#e74c3c"
    return f"""
<div style="text-align:center;padding:20px;background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:20px;">
  <div style="font-size:16px;font-weight:700;color:{color};">巡检结论：{g["summary"]}</div>
</div>"""
