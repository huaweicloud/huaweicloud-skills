# DWS I/O Diagnosis - Scenario Routing and Full Investigation Direction Reference

This file is a detailed reference for Step 6 (Analyze Diagnosis Results), containing the scenario routing table, root cause descriptions, and output examples.

## Scenario Routing and Full Investigation Directions

Based on Step 4's `io_scenario` and `phenomenon_distribution`, route to the corresponding scenario and execute full investigation:

### Scenario 1: I/O Throughput Overload

**Common Investigation Methods**:

Read I/O throughput overload:
1. Is it a non-balanced node (determined by comparing IOStat across nodes)
2. Check active statements, guess suspicious statements based on execution time and statement characteristics (cpu_io_diagnose_detail + business_query_monitor)
3. Confirm table characteristics (infer data skew from IOStat inter-node deviation, infer dirty pages/small CU bloat from active statement characteristics)

Write I/O throughput overload:
1. Is it a non-balanced node (determined by comparing IOStat across nodes)
2. Investigate whether there are spill files (infer spill operations from abnormally high write_throughput in cpu_io_diagnose_detail io_stats)
3. Check active statements to guess suspicious statements (cpu_io_diagnose_detail + business_query_monitor)
4. Confirm table characteristics (infer data skew from IOStat inter-node deviation, infer dirty pages/small CU bloat from active statement characteristics)

**Sub-scenario Routing**:

| Phenomenon Distribution | Investigation Direction Count | Investigation Direction List |
|-------------------------|-------------------------------|------------------------------|
| Single node + single disk (primary-standby balanced) | Read I/O 4 / Write I/O 5 | Read I/O: 1.Is it a non-balanced node → 2.Check active statements → 3.Confirm table characteristics (infer skew/dirty pages/small CU from inter-node deviation) → 4.Combine wait events for auxiliary judgment; Write I/O: 1.Is it a non-balanced node → 2.Investigate spill files (infer from write_throughput) → 3.Check active statements → 4.Confirm table characteristics (infer skew/dirty pages/small CU from inter-node deviation) → 5.Combine wait events for auxiliary judgment |
| Single node + all disks (overload type) | Possibility A 4 / Possibility B Read I/O 3 or Write I/O 4 | Possibility A (priority): 1.RAID card read-write strategy → 2.RAID card CC verification → 3.RAID card failure → 4.I/O scheduler strategy; Possibility B (secondary): Execute read I/O / write I/O common investigation |
| Multiple nodes / all nodes + all DN data disks | Read I/O 4 / Write I/O 4 | Read I/O: 1.Is it a non-balanced node → 2.Check active statements → 3.Confirm table characteristics (infer large table/dirty pages/small CU from inter-node deviation) → 4.Combine wait events for auxiliary judgment; Write I/O: 1.Is it a non-balanced node → 2.Investigate spill files (infer from write_throughput) → 3.Check active statements → 4.Combine wait events for auxiliary judgment |
| System disk | 2 | 1.pg_log log investigation → 2.pg_audit audit log investigation |

### Scenario 2: IOPS Overload

**Common Investigation Methods**:

Read I/O IOPS overload:
1. Is it a non-balanced node (determined by comparing IOStat across nodes)
2. Investigate fragmented I/O issues (avgrq_sz < 30 strongly suggests fragmented I/O, must pay attention)
3. Check active statements, guess suspicious statements based on execution time and statement characteristics (cpu_io_diagnose_detail + business_query_monitor)
4. Confirm table characteristics (infer data skew from IOStat inter-node deviation, infer dirty pages/small CU bloat from active statement characteristics)

Write I/O IOPS overload:
1. Is it a non-balanced node (determined by comparing IOStat across nodes)
2. Investigate whether there are spill files (infer spill operations from abnormally high write_throughput in cpu_io_diagnose_detail io_stats)
3. Check active statements to guess suspicious statements (cpu_io_diagnose_detail + business_query_monitor)
4. Confirm table characteristics (infer data skew from IOStat inter-node deviation, infer dirty pages/small CU bloat from active statement characteristics)
5. Combine wait events for auxiliary judgment (WALWriteLock etc. in bussiness_conflict_lock)

