# diagnosis_json Output Format Reference

**Note**: Strictly follow the format rules below. Do not modify the structure, do not omit any part.

## diagnosis_json Data Structure

`{{diagnosis_json}}` data structure is as follows (example data is for format reference only, using IO throughput overload scenario with io_data_available=true):
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

## content Field Format Rules

- **When io_data_available=true** (IO consumption data available, rare scenario):
  ```
  【IO贡献Top3 SQL】（高IO时段N个采样点聚合）:
    - 查询1摘要 (query_id, 用户名, 总io_read: xxx, 总io_write: xxx, 出现N/M次, IO特征如:下盘/全表扫描/高IO等待)
    - 查询2摘要 (query_id, 用户名, 总io_read: xxx, 总io_write: xxx, 出现N/M次, IO特征)
  【IO贡献Top3 用户】（高IO时段N个采样点聚合）:
    - 用户1 (总io_read: xxx, 总io_write: xxx, 出现N/M次)
    - 用户2 (总io_read: xxx, 总io_write: xxx, 出现N/M次)
  ```
  Where N is the number of sampling points this SQL/user appeared, M is the total sampling points in high IO time period. TopN SQL entries include IO characteristics (spill/full table scan/high IO wait etc. qualitative description), no separate 【IO Related Anomalous Queries】 section to avoid same SQL appearing twice

- **When io_data_available=false** (IO consumption data unavailable, common scenario, sort by CPU usage as reference):
  ```
  【IO贡献Top3 SQL】（高IO时段N个采样点聚合，IO消耗数据不可用，按CPU占用排序作为参考）:
    - 查询1摘要 (query_id, 用户名, 总CPU占用: xxx%, 出现N/M次, IO特征如:下盘/全表扫描/高IO等待)
    - 查询2摘要 (query_id, 用户名, 总CPU占用: xxx%, 出现N/M次, IO特征)
  【IO贡献Top3 用户】（高IO时段N个采样点聚合，IO消耗数据不可用，按CPU占用排序作为参考）:
    - 用户1 (总CPU占用: xxx%, 出现N/M次)
    - 用户2 (总CPU占用: xxx%, 出现N/M次)
  【IO排查方向】（基于语句特征和等待事件推断，非IO消耗量化数据）:
    - 下盘特征: 检测到N条多表JOIN+排序/聚合SQL，伴随wait file write事件
    - 全表扫描特征: 检测到N条大表SELECT */COUNT查询
    - IO等待事件: wait wal sync N次、WALWriteLock N次
  ```

- **System-side (io_data_available=false example)**: `单节点DN实例，IO异常，系统用户Ruby执行autovacuum任务导致IO高\n基础诊断: 最高util 99%，最高await 500ms，IO异常(读写均低但await极高)\n- IO异常(硬件层): 所有磁盘吞吐远低于规格但await持续>100ms，疑似RAID卡读写策略降级或RAID卡CC校验\n- 系统内部任务占用IO高（系统侧）: 系统用户Ruby执行自动VACUUM任务\n  QueryID: q-456-789\n  用户名: Ruby\n  采集时间: 2026-05-20 09:30:00\n  具体SQL: VACUUM ANALYZE large_table\n\n【IO贡献Top3 SQL】（高IO时段2个采样点聚合，IO消耗数据不可用，按CPU占用排序作为参考）:\n  - VACUUM ANALYZE large_table (q-456-789, Ruby, 总CPU占用: 45%, 出现2/2次, 系统内部任务)\n【IO贡献Top3 用户】（高IO时段2个采样点聚合，IO消耗数据不可用，按CPU占用排序作为参考）:\n  - Ruby (总CPU占用: 45%, 出现2/2次)\n【IO排查方向】（基于语句特征和等待事件推断，非IO消耗量化数据）:\n  - 下盘特征: 未检测到\n  - 全表扫描特征: 未检测到\n  - IO等待事件: wait wal sync 15次\n\n诊断时间范围: 2026-05-20 09:40:00 ~ 2026-05-20 10:00:00`, addition.advice = `"建议联系华为技术支持人员"`

- **No anomaly detected (io_data_available=false)**: content includes 【IO贡献Top3 SQL】 and 【IO贡献Top3 用户】 reference information sorted by CPU usage, annotated as "IO消耗数据不可用，按CPU占用排序作为参考", plus 【IO参考信息】 section. Format: `"诊断暂未发现异常\n\n【IO贡献Top3 SQL】（高IO时段N个采样点聚合，IO消耗数据不可用，按CPU占用排序作为参考）:\n  - 查询1摘要 (query_id, 用户名, 总CPU占用: xxx%, 出现N/M次, IO特征)\n  - 查询2摘要 (query_id, 用户名, 总CPU占用: xxx%, 出现N/M次, IO特征)\n【IO贡献Top3 用户】（高IO时段N个采样点聚合，IO消耗数据不可用，按CPU占用排序作为参考）:\n  - 用户1 (总CPU占用: xxx%, 出现N/M次)\n  - 用户2 (总CPU占用: xxx%, 出现N/M次)\n\n【IO参考信息】（IO未发现异常，以下为当前活跃查询参考信息）:\n  - 下盘特征: {spill_description}\n  - 全表扫描特征: {full_scan_description}\n  - IO等待事件: {io_wait_description}\n\n诊断时间范围: {from_time} ~ {to_time}"`, addition.advice = `"暂无"`
- **No anomaly detected (io_data_available=true)**: content includes 【IO贡献Top3 SQL】 and 【IO贡献Top3 用户】 reference information with aggregated IO data, annotated as reference rather than root cause evidence, addition.advice = `"暂无"`

## Ruby User Constraint

Ruby user must not appear in IO Contribution TopN; its IO consumption is reflected in system-side root cause description (e.g., "System user Ruby's autovacuum task causing high IO").
