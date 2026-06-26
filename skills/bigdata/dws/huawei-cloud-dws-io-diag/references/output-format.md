# Output Format - DWS I/O Overload Diagnosis

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
  .header { background: linear-gradient(135deg, #165dff, #0fc6c2); color: #fff; padding: 24px 32px; }
  .header h1 { margin: 0; font-size: 22px; letter-spacing: 1px; }
  .header .subtitle { margin-top: 4px; font-size: 13px; opacity: 0.85; }
  .section { padding: 20px 32px; border-bottom: 1px solid #e5e6eb; }
  .section:last-child { border-bottom: none; }
  .section-title { font-size: 16px; font-weight: 600; color: #165dff; margin: 0 0 12px 0; padding-left: 10px; border-left: 3px solid #165dff; }
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
  .tag { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 12px; font-weight: 500; }
  .tag-warn { background: #fff7e8; color: #ff7d00; }
  .tag-danger { background: #ffece8; color: #cb2634; }
  .tag-info { background: #e8f3ff; color: #165dff; }
  .freq-help { display: inline-block; width: 16px; height: 16px; line-height: 16px; text-align: center; border-radius: 50%; background: #c9cdd4; color: #fff; font-size: 11px; font-weight: 700; cursor: pointer; margin-left: 4px; vertical-align: middle; position: relative; }
  .freq-help:hover { background: #86909c; }
  .freq-help .freq-tooltip { display: none; position: absolute; left: 50%; bottom: 24px; transform: translateX(-50%); background: #1d2129; color: #fff; font-size: 12px; font-weight: 400; padding: 8px 12px; border-radius: 4px; white-space: normal; width: 240px; z-index: 10; line-height: 1.5; }
  .freq-help .freq-tooltip::after { content: ''; position: absolute; top: 100%; left: 50%; transform: translateX(-50%); border: 5px solid transparent; border-top-color: #1d2129; }
  .freq-help:hover .freq-tooltip { display: block; }
</style>
</head>
<body>
<div class="report">

  <div class="header">
    <h1>DWS 集群 IO 诊断报告</h1>
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
    <div class="section-title">问题节点IO概览</div>
    <table>
      <tr><th>节点名称</th><th>节点IP</th><th>磁盘利用率</th><th>IO响应时间(ms)</th><th>读IOPS</th><th>写IOPS</th><th>读吞吐(MB/s)</th><th>写吞吐(MB/s)</th></tr>
      <tr><td>{node_name}</td><td>{node_ip}</td><td>{util}%</td><td>{await}</td><td>{read_iops}</td><td>{write_iops}</td><td>{read_throughput}</td><td>{write_throughput}</td></tr>
    </table>
  </div>

  <div class="section">
    <div class="section-title">诊断结论</div>
    {diagnosis_summary}
  </div>

  <div class="section">
    <div class="section-title">IO相关异常查询与排查信息</div>
    {io_investigation_content}
  </div>

  <div class="section">
    <div class="section-title">IO贡献Top3 SQL</div>
    {topn_sql_io_content}
  </div>

  <div class="section">
    <div class="section-title">IO贡献Top3 用户</div>
    {topn_user_io_content}
  </div>

</div>
</body>
</html>
```

## diagnosis_summary Fill Rules

- If all metrics are normal → Output `<div class="conclusion-item normal">诊断暂未发现异常</div><div class="conclusion-item normal">诊断时间范围: {from_time} ~ {to_time}</div>`
- Otherwise, output one `<div class="conclusion-item">` per anomaly, content format: `<anomaly_type>: <factual_description>`
- First line summarizes the cause of high I/O in one sentence, must include node scope + I/O scenario + I/O type + cause type + user + operation
- Basic diagnostic information immediately follows the first line summary (one line): highest disk utilization, highest await, I/O scenario determination, I/O type
- If a specific SQL is identified, append a location sub-block after the anomaly item div:
  ```html
  <div class="conclusion-item"><anomaly_type>: <factual_description></div>
  <div class="locate-block">
    <div class="loc-row"><span class="loc-key">SQL摘要</span><span class="loc-val">{specific_sql} (max 50 characters)</span></div>
    <div class="loc-row"><span class="loc-key">QueryID</span><span class="loc-val">{query_id}</span></div>
    <div class="loc-row"><span class="loc-key">用户名</span><span class="loc-val">{username}</span></div>
    <div class="loc-row"><span class="loc-key">启动时间</span><span class="loc-val">{start_time_beijing}</span></div>
  </div>
  ```
- Anomaly items can use tags for readability: System cause uses `<span class="tag tag-warn">系统</span>`, Customer-side cause uses `<span class="tag tag-danger">客户侧</span>`, I/O overload uses `<span class="tag tag-info">过载</span>`, I/O anomaly uses `<span class="tag tag-warn">异常</span>`
- gaussdb process I/O high is the result/manifestation of business SQL, merged into the corresponding root cause description, not listed as an independent root cause
- Multiple similar SQLs described as "N条同类xxx查询"
- Diagnosis time range must be appended at the end of conclusions, format: "诊断时间范围: 2026-05-20 09:40:00 ~ 2026-05-20 10:00:00"

## IO Related Anomalous Queries and Investigation Information Fill Rules

This section displays IO-related investigation directions or a reference note to the TopN sections below.

- **When io_data_available=true** (IO consumption data available, rare scenario):
  - This section displays: "详见下方IO贡献Top3模块" (TopN data is in the separate sections below)
  - TopN SQL and TopN User are rendered in their own dedicated sections (see below)
- **When io_data_available=false** (IO consumption data unavailable, common scenario, can only infer investigation directions from indirect characteristics):
  - Output text format content:
    ```
    【IO排查方向】（基于语句特征和等待事件推断，非IO消耗量化数据）:
      - 下盘特征: 检测到N条多表JOIN+排序/聚合SQL，伴随wait file write事件
      - 全表扫描特征: 检测到N条大表SELECT */COUNT查询
      - IO等待事件: wait wal sync N次、WALWriteLock N次
      - 高CPU活跃查询: 查询1摘要 (query_id, 用户名, cpu_rate: xx%)
    ```
  - These are possibility inferences, annotated as "investigation direction" rather than "IO anomalous queries"
  - HTML rendering:
    ```html
    <div style="padding:12px;background:#f7f8fa;border-radius:4px;font-size:13px;font-family:'Cascadia Code','Fira Code','Consolas',monospace;white-space:pre-wrap;">
【IO排查方向】（基于语句特征和等待事件推断，非IO消耗量化数据）:
  - 下盘特征: {spill_description}
  - 全表扫描特征: {full_scan_description}
  - IO等待事件: {io_wait_description}
  - 高CPU活跃查询: {high_cpu_queries_description}
    </div>
    ```
- gaussdb main process is not listed as an independent statement; its IO overhead is merged into the corresponding root cause description
- If no IO-related data at all, fill with "无法获取"
- **When no anomaly detected (io_scenario=normal)**: Display current active query reference information, annotated as "IO未发现异常，以下为当前活跃查询参考信息". Follow the same io_data_available=true/false rendering rules as the anomaly scenario, but replace "IO排查方向" with "IO参考信息" and annotate as reference rather than investigation direction

## IO Contribution Top3 SQL Section Fill Rules

This section is displayed when io_data_available=true; when io_data_available=false, render as HTML table sorted by CPU usage with annotation.

- **When io_data_available=true**: Render as HTML table:
  ```html
  <table>
    <tr><th>SQL摘要</th><th>QueryID</th><th>用户名</th><th>总io_read(MB)</th><th>总io_write(MB)</th><th>出现频次<span class="freq-help">?<span class="freq-tooltip">出现频次表示该SQL在诊断时段内被采集到的采样点数占总采样点数的比例。格式为N/M，其中N为该SQL出现的采样点数，M为诊断时段内总采样点数。频次越高说明该SQL执行越持久。</span></span></th><th>IO特征</th></tr>
    <tr><td class="sql-text">{query_preview_1}</td><td>{query_id_1}</td><td>{username_1}</td><td>{total_io_read_1}</td><td>{total_io_write_1}</td><td>{N_1}/{M}</td><td>{io_characteristic_1}</td></tr>
    <tr><td class="sql-text">{query_preview_2}</td><td>{query_id_2}</td><td>{username_2}</td><td>{total_io_read_2}</td><td>{total_io_write_2}</td><td>{N_2}/{M}</td><td>{io_characteristic_2}</td></tr>
  </table>
  ```
  - Where N is the number of sampling points this SQL appeared, M is the total sampling points in high IO time period
  - TopN SQL entries include IO characteristics (spill/full table scan/high IO wait etc. qualitative description)
  - Ruby user must not appear in TopN; its IO consumption is reflected in system-side root cause description
  - SQL preview max 50 characters, truncate with "..." if exceeded
- **When io_data_available=false**: Render as HTML table sorted by CPU usage, annotated as reference:
  ```html
  <div style="font-size:13px;color:#86909c;margin-bottom:8px;">IO消耗数据不可用，按CPU占用排序作为参考</div>
  <table>
    <tr><th>SQL摘要</th><th>QueryID</th><th>用户名</th><th>总CPU占用(%)</th><th>出现频次<span class="freq-help">?<span class="freq-tooltip">出现频次表示该SQL在诊断时段内被采集到的采样点数占总采样点数的比例。格式为N/M，其中N为该SQL出现的采样点数，M为诊断时段内总采样点数。频次越高说明该SQL执行越持久。</span></span></th><th>IO特征</th></tr>
    <tr><td class="sql-text">{query_preview_1}</td><td>{query_id_1}</td><td>{username_1}</td><td>{total_cpu_rate_1}</td><td>{N_1}/{M}</td><td>{io_characteristic_1}</td></tr>
    <tr><td class="sql-text">{query_preview_2}</td><td>{query_id_2}</td><td>{username_2}</td><td>{total_cpu_rate_2}</td><td>{N_2}/{M}</td><td>{io_characteristic_2}</td></tr>
  </table>
  ```
  - Where N is the number of sampling points this SQL appeared, M is the total sampling points in high IO time period
  - Ruby user must not appear in TopN; its IO consumption is reflected in system-side root cause description
  - SQL preview max 50 characters, truncate with "..." if exceeded
- **When no anomaly detected (io_scenario=normal) and io_data_available=true**: Render as HTML table using the same format as the anomaly scenario, but annotate as reference information rather than root cause evidence
- **When no anomaly detected (io_scenario=normal) and io_data_available=false**: Render as HTML table using the same io_data_available=false format as the anomaly scenario, annotated as reference information rather than root cause evidence

## IO Contribution Top3 User Section Fill Rules

This section is displayed when io_data_available=true; when io_data_available=false, render as HTML table sorted by CPU usage with annotation.

- **When io_data_available=true**: Render as HTML table:
  ```html
  <table>
    <tr><th>用户名</th><th>总io_read(MB)</th><th>总io_write(MB)</th><th>出现频次<span class="freq-help">?<span class="freq-tooltip">出现频次表示该用户在诊断时段内被采集到的采样点数占总采样点数的比例。格式为N/M，其中N为该用户出现的采样点数，M为诊断时段内总采样点数。频次越高说明该用户执行查询越持久。</span></span></th></tr>
    <tr><td>{username_1}</td><td>{total_io_read_1}</td><td>{total_io_write_1}</td><td>{N_1}/{M}</td></tr>
    <tr><td>{username_2}</td><td>{total_io_read_2}</td><td>{total_io_write_2}</td><td>{N_2}/{M}</td></tr>
  </table>
  ```
  - Where N is the number of sampling points this user appeared, M is the total sampling points in high IO time period
  - Ruby user must not appear in TopN; its IO consumption is reflected in system-side root cause description
- **When io_data_available=false**: Render as HTML table sorted by CPU usage, annotated as reference:
  ```html
  <div style="font-size:13px;color:#86909c;margin-bottom:8px;">IO消耗数据不可用，按CPU占用排序作为参考</div>
  <table>
    <tr><th>用户名</th><th>总CPU占用(%)</th><th>出现频次<span class="freq-help">?<span class="freq-tooltip">出现频次表示该用户在诊断时段内被采集到的采样点数占总采样点数的比例。格式为N/M，其中N为该用户出现的采样点数，M为诊断时段内总采样点数。频次越高说明该用户执行查询越持久。</span></span></th></tr>
    <tr><td>{username_1}</td><td>{total_cpu_rate_1}</td><td>{N_1}/{M}</td></tr>
    <tr><td>{username_2}</td><td>{total_cpu_rate_2}</td><td>{N_2}/{M}</td></tr>
  </table>
  ```
  - Where N is the number of sampling points this user appeared, M is the total sampling points in high IO time period
  - Ruby user must not appear in TopN; its IO consumption is reflected in system-side root cause description
- **When no anomaly detected (io_scenario=normal) and io_data_available=true**: Render as HTML table using the same format as the anomaly scenario, but annotate as reference information rather than root cause evidence
- **When no anomaly detected (io_scenario=normal) and io_data_available=false**: Render as HTML table using the same io_data_available=false format as the anomaly scenario, annotated as reference information rather than root cause evidence

## diagnosis_json Output Structure

`{{diagnosis_json}}` data structure is as follows (example data for format reference only, using IO throughput overload scenario with io_data_available=true):
```json
{
  "show_type": "recommended_root_cause",
  "data": {
    "data": [
      {
        "id": "根因1",
        "content": "所有节点DN实例，IO吞吐过载(写IO为主)，数据库用户analyst_user执行批量导入导致IO高\n基础诊断: 最高util 99%，最高await 350ms，IO吞吐过载(写IO为主)，所有节点所有盘IO高\n- IO吞吐过载(写IO为主): 写吞吐合计2800MB/s接近RAID组上限，gaussdb DN主进程IO写占用高\n  高频查询1 → 15条同类COPY导入查询, 用户名: analyst_user, 采集时间: 2026-06-10 13:20:00, 具体SQL: COPY large_table FROM '/data/import/file.csv' WITH (FORMAT csv)\n- 全表扫描导致IO高: 检测到3条全表扫描查询\n  QueryID: 73183494456652581\n  用户名: analyst_user\n  采集时间: 2026-06-10 13:18:00\n  具体SQL: SELECT * FROM large_table WHERE condition...\n\n【IO贡献Top3 SQL】（高IO时段4个采样点聚合）:\n  - COPY large_table FROM... (73183494456652580, analyst_user, 总io_read: 48MB, 总io_write: 3424MB, 出现4/4次, 批量导入)\n  - SELECT * FROM large_table... (73183494456652581, analyst_user, 总io_read: 1692MB, 总io_write: 0MB, 出现3/4次, 全表扫描)\n  - INSERT INTO report_table... (73183494456652582, analyst_user, 总io_read: 15MB, 总io_write: 936MB, 出现2/4次, 写IO密集)\n【IO贡献Top3 用户】（高IO时段4个采样点聚合）:\n  - analyst_user (总io_read: 1755MB, 总io_write: 4360MB, 出现4/4次)\n  - report_user (总io_read: 85MB, 总io_write: 120MB, 出现2/4次)\n  - db_admin (总io_read: 30MB, 总io_write: 45MB, 出现1/4次)\n\n诊断时间范围: 2026-06-10 13:15:43 ~ 2026-06-10 13:35:43",
        "addition": {
          "advice": "建议分析业务SQL执行计划，优化高IO占用的查询；如需紧急恢复，可考虑中止高IO占用的业务SQL或错峰执行"
        }
      }
    ]
  }
}
```

**content Field Format Rules**:
- **When io_data_available=true**: Include 【IO贡献Top3 SQL】 and 【IO贡献Top3 用户】 sections with aggregated IO data. TopN SQL entries include IO characteristics (spill/full table scan/high IO wait etc.), no separate 【IO相关异常查询】 section to avoid duplication
- **When io_data_available=false**: Include 【IO排查方向】 section instead of TopN, listing: spill characteristics, full table scan characteristics, IO wait events, high CPU active queries. Annotated as "基于语句特征和等待事件推断，非IO消耗量化数据"
- **System-side (io_data_available=false example)**: content includes system user Ruby's autovacuum task description + 【IO排查方向】 section; addition.advice = `"建议联系华为技术支持人员"`
- **No anomaly detected (io_data_available=false)**: content = `"诊断暂未发现异常"`, addition.advice = `"暂无"`
- **No anomaly detected (io_data_available=true)**: content includes 【IO贡献Top3 SQL】 and 【IO贡献Top3 用户】 reference information with aggregated IO data, annotated as reference rather than root cause evidence, addition.advice = `"暂无"`
- **Ruby User Constraint**: Ruby user must not appear in IO Contribution TopN; its IO consumption is reflected in system-side root cause description

## Problem Node I/O Overview Table Fill Rules

- Only list nodes with I/O exceeding threshold (i.e., diagnosed problematic nodes), do not list normal nodes
- If all nodes are anomalous, list all nodes
- If single node anomaly, only list that anomalous node
- **When no anomaly detected (io_scenario=normal)**: Output only the table header row, no data rows (since no nodes exceed thresholds)
- Node name and IP from Step 2 host information (matched via host_id)
- I/O metrics from Step 1 IOStat data

## General Fill Rules

- Cluster name prefers cluster_name; if empty, use cluster_id
- region_id prefers the value provided by the user; if not provided, read from MCP Server config file (conf/dws_config.yaml) region_id field
- When node_name is empty, fill "集群级告警"
- gaussdb main process I/O usage is merged into the corresponding root cause description
- Multiple similar SQLs are described as "N条同类xxx查询"
- All times must be in Beijing time
- Statement summary exceeding 50 characters is truncated with "..."
- Output is a complete HTML document that can be rendered directly in a browser
- `<` `>` `&` in SQL text must be escaped as `&lt;` `&gt;` `&amp;`
