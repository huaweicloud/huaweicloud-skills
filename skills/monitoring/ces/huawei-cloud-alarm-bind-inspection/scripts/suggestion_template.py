#!/usr/bin/env python3

CSS_TEMPLATE = """<style>
:root {
    --semi-color-primary: #0064FA;
    --semi-color-success: #3BB346;
    --semi-color-warning: #FC8800;
    --semi-color-danger: #F93920;
    --semi-color-bg-0: #FFFFFF;
    --semi-color-bg-1: #FFFFFF;
    --semi-color-text-0: #1C1F23;
    --semi-color-text-1: rgba(28,31,35,0.8);
    --semi-color-text-2: rgba(28,31,35,0.62);
    --semi-color-fill-0: rgba(46,50,56,0.05);
    --semi-color-fill-1: rgba(46,50,56,0.09);
    --semi-color-border: rgba(28,31,35,0.08);
    --semi-border-radius-small: 3px;
    --semi-border-radius-large: 12px;
    --shadow-elevated: 0 4px 14px rgba(0, 0, 0, 0.1);
}
html { scroll-behavior: smooth; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Helvetica, Arial, sans-serif;
    background: var(--semi-color-fill-0);
    color: var(--semi-color-text-0);
    line-height: 1.6;
    font-size: 14px;
}
.container { max-width: 1200px; margin: 0 auto; padding: 24px; }
.header {
    background: var(--semi-color-primary); color: white;
    padding: 32px; border-radius: var(--semi-border-radius-large); margin-bottom: 24px;
    display: flex; justify-content: space-between; align-items: flex-start;
}
.header-left { flex: 1; }
.header h1 { font-size: 28px; font-weight: 600; line-height: 40px; margin-bottom: 8px; }
.header .subtitle { opacity: 0.9; font-size: 14px; }
.header-right { display: flex; align-items: center; gap: 8px; margin-left: 24px; flex-shrink: 0; }
.card {
    background: var(--semi-color-bg-1); border-radius: var(--semi-border-radius-large);
    padding: 24px; margin-bottom: 24px; border: 1px solid var(--semi-color-border); overflow: hidden;
}
.card-header {
    font-size: 20px; font-weight: 600; margin-bottom: 16px;
    padding-bottom: 12px; border-bottom: 2px solid var(--semi-color-primary);
}
.stat-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px;
}
.stat-item {
    background: var(--semi-color-fill-0); padding: 20px;
    border-radius: var(--semi-border-radius-small); text-align: center;
    transition: background var(--semi-color-fill-1);
}
.stat-item:hover { background: var(--semi-color-fill-1); }
.stat-item .value { font-size: 32px; font-weight: 600; color: var(--semi-color-primary); line-height: 40px; }
.stat-item .value.danger { color: var(--semi-color-danger); }
.stat-item .label { font-size: 14px; color: var(--semi-color-text-1); margin-top: 8px; }
.tooltip-icon { display: inline-block; margin-left: 4px; font-size: 14px; font-style: normal; color: var(--semi-color-text-2); cursor: help; position: relative; }
.tooltip-icon::after { content: attr(data-tip); position: absolute; bottom: calc(100% + 6px); left: 50%; transform: translateX(-50%); background: var(--semi-color-text-0); color: #fff; font-size: 12px; font-weight: normal; padding: 6px 10px; border-radius: 4px; white-space: nowrap; opacity: 0; pointer-events: none; transition: opacity 0.2s; z-index: 10; }
.tooltip-icon:hover::after { opacity: 1; }
.svc-summary-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.svc-summary-table th, .svc-summary-table td { padding: 8px 10px; text-align: center; border-bottom: 1px solid var(--semi-color-border); }
.svc-summary-table th:first-child, .svc-summary-table td:first-child { text-align: left; font-weight: 600; white-space: nowrap; }
.svc-summary-table thead th { background: var(--semi-color-fill-1); font-weight: 600; }
.filter-bar {
    display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
}
.filter-bar label { font-size: 14px; font-weight: 600; color: var(--semi-color-text-0); }
.filter-bar select {
    border: 1px solid var(--semi-color-border); background: var(--semi-color-bg-1);
    color: var(--semi-color-text-0); border-radius: var(--semi-border-radius-small);
    padding: 6px 12px; font-size: 14px; min-width: 160px; cursor: pointer;
}
.filter-bar select:focus { outline: none; border-color: var(--semi-color-primary); }
.svc-select { position: relative; min-width: 200px; }
.svc-select-trigger { width: 100%; border: 1px solid var(--semi-color-border); background: var(--semi-color-bg-1); color: var(--semi-color-text-0); border-radius: var(--semi-border-radius-small); padding: 6px 28px 6px 12px; font-size: 14px; cursor: pointer; box-sizing: border-box; display: flex; align-items: center; justify-content: space-between; gap: 4px; min-height: 32px; }
.svc-select-trigger:hover { border-color: var(--semi-color-primary); }
.svc-select-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.svc-select-text.placeholder { color: var(--semi-color-text-2); }
.svc-select-arrow { font-size: 10px; opacity: 0.6; flex-shrink: 0; transition: transform 0.2s; }
.svc-select-trigger.open .svc-select-arrow { transform: rotate(180deg); }
.svc-select-dropdown { display: none; position: absolute; top: 100%; left: 0; right: 0; background: var(--semi-color-bg-1); border: 1px solid var(--semi-color-border); border-top: none; border-radius: 0 0 var(--semi-border-radius-small) var(--semi-border-radius-small); box-shadow: var(--shadow-elevated); z-index: 100; }
.svc-select-dropdown.open { display: block; }
.svc-select-search-wrap { padding: 8px 8px 4px; border-bottom: 1px solid var(--semi-color-border); position: relative; }
.svc-select-search { width: 100%; border: 1px solid var(--semi-color-border); background: var(--semi-color-bg-0); color: var(--semi-color-text-0); border-radius: var(--semi-border-radius-small); padding: 6px 24px 6px 8px; font-size: 13px; box-sizing: border-box; outline: none; }
.svc-select-search:focus { border-color: var(--semi-color-primary); }
.svc-select-search::placeholder { color: var(--semi-color-text-2); }
.svc-select-clear { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); width: 16px; height: 16px; border-radius: 50%; background: var(--semi-color-fill-1); color: var(--semi-color-text-2); font-size: 10px; line-height: 16px; text-align: center; cursor: pointer; display: none; border: none; padding: 0; }
.svc-select-clear.visible { display: block; }
.svc-select-clear:hover { background: var(--semi-color-fill-1); color: var(--semi-color-text-0); }
.svc-select-options { max-height: 200px; overflow-y: auto; }
.svc-select-option { padding: 8px 12px; cursor: pointer; font-size: 14px; color: var(--semi-color-text-1); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.svc-select-option:hover { background: var(--semi-color-fill-1); }
.svc-select-option.selected { background: rgba(0,100,250,0.08); color: var(--semi-color-primary); font-weight: 600; }
.svc-select-option.all-option { border-bottom: 1px solid var(--semi-color-border); color: var(--semi-color-text-2); }
.svc-select-no-result { padding: 12px; text-align: center; color: var(--semi-color-text-2); font-size: 13px; }
#event-detail-table td { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
thead tr { background: var(--semi-color-fill-1); text-align: left; }
th { padding: 10px 12px; font-weight: 600; color: var(--semi-color-text-0); }
th:nth-child(1), th:nth-child(2) { white-space: nowrap; }
th:nth-child(1), td:nth-child(1) { min-width: 100px; }
th:nth-child(2), td:nth-child(2) { min-width: 80px; }
td { padding: 10px 12px; border-bottom: 1px solid var(--semi-color-border); color: var(--semi-color-text-1); word-break: break-all; }
tbody tr:hover { background: var(--semi-color-fill-0); }
.conclusion {
    background: var(--semi-color-bg-1); border: 1px solid var(--semi-color-danger);
    border-radius: var(--semi-border-radius-large); padding: 24px; margin-bottom: 24px;
}
.conclusion .card-header { color: var(--semi-color-danger); border-bottom-color: var(--semi-color-danger); }
.conclusion p { margin: 8px 0; color: var(--semi-color-text-1); }
.conclusion .action { font-weight: 600; color: var(--semi-color-danger); }
.pagination {
    display: flex; align-items: center; justify-content: center; gap: 4px;
    padding: 16px 0 0; font-size: 12px; line-height: 16px;
}
.pagination button {
    border: 1px solid var(--semi-color-border); background: var(--semi-color-bg-1); color: var(--semi-color-text-1);
    border-radius: var(--semi-border-radius-small); padding: 4px 10px; cursor: pointer; font-size: 12px;
}
.pagination button:hover { background: var(--semi-color-fill-1); }
.pagination button.active { background: var(--semi-color-primary); color: #fff; border-color: var(--semi-color-primary); }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.pagination .page-info { color: var(--semi-color-text-2); margin: 0 8px; }
.pagination .dots { color: var(--semi-color-text-2); padding: 0 4px; }
.section-divider {
    display: flex; align-items: center; margin: 32px 0 24px; gap: 16px;
}
.section-divider::before, .section-divider::after {
    content: ''; flex: 1; height: 2px; background: var(--semi-color-border);
}
.section-divider span {
    font-size: 18px; font-weight: 600; color: var(--semi-color-primary);
    white-space: nowrap; padding: 0 8px;
}
.sub-header {
    font-size: 16px; font-weight: 600; margin: 20px 0 12px;
    padding-left: 12px; border-left: 3px solid var(--semi-color-primary);
    color: var(--semi-color-text-0);
}
.sub-header.secondary {
    border-left-color: var(--semi-color-text-2);
    color: var(--semi-color-text-1);
}
.tab-label {
    display: inline-block; padding: 6px 16px;
    border-radius: 8px 8px 0 0;
    font-size: 14px; font-weight: 600;
    color: #fff; cursor: default; margin-top: 16px;
}
.tab-label.primary { background: var(--semi-color-primary); }
.tab-label.secondary { background: var(--semi-color-text-2); }
.tab-table-wrap {
    border: 1px solid var(--semi-color-border);
    border-radius: 0 8px 8px 8px;
    margin-bottom: 20px; overflow: hidden;
}
.main-tab-bar {
    display: flex; align-items: center; justify-content: center;
    margin: 32px 0 24px; gap: 0;
}
.main-tab-bar::before, .main-tab-bar::after {
    content: ''; flex: 1; height: 2px; background: var(--semi-color-border);
}
.main-tab-item {
    padding: 8px 16px; font-size: 18px; font-weight: 600;
    color: var(--semi-color-text-2); cursor: pointer;
    border-bottom: 3px solid transparent; margin-bottom: -2px; transition: all 0.2s;
    user-select: none;
}
.main-tab-item:hover { color: var(--semi-color-primary); }
.main-tab-item.active {
    color: var(--semi-color-primary); border-bottom-color: var(--semi-color-primary);
}
.main-tab-content { display: none; }
.main-tab-content.active { display: block; }
</style>"""