**Sub-scenario Routing**:

| Phenomenon Distribution | Investigation Direction Count | Investigation Direction List |
|-------------------------|-------------------------------|------------------------------|
| Single node + single disk (primary-standby balanced) | Read I/O 4 / Write I/O 5 | Read I/O: 1.Is it a non-balanced node → 2.Fragmented I/O investigation (must check when avgrq_sz<30) → 3.Check active statements → 4.Confirm table characteristics (infer skew/dirty pages/small CU from inter-node deviation); Write I/O: 1.Is it a non-balanced node → 2.Investigate spill files (infer from write_throughput) → 3.Check active statements → 4.Confirm table characteristics (infer skew/dirty pages/small CU from inter-node deviation) → 5.Combine wait events for auxiliary judgment |
| Single node + all disks (overload type) | Possibility A 4 / Possibility B Read I/O 4 or Write I/O 4 | Possibility A (priority): 1.RAID card read-write strategy → 2.RAID card CC verification → 3.RAID card failure → 4.I/O scheduler strategy; Possibility B (secondary): Execute read I/O / write I/O common investigation |
| Multiple nodes / all nodes + all DN data disks | Read I/O 4 / Write I/O 4 | Read I/O: 1.Is it a non-balanced node → 2.Fragmented I/O investigation (must check when avgrq_sz<30) → 3.Check active statements → 4.Confirm table characteristics (infer large table/dirty pages/small CU from inter-node deviation); Write I/O: 1.Is it a non-balanced node → 2.Investigate spill files (infer from write_throughput) → 3.Check active statements → 4.Combine wait events for auxiliary judgment |
| System disk | 2 | 1.pg_log log investigation → 2.pg_audit audit log investigation |

### Scenario 3: I/O Anomaly

| Phenomenon Distribution | Investigation Direction Count | Investigation Direction List |
|-------------------------|-------------------------------|------------------------------|
| Single node + single disk | 5 | 1.Slow disk within RAID → 2.RAID rebuild → 3.RAID card CC/PR verification → 4.RAID card read-write strategy → 5.I/O scheduler strategy |
| Single node + all disks | 4 | 1.RAID card failure → 2.RAID card read-write strategy → 3.I/O scheduler strategy → 4.RAID card CC/PR verification |
| Multiple nodes / all nodes + all disks | 3 | 1.RAID card read-write strategy → 2.I/O scheduler strategy → 3.Manufacturer hard disk power-on > 65535h performance degradation |

Note: I/O anomaly scenario does not depend on active statement investigation, as the bottleneck is at the hardware layer rather than the statement layer; does not include data skew.

### Scenario 4: Dual Overload (Throughput + IOPS both exceed maximum specifications)

Must include investigation directions from both I/O throughput overload and IOPS overload lists, but duplicate directions are merged. First list the directions for I/O throughput overload corresponding sub-scenario, then list the directions for IOPS overload corresponding sub-scenario; identical investigation directions are merged into one (annotated as belonging to both scenarios).

### Gray Zone (Cannot Definitively Determine)

Must simultaneously output two complete sets of investigation directions: [Possibility A: I/O Overload] and [Possibility B: I/O Anomaly]. The two sets are numbered independently and cannot be merged. I/O anomaly directions are expanded as: RAID card read-write strategy, RAID card CC verification, I/O scheduler strategy, RAID card failure.

## Statement Characteristics Reference Table (Auxiliary Active Statement Guessing)

| I/O Type | Statement Characteristics | Table Characteristics (Auxiliary Judgment) |
|----------|--------------------------|---------------------------------------------|
| Read I/O | SELECT or query-related statements (CREATE AS SELECT, INSERT INTO SELECT, etc.) | Data skew, high dirty page rate, column-store small CU bloat |
| Write I/O | ALTER TABLE MODIFY COLUMN, INSERT, COPY, SELECT spill, autovacuum statements, topsql-related queries | Data skew, high dirty page rate, column-store small CU bloat |
| CN disk read I/O | SELECT system catalog, non-pushdown statements | System catalog most suspicious |
| CN disk write I/O | CN spill | System catalog most suspicious |

