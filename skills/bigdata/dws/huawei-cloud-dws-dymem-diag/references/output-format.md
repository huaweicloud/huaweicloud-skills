# Output Format - DWS Memory High Diagnosis

**Note**: Strictly output and return according to the template below. Do not analyze or summarize the template content, do not omit any part, do not modify the template structure. The output must be consistent with the template.

## HTML Template

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; margin: 20px; background: #f5f7fa; color: #1d2129; }
  .report { max-width: 960px; margin: 0 auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); overflow: hidden; }
  .header { background: linear-gradient(135deg, #722ed1, #1890ff); color: #fff; padding: 24px 32px; }
  .header h1 { margin: 0; font-size: 22px; letter-spacing: 1px; }
  .header .subtitle { margin-top: 4px; font-size: 13px; opacity: 0.85; }
  .section { padding: 20px 32px; border-bottom: 1px solid #e5e6eb; }
  .section:last-child { border-bottom: none; }
  .section-title { font-size: 16px; font-weight: 600; color: #722ed1; margin: 0 0 12px 0; padding-left: 10px; border-left: 3px solid #722ed1; }
  .info-grid { display: grid; grid-template-columns: 120px 1fr; row-gap: 8px; }
  .info-key { color: #86909c; font-size: 14px; text-align: right; padding-right: 12px; }
  .info-val { color: #1d2129; font-size: 14px; font-weight: 500; word-break: break-all; }
  .conclusion-item { padding: 8px 12px; margin-bottom: 6px; background: #fff7e8; border-left: 3px solid #ff7d00; border-radius: 0 4px 4px 0; font-size: 14px; }
  .conclusion-item.normal { background: #e8ffea; border-left-color: #00b42a; }
  .locate-block { margin: 6px 0 6px 16px; padding: 10px 14px; background: #f7f8fa; border-radius: 4px; font-size: 13px; }
  .locate-block .loc-row { display: flex; margin-bottom: 4px; }
  .locate-block .loc-key { width: 80px; color: #86909c; flex-shrink: 0; }
  .locate-block .loc-val { color: #1d2129; word-break: break-all; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th { background: #f2f3f5; color: #4e5969; font-weight: 600; text-align: left; padding: 10px 12px; border-bottom: 2px solid #e5e6eb; }
  td { padding: 10px 12px; border-bottom: 1px solid #f2f3f5; vertical-align: top; }
  tr:hover td { background: #f7f8fa; }
  .sql-text { font-family: "Cascadia Code", "Fira Code", "Consolas", monospace; font-size: 12px; color: #4e5969; max-width: 500px; word-break: break-all; white-space: pre-wrap; }
  .pct-bar { display: inline-block; height: 16px; border-radius: 2px; background: linear-gradient(90deg, #722ed1, #1890ff); vertical-align: middle; }
  .pct-val { margin-left: 6px; font-weight: 600; color: #722ed1; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 12px; font-weight: 500; }
  .tag-warn { background: #fff7e8; color: #ff7d00; }
  .tag-danger { background: #ffece8; color: #cb2634; }
  .tag-info { background: #f0e8ff; color: #722ed1; }
</style>
</head>
<body>
<div class="report">

  <div class="header">
    <h1>DWS 集群内存诊断报告</h1>
    <div class="subtitle">{region_id} | {resource_name}</div>
  </div>

  <div class="section">
    <div class="section-title">基本信息</div>
    <div class="info-grid">
      <span class="info-key">所属服务</span><span class="info-val">DWS</span>
      <span class="info-key">所属区域</span><span class="info-val">{region_id}</span>
      <span class="info-key">集群名称</span><span class="info-val">{resource_name}</span>
      <span class="info-key">集群ID</span><span class="info-val">{resource_id}</span>
      <span class="info-key">TOP节点</span><span class="info-val">{node_name}</span>
    </div>
  </div>

  <div class="section">
    <div class="section-title">问题节点内存概览</div>
    <table>
      <tr><th>节点名称</th><th>节点IP</th><th>内存使用率</th><th>已用内存(MB)</th><th>总内存(MB)</th><th>可用内存(MB)</th><th>缓存(MB)</th></tr>
      <tr><td>{node_name}</td><td>{node_ip}</td><td>{mem_usage}%</td><td>{used}</td><td>{total}</td><td>{available}</td><td>{buffers_cached}</td></tr>
    </table>
  </div>

  <div class="section">
    <div class="section-title">诊断结论</div>
    {diagnosis_summary}
  </div>

  <div class="section">
    <div class="section-title">内存贡献 Top3 语句</div>
    <table>
      <tr><th style="width:40px">#</th><th style="width:180px">QueryID</th><th style="width:80px">用户</th><th style="width:80px">内存占比</th><th style="width:160px">时间</th><th>SQL</th></tr>
      <tr><td>1</td><td>{query_id}</td><td>{username}</td><td>{pct}%</td><td>{start_time_beijing}</td><td class="sql-text">{query_text}</td></tr>
      <tr><td>2</td><td>{query_id}</td><td>{username}</td><td>{pct}%</td><td>{start_time_beijing}</td><td class="sql-text">{query_text}</td></tr>
      <tr><td>3</td><td>{query_id}</td><td>{username}</td><td>{pct}%</td><td>{start_time_beijing}</td><td class="sql-text">{query_text}</td></tr>
    </table>
  </div>

  <div class="section">
    <div class="section-title">内存贡献 Top3 数据库用户</div>
    <table>
      <tr><th style="width:40px">#</th><th>用户名</th><th style="width:260px">内存占比</th></tr>
      <tr><td>1</td><td>{user1}</td><td><span class="pct-bar" style="width:{bar1}px"></span><span class="pct-val">{pct1}%</span></td></tr>
      <tr><td>2</td><td>{user2}</td><td><span class="pct-bar" style="width:{bar2}px"></span><span class="pct-val">{pct2}%</span></td></tr>
      <tr><td>3</td><td>{user3}</td><td><span class="pct-bar" style="width:{bar3}px"></span><span class="pct-val">{pct3}%</span></td></tr>
    </table>
  </div>

</div>
</body>
</html>
```

## diagnosis_summary Fill Rules

- If all metrics are normal → Output `<div class="conclusion-item normal">诊断暂未发现异常</div>`
- Otherwise, output one `<div class="conclusion-item">` per anomaly, content format: `<anomaly_type>: <factual_description>`
- First line summarizes the cause of high memory in one sentence, must include node scope + instance type + memory type + cause type + user + operation (e.g., "All nodes DN instances, database user analyst_user executing single SQL causing high memory")
- Basic diagnostic information immediately follows the first line summary (one line): highest memory usage, memory distribution type (global high / single node / single instance / data skew), memory type (dynamic memory high / process memory high), memory_pool status
- Format: "基础诊断: 最高内存使用率 85%, 单节点内存高(节点间偏差45%), 动态内存高(动态内存使用率78%), work_mem使用率82%"
- If a specific SQL is identified, append a location sub-block after the anomaly item div:
  ```html
  <div class="conclusion-item"><anomaly_type>: <factual_description></div>
  <div class="locate-block">
    <div class="loc-row"><span class="loc-key">QueryID</span><span class="loc-val">{query_id}</span></div>
    <div class="loc-row"><span class="loc-key">用户名</span><span class="loc-val">{username}</span></div>
    <div class="loc-row"><span class="loc-key">启动时间</span><span class="loc-val">{start_time_beijing}</span></div>
    <div class="loc-row"><span class="loc-key">具体SQL</span><span class="loc-val">{query_preview} (max 1000 characters)</span></div>
  </div>
  ```
- Anomaly items can use tags for readability: System cause uses `<span class="tag tag-warn">系统</span>`, Customer-side cause uses `<span class="tag tag-danger">客户侧</span>`, Memory type uses `<span class="tag tag-info">动态内存</span>` or `<span class="tag tag-info">进程内存</span>`
- gaussdb process memory high is the result/manifestation of business SQL, merged into the corresponding root cause description, not listed as an independent root cause
- Multiple similar SQLs described as "N条同类xxx查询"
- Diagnosis time range must be appended at the end of conclusions, format: "诊断时间范围: 2026-05-20 09:40:00 ~ 2026-05-20 10:00:00"

**Top 3 Statements Fill Rules**:
- Data source: Top 3 statements from memory_diagnose_detail, sorted by mem_used descending
- Each row in memory_diagnose_detail active_sessions represents one query execution; treat each row independently when sorting for Top 3
- QueryID: From query_id field; multiple similar SQLs are comma-separated with count annotation (e.g., "73183494456652581等4条")
- Username: From userName field (database user)
- Memory Proportion: From mem_used field, calculate as percentage of total node memory consumption; keep 1 decimal place (e.g., 76.5%)
- Time: When duration_ms exists, it is ctime - duration_ms converted to Beijing time, column header shows "启动时间"; When duration_ms is absent, use ctime converted to Beijing time, column header shows "采集时间"
- SQL: From query field, display up to 1000 characters; truncate with "..." if exceeded
- gaussdb main process is not listed as an independent statement; its memory overhead is merged into the corresponding root cause description
- If no statement data (e.g., memory_diagnose_detail is empty), fill the table with "无法获取"

**Top 3 Users Fill Rules**:
- Data source: mem_used aggregated by userName from memory_diagnose_detail active_sessions
- The userName here is the **database user**, NOT the OS user. Do not use the username field from command_cpu_usage
- Only count database users with state=active
- Ratio = user's total mem_used / all users' total mem_used × 100%
- If fewer than 3 data points, list actual count
- pct-bar width calculation: `width = Math.round(ratio / max_ratio * 200)`, where max_ratio is the top user's ratio

**Multi-root-cause Handling**: When diagnosis results contain multiple independent root causes, each root cause occupies one item in the diagnosis_summary, with independent conclusion-item divs.

**addition.advice Fill Rules**:
- **Customer-side causes** (single SQL / multi-user concurrent / data skew): Suggest analyzing business SQL execution plans; if single SQL memory proportion too high, consider aborting the business SQL or executing during off-peak hours
- **System-side causes** (system SQL / memory leak / configuration unreasonable): Suggest contacting Huawei technical support
- **Mixed causes**: Include both types of suggestions above
- Do not provide overly detailed operation steps (e.g., specific kill commands, parameter modification values), do not provide dangerous operation suggestions
- advice content should be concise, 1-2 sentences

## Problem Node Memory Overview Table Fill Rules

- Only list nodes with memory exceeding threshold (i.e., diagnosed problematic nodes), do not list normal nodes
- If all nodes are anomalous (mem_scope=all_nodes), list all nodes
- If single node anomaly, only list that anomalous node
- Node name and IP from Step 2 host information (matched via host_id)
- Memory metrics from Step 1 MemStat data
- buffers_cached = buffers + cached

## General Fill Rules

- Cluster name prefers cluster_name; if empty, use cluster_id
- When node_name is empty, fill "集群级告警"
- gaussdb main process memory usage is merged into the corresponding root cause description
- Multiple similar SQLs are described as "N条同类xxx查询"
- All times must be in Beijing time
- SQL text exceeding 1000 characters is truncated with "..."
- Output is a complete HTML document that can be rendered directly in a browser
- `<` `>` `&` in SQL text must be escaped as `&lt;` `&gt;` `&amp;`