def get_html_body(now, total_instances, instances_needing_action, total_missing, metric_coverage_rate, detail_col_headers, event_section):
    return """
<body>
    <div class="container">
        <div class="header">
            <div class="header-left">
                <h1>监控告警底线指标与事件补齐建议书</h1>
                <div class="subtitle">生成时间：""" + now + """</div>
            </div>

        </div>

        <div class="main-tab-bar">
            <div class="main-tab-item active" data-tab="ces-metric">指标基线</div>
            <div class="main-tab-item" data-tab="ces-event">事件基线</div>
        </div>

        <div class="main-tab-content active" id="ces-metric-tab-content">

        <div class="card" id="overview">
            <h2 class="card-header">概览</h2>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="value" id="metric-stat-total">""" + str(total_instances) + """</div>
                    <div class="label">核心实例总数</div>
                </div>
                <div class="stat-item">
                    <div class="value danger" id="metric-stat-needing">""" + str(instances_needing_action) + """</div>
                    <div class="label">需补齐实例数</div>
                </div>
                <div class="stat-item">
                    <div class="value danger" id="metric-stat-missing">""" + str(total_missing) + """</div>
                    <div class="label">缺失指标总数</div>
                </div>
                <div class="stat-item">
                    <div class="value" id="metric-stat-rate">""" + metric_coverage_rate + """</div>
                    <div class="label">指标覆盖率<i class="tooltip-icon" data-tip="已覆盖底线指标数 / 总底线指标数">ⓘ</i></div>
                </div>
            </div>
        </div>

        <div class="card" id="svc-stats">
            <h2 class="card-header">按服务统计</h2>
            <div class="tab-label primary">有指标基线的核心实例</div>
            <div class="tab-table-wrap">
                <table class="svc-summary-table">
                    <thead>
                        <tr><th>监控体系</th><th>云服务-指标维度</th><th>实例总数</th><th>完全配置</th><th>部分配置</th><th>未配置</th><th>建议指标数</th><th>总体配置率</th></tr>
                    </thead>
                    <tbody id="metric-svc-stat-tbody"></tbody>
                </table>
            </div>
            <div id="no-baseline-section" style="display:none;">
                <div class="tab-label secondary">无指标基线的核心实例</div>
                <div class="tab-table-wrap">
                    <table class="svc-summary-table">
                        <thead>
                            <tr><th>云服务</th><th>实例数量</th><th>实例ID列表</th></tr>
                        </thead>
                        <tbody id="no-baseline-tbody"></tbody>
                    </table>
                </div>
            </div>
            <div id="non-exist-section" style="display:none;">
                <div class="tab-label" style="background:var(--semi-color-danger);">不存在的实例</div>
                <span style="font-size:12px;color:var(--semi-color-text-2);margin-left:12px;">1. 请前往OA-监控告警-资源分组-新建-添加资源中验证是否存在该实例。&nbsp;&nbsp;2. 请确认【核心实例清单】中region是否填对。</span>
                <div class="tab-table-wrap">
                    <table class="svc-summary-table">
                        <thead>
                            <tr><th>云服务</th><th>实例数量</th><th>实例ID列表</th></tr>
                        </thead>
                        <tbody id="non-exist-tbody"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="card" id="detail" style="min-height:500px;">
            <h2 class="card-header">补齐明细</h2>
            <div class="filter-bar">
                <label for="svc-filter">服务筛选：</label>
                <div class="svc-select" id="svc-select">
                    <div class="svc-select-trigger" id="svc-select-trigger">
                        <span class="svc-select-text placeholder" id="svc-select-text">全部服务</span>
                        <span class="svc-select-arrow">▼</span>
                    </div>
                    <div class="svc-select-dropdown" id="svc-select-dropdown">
                        <div class="svc-select-search-wrap">
                            <input type="text" class="svc-select-search" id="svc-search" placeholder="搜索服务" autocomplete="off" />
                            <button type="button" class="svc-select-clear" id="svc-search-clear">&times;</button>
                        </div>
                        <div class="svc-select-options" id="svc-select-options"></div>
                    </div>
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>监控体系</th>
                        <th>实例ID</th>
                        <th>Region</th>
                        <th>服务</th>
                        <th>指标维度</th>
                        """ + detail_col_headers + """
                    </tr>
                </thead>
                <tbody id="detail-tbody"></tbody>
            </table>
            <div class="pagination" id="detail-pagination"></div>
        </div>


        </div>

        <div class="main-tab-content" id="ces-event-tab-content">

        """ + event_section + """


        </div>



        <div class="conclusion card" id="conclusion">
            <h2 class="card-header">自动化可行性结论</h2>
            <p><strong>是否可自动补齐：否</strong></p>
            <p>原因：人机账号不允许通过agent操作现网，建议书仅作为人工操作参考。</p>
            <p class="action">建议操作：人工通过Console或审批流程按建议书补齐告警规则。</p>
        </div>
    </div>
"""