## Customer-Side Causes (User is not omm or Ruby)

1. **Full Table Scan Causing High I/O**
   - Characteristics: cpu_io_diagnose_detail contains large table SELECT *, COUNT, MAX and other full table scan statements; business_query_monitor shows long execution time
   - Phenomenon distribution: Without skew, all nodes all disks I/O high; with skew, single disk I/O high
   - Suggestion: Reduce full table scan frequency, change row-store tables to column-store, add indexes, run ANALYZE promptly

2. **Spill Operations Causing High I/O**
   - Characteristics: cpu_io_diagnose_detail io_stats shows high write I/O (abnormally high write_throughput); active statements contain multi-table JOIN or sort operations generating large temporary files
   - Phenomenon distribution: May cause all nodes I/O high; if plan is skewed, may also cause individual disk I/O high
   - I/O type: Write I/O
   - Suggestion: Optimize query plans to reduce spill, split large JOINs, adjust work_mem parameter

3. **Data Skew Causing High I/O**
   - Characteristics: IOStat shows single node util and await significantly higher than other nodes (deviation > 20%); cpu_io_diagnose_detail shows query volume on that node far exceeds other nodes
   - Phenomenon distribution: Single disk I/O high or single node all disks I/O high
   - Suggestion: Modify table distribution column to make data distribution even

4. **Index-Bearing Import Causing High I/O**
   - Characteristics: High concurrency INSERT/COPY operations, index count > 3; IOStat shows high write IOPS; bussiness_conflict_lock may contain WALWriteLock
   - Phenomenon distribution: Generally all nodes all disks IOPS high
   - I/O type: Write IOPS
   - Suggestion: Drop indexes before import, control index count (recommended within 3), batch import

5. **Data Bloat / Dirty Pages Causing High I/O**
   - Characteristics: IOStat shows high read I/O but small effective data volume; active statements contain large amounts of UPDATE/DELETE operations without timely VACUUM
   - Phenomenon distribution: Generally all nodes all disks I/O high
   - Suggestion: Regular VACUUM FULL (during off-peak hours), change column-store tables to batch import, change frequently small-batch imported tables to row-store

6. **Small CU Bloat Causing High IOPS**
   - Characteristics: IOStat shows high read IOPS and small avgrq_sz; active statements involve column-store table scans; column-store tables with frequent small-batch imports causing small CU bloat
   - Phenomenon distribution: Generally all nodes all disks I/O high
   - Suggestion: Change column-store tables to batch import, regular VACUUM FULL, change frequently small-batch imported tables to row-store

7. **Large-Scale Import Operations Causing High I/O**
   - Characteristics: business_query_monitor shows COPY or INSERT INTO statements executing; IOStat shows high write throughput
   - Phenomenon distribution: Without skew, all nodes all disks I/O high; with skew, single disk I/O high
   - I/O type: Write I/O
   - Suggestion: Reduce import concurrency, batch import, avoid index-bearing import

8. **ALTER Modifying Column Type Triggering Rewrite**
   - Characteristics: business_query_monitor shows ALTER TABLE ... MODIFY statement executing; row-store table column type modification triggers rewrite rewriting pages
   - Phenomenon distribution: Without skew, all nodes all disks I/O high; with skew, single disk I/O high
   - I/O type: Write I/O
   - Suggestion: Avoid executing ALTER operations during business peak hours; for large table column type changes, consider rebuilding the table instead

9. **Subplan (Target Column Contains Subquery)**
   - Characteristics: cpu_io_diagnose_detail shows query statement target column contains subquery; plan contains subplan
   - Phenomenon distribution: Without skew, all nodes all disks I/O high; with skew, single disk I/O high
   - I/O type: Read I/O
   - Suggestion: Optimize SQL to avoid subqueries, rewrite as JOIN

## System Causes (User is omm or Ruby)

1. **autovacuum Consuming High I/O**
   - Characteristics: cpu_io_diagnose_detail detects autovacuum process; IOStat shows mixed read-write I/O; business_thread_wait may contain autovacuum-related waits
   - Phenomenon distribution: May cause all nodes all disks I/O high, or individual disk I/O high
   - I/O type: Mixed read-write I/O
   - Suggestion: Reduce autovacuum_max_workers, increase autovacuum_vacuum_cost_delay, evaluate disabling autovacuum

2. **topsql Consuming High I/O**
   - Characteristics: business_query_monitor shows system internal queries on PGXC_WLM_SESSION_INFO/HISTORY and other system catalog tables
   - Phenomenon distribution: May cause all nodes all disks I/O high, or individual disk I/O high
   - I/O type: Read I/O
   - Suggestion: Kill the corresponding query as emergency response

3. **pg_log/pg_audit Log Writing to System Disk**
   - Characteristics: System disk I/O high; abnormal log generation speed
   - Phenomenon distribution: Single node or all nodes system disk I/O high
   - Suggestion: Disable DN audit log parameters, reduce audit types, analyze whether logs are repeatedly printed

4. **XLOG Surge**
   - Characteristics: bussiness_conflict_lock contains large amounts of wait wal sync and WALWriteLock waits; primary-standby synchronization slow
   - Usually triggered by index-bearing import, row-store large table first query triggering FPW, etc.
   - Suggestion: Check for large transactions, control index count

## Output Examples

### Example 1: Full Table Scan (Customer-Side, I/O Throughput Overload)

```
[I/O Scenario Determination]: I/O Throughput Overload
[Phenomenon Distribution]: Multiple nodes / all nodes + all DN data disks
[I/O Type]: Read I/O
- Full table scan causing high I/O: Detected 3 full table scan statements, maximum execution time 43s, suggest reducing scan frequency
- Cluster I/O load imbalanced: Inter-node I/O deviation is 35%, possible data skew
```

### Example 2: Spill Operations (Customer-Side, I/O Throughput Overload)

```
[I/O Scenario Determination]: I/O Throughput Overload
[Phenomenon Distribution]: Multiple nodes / all nodes + all DN data disks
[I/O Type]: Write I/O
- Spill operations causing high I/O: cpu_io_diagnose_detail shows abnormally high write_throughput, active statements contain multi-table JOIN, write I/O dominant, suggest optimizing query plan
Located SQL: SELECT a.*, b.* FROM large_table1 a LEFT JOIN large_table2 b ON...
QueryID: q-789-012
Username: analyst_user
Start Time: 2026-05-20 10:05:00
Specific SQL: SELECT a.*, b.* FROM large_table1 a LEFT JOIN large_table2 b ON a.id = b.id...
```

### Example 3: I/O Anomaly (Single Node + All Disks)

```
[I/O Scenario Determination]: I/O Anomaly
[Phenomenon Distribution]: Single node + all disks
[I/O Type]: Mixed I/O
- RAID card failure: Single node all disks IOPS and throughput far below specifications, await persistently high, prioritize suspicion of RAID card failure or strategy degradation
- RAID card read-write strategy: Suggest checking whether RAID card read-write strategy has degraded from Write Back to Write Through
- I/O scheduler strategy: Suggest checking I/O scheduler strategy configuration
- RAID card CC/PR verification: More common on Saturday/Sunday/Monday, suggest confirming whether CC verification is currently running
```

### Example 4: Data Skew + Dirty Pages (Customer-Side)

```
[I/O Scenario Determination]: I/O Throughput Overload
[Phenomenon Distribution]: Single node + single disk
[I/O Type]: Read I/O
- Data skew causing high I/O: IOStat detected single node util reaching 95% while other nodes average 30%, deviation 65%, suggest modifying table distribution column
- Data bloat causing high I/O: Detected large amounts of UPDATE/DELETE operations without timely VACUUM, high read I/O but small effective data volume, suggest regular VACUUM FULL
```