def get_js_script(metric_overview_json, metric_svc_stat_json,
                  no_baseline_json, non_exist_json, rows_json, event_overview_json,
                  event_svc_stat_json, event_rows_json,
                  event_no_baseline_json, event_non_exist_json, svc_options_json, col_keys_json,
                  event_col_keys_json, event_svc_options_json):
    return """
<script>
var METRIC_OVERVIEW = """ + metric_overview_json + """;
var METRIC_SVC_STAT = """ + metric_svc_stat_json + """;
var NO_BASELINE = """ + no_baseline_json + """;
var NON_EXIST = """ + non_exist_json + """;
var ROWS = """ + rows_json + """;
var EVENT_OVERVIEW = """ + event_overview_json + """;
var EVENT_SVC_STAT = """ + event_svc_stat_json + """;
var EVENT_ROWS = """ + event_rows_json + """;
var EVENT_NO_BASELINE = """ + event_no_baseline_json + """;
var EVENT_NON_EXIST = """ + event_non_exist_json + """;

function escapeHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}


function renderMetricOverview() {
  var d = METRIC_OVERVIEW;
  document.getElementById('metric-stat-total').textContent = d.total_instances || 0;
  document.getElementById('metric-stat-needing').textContent = d.instances_needing_action || 0;
  document.getElementById('metric-stat-missing').textContent = d.total_missing || 0;
  var rateEl = document.getElementById('metric-stat-rate');
  rateEl.textContent = d.coverage_rate || 'N/A';
  rateEl.className = 'value' + (d.coverage_rate && d.coverage_rate !== 'N/A' && parseFloat(d.coverage_rate) < 100 ? '' : '');
}

function renderMetricSvcStat() {
  var data = METRIC_SVC_STAT;
  var tbody = document.getElementById('metric-svc-stat-tbody');
  var html = '';
  var totalInst = 0, totalFully = 0, totalPartially = 0, totalUnbound = 0;
  var totalBoundBaseline = 0, totalTotalBaseline = 0;

  for (var i = 0; i < data.length; i++) {
    var r = data[i];
    var isNoRules = r.is_no_rules || r.is_no_baseline || false;
    var rateVal = 0;
    if (r.bind_rate !== 'N/A') rateVal = parseFloat(r.bind_rate);
    var rateStyle = isNoRules ? 'color:var(--semi-color-text-2);'
      : rateVal >= 100 ? 'color:var(--semi-color-success);font-weight:600;'
      : rateVal > 0 ? 'color:var(--semi-color-primary);font-weight:600;'
      : 'color:var(--semi-color-danger);font-weight:600;';
    var metricStyle = isNoRules ? 'color:var(--semi-color-text-2);'
      : r.missing_metrics === 0 ? 'color:var(--semi-color-text-2);' : 'color:var(--semi-color-primary);font-weight:600;';
    html += '<tr>';
    html += '<td>' + escapeHtml(r.monitor_system || 'CES') + '</td>';
    html += '<td style="font-weight:600;">' + escapeHtml(r.svc_dim) + '</td>';
    html += '<td>' + r.total_inst + '</td>';
    html += '<td>' + escapeHtml(String(r.fully)) + '</td>';
    html += '<td>' + escapeHtml(String(r.partially)) + '</td>';
    html += '<td>' + r.unbound + '</td>';
    html += '<td style="' + metricStyle + '">' + escapeHtml(String(r.baseline_metrics_count)) + '</td>';
    html += '<td style="' + rateStyle + '">' + escapeHtml(r.bind_rate) + '</td>';
    html += '</tr>';
    totalInst += r.total_inst;
    totalUnbound += r.unbound;
    if (!isNoRules) {
      totalFully += (typeof r.fully === 'number' ? r.fully : 0);
      totalPartially += (typeof r.partially === 'number' ? r.partially : 0);
      totalBoundBaseline += (typeof r.bound_baseline === 'number' ? r.bound_baseline : 0);
      totalTotalBaseline += (typeof r.total_baseline === 'number' ? r.total_baseline : 0);
    }
  }
  var totalRate = totalTotalBaseline > 0 ? (totalBoundBaseline / totalTotalBaseline * 100).toFixed(1) + '%' : 'N/A';
  var totalRateVal = totalTotalBaseline > 0 ? totalBoundBaseline / totalTotalBaseline * 100 : 0;
  var totalRateStyle = totalRateVal >= 100 ? 'color:var(--semi-color-success);font-weight:600;'
    : totalRateVal > 0 ? 'color:var(--semi-color-primary);font-weight:600;'
    : 'color:var(--semi-color-danger);font-weight:600;';
  html += '<tr style="background:var(--semi-color-fill-1);font-weight:700;">';
  html += '<td>-</td>';
  html += '<td style="font-weight:700;">总计</td>';
  html += '<td style="font-weight:700;">' + totalInst + '</td>';
  html += '<td style="font-weight:700;">' + totalFully + '</td>';
  html += '<td style="font-weight:700;">' + totalPartially + '</td>';
  html += '<td style="font-weight:700;">' + totalUnbound + '</td>';
  html += '<td>-</td>';
  html += '<td style="' + totalRateStyle + '">' + totalRate + '</td>';
  html += '</tr>';
  tbody.innerHTML = html;
}

function renderNoBaseline() {
  var data = NO_BASELINE;
  var section = document.getElementById('no-baseline-section');
  if (!section) return;
  if (!data || data.length === 0) { section.style.display = 'none'; return; }
  section.style.display = '';
  var tbody = document.getElementById('no-baseline-tbody');
  var bySvc = {};
  for (var i = 0; i < data.length; i++) {
    var r = data[i];
    if (!bySvc[r.service]) bySvc[r.service] = [];
    bySvc[r.service].push(r.instance_id);
  }
  var html = '';
  var svcKeys = Object.keys(bySvc).sort();
  for (var j = 0; j < svcKeys.length; j++) {
    var svc = svcKeys[j];
    var ids = bySvc[svc];
    html += '<tr>';
    html += '<td style="font-weight:600;">' + escapeHtml(svc) + '</td>';
    html += '<td>' + ids.length + '</td>';
    var idLines = [];
    for (var k = 0; k < ids.length; k += 3) {
      var chunk = ids.slice(k, k + 3).map(function(id) { return escapeHtml(id); });
      idLines.push(chunk.join('\\u3001'));
    }
    html += '<td style="text-align:left;font-size:12px;"><div style="max-height:150px;overflow-y:auto;word-break:break-all;">' + idLines.join('<br>') + '</div></td>';
    html += '</tr>';
  }
  tbody.innerHTML = html;
}

function renderNonExist() {
  var data = NON_EXIST;
  var section = document.getElementById('non-exist-section');
  if (!section) return;
  if (!data || data.length === 0) { section.style.display = 'none'; return; }
  section.style.display = '';
  var tbody = document.getElementById('non-exist-tbody');
  var bySvc = {};
  for (var i = 0; i < data.length; i++) {
    var r = data[i];
    if (!bySvc[r.service]) bySvc[r.service] = [];
    bySvc[r.service].push(r.instance_id);
  }
  var html = '';
  var svcKeys = Object.keys(bySvc).sort();
  for (var j = 0; j < svcKeys.length; j++) {
    var svc = svcKeys[j];
    var ids = bySvc[svc];
    html += '<tr>';
    html += '<td style="font-weight:600;">' + escapeHtml(svc) + '</td>';
    html += '<td>' + ids.length + '</td>';
    var idLines = [];
    for (var k = 0; k < ids.length; k += 3) {
      var chunk = ids.slice(k, k + 3).map(function(id) { return escapeHtml(id); });
      idLines.push(chunk.join('\\u3001'));
    }
    html += '<td style="text-align:left;font-size:12px;"><div style="max-height:150px;overflow-y:auto;word-break:break-all;">' + idLines.join('<br>') + '</div></td>';
    html += '</tr>';
  }
  tbody.innerHTML = html;
}

function renderEventNoBaseline() {
  var data = EVENT_NO_BASELINE;
  var section = document.getElementById('event-no-baseline-section');
  if (!section) return;
  if (!data || data.length === 0) { section.style.display = 'none'; return; }
  section.style.display = '';
  var tbody = document.getElementById('event-no-baseline-tbody');
  var html = '';
  for (var i = 0; i < data.length; i++) {
    var r = data[i];
    html += '<tr>';
    html += '<td style="font-weight:600;">' + escapeHtml(r.service) + '</td>';
    html += '<td>' + r.instance_count + '</td>';
    var ids = r.instance_ids || [];
    var idLines = [];
    for (var k = 0; k < ids.length; k += 3) {
      var chunk = ids.slice(k, k + 3).map(function(id) { return escapeHtml(id); });
      idLines.push(chunk.join('\\u3001'));
    }
    html += '<td style="text-align:left;font-size:12px;"><div style="max-height:150px;overflow-y:auto;word-break:break-all;">' + idLines.join('<br>') + '</div></td>';
    html += '</tr>';
  }
  tbody.innerHTML = html;
}

function renderEventNonExist() {
  var data = EVENT_NON_EXIST;
  var section = document.getElementById('event-non-exist-section');
  if (!section) return;
  if (!data || data.length === 0) { section.style.display = 'none'; return; }
  section.style.display = '';
  var tbody = document.getElementById('event-non-exist-tbody');
  var bySvc = {};
  for (var i = 0; i < data.length; i++) {
    var r = data[i];
    if (!bySvc[r.service]) bySvc[r.service] = [];
    bySvc[r.service].push(r.instance_id);
  }
  var html = '';
  var svcKeys = Object.keys(bySvc).sort();
  for (var j = 0; j < svcKeys.length; j++) {
    var svc = svcKeys[j];
    var ids = bySvc[svc];
    html += '<tr>';
    html += '<td style="font-weight:600;">' + escapeHtml(svc) + '</td>';
    html += '<td>' + ids.length + '</td>';
    var idLines = [];
    for (var k = 0; k < ids.length; k += 3) {
      var chunk = ids.slice(k, k + 3).map(function(id) { return escapeHtml(id); });
      idLines.push(chunk.join('\\u3001'));
    }
    html += '<td style="text-align:left;font-size:12px;"><div style="max-height:150px;overflow-y:auto;word-break:break-all;">' + idLines.join('<br>') + '</div></td>';
    html += '</tr>';
  }
  tbody.innerHTML = html;
}

var SVC_OPTIONS = """ + svc_options_json + """;
var COL_KEYS = """ + col_keys_json + """;
var metricDetailCurrentPage = 1;
var METRIC_DETAIL_PAGE_SIZE = 10;
var svcSelect = null;

function getMetricDetailFilteredData() {
  var svc = svcSelect ? svcSelect.getValue() : '';
  var rows = ROWS;
  return rows.filter(function(r) {
    if (svc && r.service + '|' + (r.metric_dimension || '未配置') !== svc) return false;
    return true;
  });
}

function renderMetricDetail() {
  var data = getMetricDetailFilteredData();
  var totalPages = Math.max(1, Math.ceil(data.length / METRIC_DETAIL_PAGE_SIZE));
  if (metricDetailCurrentPage > totalPages) metricDetailCurrentPage = totalPages;
  var start = (metricDetailCurrentPage - 1) * METRIC_DETAIL_PAGE_SIZE;
  var end = metricDetailCurrentPage * METRIC_DETAIL_PAGE_SIZE;
  var pageData = data.slice(start, end);
  var tbody = document.getElementById('detail-tbody');
  var html = '';
  if (data.length === 0) {
    html = '<tr><td colspan="' + (5 + COL_KEYS.length) + '" style="text-align:center;color:var(--semi-color-text-2);padding:24px;">无补齐数据</td></tr>';
  }
  for (var i = 0; i < pageData.length; i++) {
    var r = pageData[i];
    html += '<tr>';
    html += '<td>' + escapeHtml(r.monitor_system || 'CES') + '</td>';
    html += '<td>' + escapeHtml(r.instance_id) + '</td>';
    html += '<td>' + escapeHtml(r.region || '') + '</td>';
    html += '<td>' + escapeHtml(r.service) + '</td>';
    html += '<td>' + escapeHtml(r.metric_dimension_cn || '') + '</td>';
    if (r._no_missing) {
      html += '<td colspan="' + COL_KEYS.length + '" style="color:var(--semi-color-text-2);">缺失指标</td>';
    } else {
      for (var j = 0; j < COL_KEYS.length; j++) {
        html += '<td>' + escapeHtml(r[COL_KEYS[j]]) + '</td>';
      }
    }
    html += '</tr>';
  }
  tbody.innerHTML = html;
  renderMetricDetailPagination(data.length, totalPages);
}

function renderMetricDetailPagination(totalRows, totalPages) {
  var pgEl = document.getElementById('detail-pagination');
  pgEl.innerHTML = '';
  if (totalPages <= 1) return;
  var prev = document.createElement('button');
  prev.textContent = '<';
  prev.disabled = metricDetailCurrentPage === 1;
  prev.onclick = function() { metricDetailCurrentPage--; renderMetricDetail(); };
  pgEl.appendChild(prev);
  function addBtn(p) {
    var btn = document.createElement('button');
    btn.textContent = p;
    btn.className = p === metricDetailCurrentPage ? 'active' : '';
    btn.onclick = function() { metricDetailCurrentPage = p; renderMetricDetail(); };
    pgEl.appendChild(btn);
  }
  function addDots() {
    var span = document.createElement('span');
    span.textContent = '...';
    span.className = 'dots';
    pgEl.appendChild(span);
  }
  if (totalPages <= 7) {
    for (var p = 1; p <= totalPages; p++) addBtn(p);
  } else {
    addBtn(1);
    if (metricDetailCurrentPage > 4) addDots();
    var s = Math.max(2, metricDetailCurrentPage - 1);
    var e = Math.min(totalPages - 1, metricDetailCurrentPage + 1);
    if (metricDetailCurrentPage <= 4) { s = 2; e = 5; }
    if (metricDetailCurrentPage >= totalPages - 3) { s = totalPages - 4; e = totalPages - 1; }
    for (var p = s; p <= e; p++) addBtn(p);
    if (metricDetailCurrentPage < totalPages - 3) addDots();
    addBtn(totalPages);
  }
  var next = document.createElement('button');
  next.textContent = '>';
  next.disabled = metricDetailCurrentPage === totalPages;
  next.onclick = function() { metricDetailCurrentPage++; renderMetricDetail(); };
  pgEl.appendChild(next);
  var info = document.createElement('span');
  info.className = 'page-info';
  info.textContent = metricDetailCurrentPage + ' / ' + totalPages + ' 页（共' + totalRows + '条）';
  pgEl.appendChild(info);
}

function renderEventOverview() {
  var d = EVENT_OVERVIEW;
  document.getElementById('event-stat-instances').textContent = d.total_instances || 0;
  document.getElementById('event-stat-needing').textContent = d.instances_needing_action || 0;
  document.getElementById('event-stat-no-rules').textContent = d.missing_events_total || 0;
  document.getElementById('event-stat-rate').textContent = d.overall_rate || 'N/A';
}

var EVENT_COL_KEYS = """ + event_col_keys_json + """;
var EVENT_SVC_OPTIONS = """ + event_svc_options_json + """;

function renderEventSvcStat() {
  var data = EVENT_SVC_STAT;
  var tbody = document.getElementById('svc-stat-tbody');
  if (!tbody) return;
  var html = '';
  var sumTotal = 0, sumFully = 0, sumPartial = 0, sumUnbound = 0, sumBaselineEvt = 0;
  var sumCoveredBaseline = 0, sumTotalBaseline = 0;
  for (var i = 0; i < data.length; i++) {
    var r = data[i];
    var rateVal = 0;
    if (r.bind_rate !== 'N/A') rateVal = parseFloat(r.bind_rate);
    var rateStyle = rateVal >= 100 ? 'color:var(--semi-color-success);font-weight:600;'
      : rateVal > 0 ? 'color:var(--semi-color-primary);font-weight:600;'
      : 'color:var(--semi-color-danger);font-weight:600;';
    html += '<tr>';
    html += '<td>' + escapeHtml(r.monitor_system || 'CES') + '</td>';
    html += '<td style="font-weight:600;">' + escapeHtml(r.svc) + '</td>';
    html += '<td>' + r.total_instances + '</td>';
    html += '<td style="color:var(--semi-color-success);">' + r.fully_bound + '</td>';
    html += '<td style="color:var(--semi-color-primary);">' + r.partially_bound + '</td>';
    html += '<td style="color:var(--semi-color-danger);">' + (r.unbound + r.no_online_rules) + '</td>';
    html += '<td style="color:var(--semi-color-primary);font-weight:600;">' + r.baseline_event_count + '</td>';
    html += '<td style="' + rateStyle + '">' + escapeHtml(r.bind_rate) + '</td>';
    html += '</tr>';
    sumTotal += r.total_instances;
    sumFully += r.fully_bound;
    sumPartial += r.partially_bound;
    sumUnbound += (r.unbound + r.no_online_rules);
    sumBaselineEvt += r.baseline_event_count;
    sumCoveredBaseline += (r.covered_baseline || 0);
    sumTotalBaseline += (r.total_baseline || 0);
  }
  var sumRate = sumTotalBaseline > 0 ? (sumCoveredBaseline / sumTotalBaseline * 100).toFixed(1) + '%' : 'N/A';
  var sumRateVal = sumTotalBaseline > 0 ? sumCoveredBaseline / sumTotalBaseline * 100 : 0;
  var sumRateStyle = sumRateVal >= 100 ? 'color:var(--semi-color-success);font-weight:700;'
    : sumRateVal > 0 ? 'color:var(--semi-color-primary);font-weight:700;'
    : 'color:var(--semi-color-danger);font-weight:700;';
  html += '<tr style="background:var(--semi-color-fill-0);font-weight:700;">';
  html += '<td>-</td>';
  html += '<td>总计</td>';
  html += '<td>' + sumTotal + '</td>';
  html += '<td style="color:var(--semi-color-success);">' + sumFully + '</td>';
  html += '<td style="color:var(--semi-color-primary);">' + sumPartial + '</td>';
  html += '<td style="color:var(--semi-color-danger);">' + sumUnbound + '</td>';
  html += '<td style="color:var(--semi-color-primary);">' + sumBaselineEvt + '</td>';
  html += '<td style="' + sumRateStyle + '">' + escapeHtml(sumRate) + '</td>';
  html += '</tr>';
  tbody.innerHTML = html;
  var cells = tbody.querySelectorAll('td');
  for (var ci = 0; ci < cells.length; ci++) {
    if (cells[ci].scrollWidth > cells[ci].clientWidth) {
      cells[ci].title = cells[ci].textContent;
    }
  }
}

var eventDetailCurrentPage = 1;
var EVENT_DETAIL_PAGE_SIZE = 10;
var eventSvcSelect = null;

function getEventDetailFilteredData() {
  var svc = eventSvcSelect ? eventSvcSelect.getValue() : '';
  var rows = EVENT_ROWS;
  return rows.filter(function(r) {
    if (svc && r.svc !== svc) return false;
    return true;
  });
}

function renderEventDetail() {
  var card = document.getElementById('event-detail');
  if (!card) return;
  var data = getEventDetailFilteredData();
  var totalPages = Math.max(1, Math.ceil(data.length / EVENT_DETAIL_PAGE_SIZE));
  if (eventDetailCurrentPage > totalPages) eventDetailCurrentPage = totalPages;
  var start = (eventDetailCurrentPage - 1) * EVENT_DETAIL_PAGE_SIZE;
  var end = eventDetailCurrentPage * EVENT_DETAIL_PAGE_SIZE;
  var pageData = data.slice(start, end);
  var tbody = document.getElementById('event-tbody');
  var html = '';
  if (data.length === 0) {
    html = '<tr><td colspan="' + (4 + EVENT_COL_KEYS.length) + '" style="text-align:center;color:var(--semi-color-text-2);padding:24px;">无补齐数据</td></tr>';
  }
  for (var i = 0; i < pageData.length; i++) {
    var r = pageData[i];
    html += '<tr>';
    html += '<td>' + escapeHtml(r.monitor_system || 'CES') + '</td>';
    html += '<td>' + escapeHtml(r.instance_id) + '</td>';
    html += '<td>' + escapeHtml(r.region || '') + '</td>';
    html += '<td>' + escapeHtml(r.svc) + '</td>';
    if (r._no_missing) {
      html += '<td colspan="' + EVENT_COL_KEYS.length + '" style="color:var(--semi-color-text-2);">无缺失事件</td>';
    } else {
      for (var j = 0; j < EVENT_COL_KEYS.length; j++) {
        html += '<td>' + escapeHtml(r[EVENT_COL_KEYS[j]]) + '</td>';
      }
    }
    html += '</tr>';
  }
  tbody.innerHTML = html;
  var cells = tbody.querySelectorAll('td');
  for (var ci = 0; ci < cells.length; ci++) {
    if (cells[ci].scrollWidth > cells[ci].clientWidth) {
      cells[ci].title = cells[ci].textContent;
    }
    cells[ci].addEventListener('click', function() {
      if (this.querySelector('input')) return;
      var input = document.createElement('input');
      input.type = 'text';
      input.readOnly = true;
      input.value = this.textContent;
      input.style.cssText = 'width:100%;box-sizing:border-box;border:1px solid var(--semi-color-primary);border-radius:3px;padding:2px 4px;font-size:14px;background:#fff;outline:none;';
      this.textContent = '';
      this.appendChild(input);
      input.select();
      input.addEventListener('blur', function() {
        var td = this.parentNode;
        td.textContent = this.value;
      });
      input.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') this.blur();
      });
    });
  }
  renderEventDetailPagination(data.length, totalPages);
}

function renderEventDetailPagination(totalRows, totalPages) {
  var pgEl = document.getElementById('event-pagination');
  if (!pgEl) return;
  pgEl.innerHTML = '';
  if (totalPages <= 1) return;
  function addBtn(p) {
    var btn = document.createElement('button');
    btn.textContent = p;
    btn.className = p === eventDetailCurrentPage ? 'active' : '';
    btn.onclick = function() { eventDetailCurrentPage = p; renderEventDetail(); };
    pgEl.appendChild(btn);
  }
  function addDots() {
    var span = document.createElement('span');
    span.textContent = '...';
    span.className = 'dots';
    pgEl.appendChild(span);
  }
  var prev = document.createElement('button');
  prev.textContent = '<';
  prev.disabled = eventDetailCurrentPage === 1;
  prev.onclick = function() { eventDetailCurrentPage--; renderEventDetail(); };
  pgEl.appendChild(prev);
  if (totalPages <= 7) {
    for (var p = 1; p <= totalPages; p++) addBtn(p);
  } else {
    addBtn(1);
    if (eventDetailCurrentPage > 4) addDots();
    var s = Math.max(2, eventDetailCurrentPage - 1);
    var e = Math.min(totalPages - 1, eventDetailCurrentPage + 1);
    if (eventDetailCurrentPage <= 4) { s = 2; e = 5; }
    if (eventDetailCurrentPage >= totalPages - 3) { s = totalPages - 4; e = totalPages - 1; }
    for (var p = s; p <= e; p++) addBtn(p);
    if (eventDetailCurrentPage < totalPages - 3) addDots();
    addBtn(totalPages);
  }
  var next = document.createElement('button');
  next.textContent = '>';
  next.disabled = eventDetailCurrentPage === totalPages;
  next.onclick = function() { eventDetailCurrentPage++; renderEventDetail(); };
  pgEl.appendChild(next);
  var info = document.createElement('span');
  info.className = 'page-info';
  info.textContent = eventDetailCurrentPage + ' / ' + totalPages + ' 页（共' + totalRows + '条）';
  pgEl.appendChild(info);
}

function initSearchSelect(selectId, optionsData, onSelect) {
  var container = document.getElementById(selectId);
  var trigger = container.querySelector('.svc-select-trigger');
  var textEl = container.querySelector('.svc-select-text');
  var dropdown = container.querySelector('.svc-select-dropdown');
  var searchInput = container.querySelector('.svc-select-search');
  var searchClear = container.querySelector('.svc-select-clear');
  var optionsEl = container.querySelector('.svc-select-options');
  var selectedValue = '';

  function updateClearBtn() {
    if (searchClear) {
      if (searchInput.value) searchClear.className = 'svc-select-clear visible';
      else searchClear.className = 'svc-select-clear';
    }
  }

  function openDropdown() {
    searchInput.value = '';
    renderOptions('');
    dropdown.classList.add('open');
    trigger.classList.add('open');
    setTimeout(function() { searchInput.focus(); }, 0);
  }

  function closeDropdown() {
    dropdown.classList.remove('open');
    trigger.classList.remove('open');
  }

  function renderOptions(keyword) {
    var kw = (keyword || '').toLowerCase();
    var html = '';
    var hasMatch = false;
    for (var i = 0; i < optionsData.length; i++) {
      var opt = optionsData[i];
      if (kw && opt.value !== '' && opt.label.toLowerCase().indexOf(kw) === -1 && opt.value.toLowerCase().indexOf(kw) === -1) continue;
      hasMatch = true;
      var cls = 'svc-select-option';
      if (opt.value === '') cls += ' all-option';
      if (opt.value === selectedValue) cls += ' selected';
      html += '<div class="' + cls + '" data-value="' + opt.value + '">' + escapeHtml(opt.label) + '</div>';
    }
    if (!hasMatch) html = '<div class="svc-select-no-result">无匹配结果</div>';
    optionsEl.innerHTML = html;
    var items = optionsEl.querySelectorAll('.svc-select-option');
    for (var j = 0; j < items.length; j++) {
      items[j].addEventListener('mousedown', function(e) {
        e.preventDefault();
        var val = this.getAttribute('data-value');
        selectedValue = val;
        for (var k = 0; k < optionsData.length; k++) {
          if (optionsData[k].value === val) {
            textEl.textContent = optionsData[k].label;
            textEl.classList.remove('placeholder');
            break;
          }
        }
        if (val === '') {
          textEl.textContent = '全部服务';
          textEl.classList.add('placeholder');
        }
        closeDropdown();
        if (onSelect) onSelect(val);
      });
    }
  }

  trigger.addEventListener('click', function(e) {
    if (dropdown.classList.contains('open')) {
      closeDropdown();
    } else {
      openDropdown();
    }
  });

  searchInput.addEventListener('input', function() {
    renderOptions(searchInput.value);
    updateClearBtn();
  });

  searchInput.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') { closeDropdown(); }
  });

  document.addEventListener('mousedown', function(e) {
    if (!container.contains(e.target)) closeDropdown();
  });

  if (searchClear) {
    searchClear.addEventListener('click', function(e) {
      e.stopPropagation();
      searchInput.value = '';
      renderOptions('');
      updateClearBtn();
      searchInput.focus();
    });
  }

  return { getValue: function() { return selectedValue; }, reset: function() { selectedValue = ''; textEl.textContent = '全部服务'; textEl.classList.add('placeholder'); }, updateOptions: function(newOptionsData) { optionsData = newOptionsData; selectedValue = ''; textEl.textContent = '全部服务'; textEl.classList.add('placeholder'); } };
}

document.querySelectorAll('.main-tab-item').forEach(function(tab) {
    tab.addEventListener('click', function() {
        document.querySelectorAll('.main-tab-item').forEach(function(t) { t.classList.remove('active'); });
        document.querySelectorAll('.main-tab-content').forEach(function(c) { c.classList.remove('active'); });
        this.classList.add('active');
        document.getElementById(this.getAttribute('data-tab') + '-tab-content').classList.add('active');
    });
});

svcSelect = initSearchSelect('svc-select', SVC_OPTIONS, function(val) {
  metricDetailCurrentPage = 1; renderMetricDetail();
});

eventSvcSelect = initSearchSelect('event-svc-select', EVENT_SVC_OPTIONS, function(val) {
  eventDetailCurrentPage = 1; renderEventDetail();
});

renderMetricOverview();
renderMetricSvcStat();
renderNoBaseline();
renderNonExist();
renderMetricDetail();
renderEventOverview();
renderEventSvcStat();
renderEventNoBaseline();
renderEventNonExist();
renderEventDetail();

</script>"""