### Example 5: autovacuum + XLOG (System-Side)

```
[I/O Scenario Determination]: IOPS Overload
[Phenomenon Distribution]: Multiple nodes / all nodes + all DN data disks
[I/O Type]: Mixed read-write I/O
- autovacuum consuming high I/O (system-side): Detected autovacuum process running simultaneously on 3 nodes, I/O wait rate reaching 55%
- XLOG surge: bussiness_conflict_lock detected large amounts of WALWriteLock waits, primary-standby synchronization slow
```

### Example 5b: I/O Anomaly - System-Side with io_data_available=false

```
[I/O Scenario Determination]: I/O Anomaly
[Phenomenon Distribution]: Single node + all disks
[I/O Type]: Mixed I/O
- I/O Anomaly (hardware layer): All disks throughput far below specifications but await persistently > 100ms, suspected RAID card read-write strategy degradation or RAID card CC verification
- System internal tasks consuming high I/O (system-side): System user Ruby executing autovacuum task
  QueryID: q-456-789
  Username: Ruby
  Collection Time: 2026-05-20 09:30:00
  Specific SQL: VACUUM ANALYZE large_table

【IO排查方向】（基于语句特征和等待事件推断，非IO消耗量化数据）:
  - 下盘特征: 未检测到
  - 全表扫描特征: 未检测到
  - IO等待事件: wait wal sync 15次
  - 高CPU活跃查询: VACUUM ANALYZE large_table (q-456-789, Ruby, cpu_rate: 45%)
```

### Example 6: Index-Bearing Import (Customer-Side)

```
[I/O Scenario Determination]: IOPS Overload
[Phenomenon Distribution]: Multiple nodes / all nodes + all DN data disks
[I/O Type]: Write I/O
- Index-bearing import causing high I/O: Write IOPS reaching 8000/s, bussiness_conflict_lock contains WALWriteLock waits, suggest dropping indexes before import
```

### Example 6b: I/O Throughput Overload with io_data_available=true (Customer-Side)

```
[I/O Scenario Determination]: I/O Throughput Overload
[Phenomenon Distribution]: Multiple nodes / all nodes + all DN data disks
[I/O Type]: Write I/O
- I/O throughput overload (write I/O dominant): Write throughput total 2800MB/s approaching RAID group upper limit, gaussdb DN main process IO write usage high
  High-frequency query 1 → 15 similar COPY import queries, Username: analyst_user, Collection Time: 2026-06-10 13:20:00, Specific SQL: COPY large_table FROM '/data/import/file.csv' WITH (FORMAT csv)
- Full table scan causing high I/O: Detected 3 full table scan queries
  QueryID: 73183494456652581
  Username: analyst_user
  Collection Time: 2026-06-10 13:18:00
  Specific SQL: SELECT * FROM large_table WHERE condition...

【IO贡献Top3 SQL】（高IO时段4个采样点聚合）:
  - COPY large_table FROM... (73183494456652580, analyst_user, 总io_read: 48MB, 总io_write: 3424MB, 出现4/4次, 批量导入)
  - SELECT * FROM large_table... (73183494456652581, analyst_user, 总io_read: 1692MB, 总io_write: 0MB, 出现3/4次, 全表扫描)
  - INSERT INTO report_table... (73183494456652582, analyst_user, 总io_read: 15MB, 总io_write: 936MB, 出现2/4次, 写IO密集)
【IO贡献Top3 用户】（高IO时段4个采样点聚合）:
  - analyst_user (总io_read: 1755MB, 总io_write: 4360MB, 出现4/4次)
  - report_user (总io_read: 85MB, 总io_write: 120MB, 出现2/4次)
  - db_admin (总io_read: 30MB, 总io_write: 45MB, 出现1/4次)
```

### Example 7: No Anomaly Detected

```
No anomaly detected in diagnosis
```
