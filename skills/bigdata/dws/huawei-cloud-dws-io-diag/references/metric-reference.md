# Metric Reference - DWS I/O Overload Diagnosis

## Key Fields per Metric

| Metric | Key Fields |
|--------|------------|
| IOStat | ctime, host_id, disk_name, io_data{util, await, r_await, w_await, r_s, w_s, read_iops, write_iops, rMB_s, wMB_s, read_throughput, write_throughput, avgrq_sz, avgqu_sz} → core I/O metrics |
| CpuStat | ctime, host_id, cpu_data{usr, sys, idle, iowait} → iowait > 30% indicates significant I/O pressure |
| cpu_io_diagnose_detail | Flat row structure: ctime, host_id, inst_name, username, cpu_rate, count, datname, io_read, io_write, query_id, query, duration_ms, state. Also contains io_stats: read_iops, write_iops, read_throughput, write_throughput |
| business_concurrency | ctime, concurrency_value, active_connections |
| business_query_monitor | ctime, query, query_id, username, duration_ms, host_id |
| business_thread_wait | ctime, wait_event, count, username, host_id → wait events (wait wal sync, WALWriteLock, etc.) |
| bussiness_conflict_lock | ctime, lock_type, blocker, waiter, username, host_id → lock conflicts |

## Query Differences per Step

| Step | metric_name | Paginated | Filtering | hcloud Command |
|------|-------------|-----------|-----------|----------------|
| Step 1 | IOStat | Yes (limit=200) | No | `hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<cid> --metric_name=IOStat --project_id=<pid> --from=<from_ts> --to=<to_ts> --offset=0 --limit=200` |
| Step 3 | CpuStat | Yes (limit=200) | No | `hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<cid> --metric_name=CpuStat --project_id=<pid> --from=<from_ts> --to=<to_ts> --offset=0 --limit=200` |
| Step 5a | business_concurrency | Yes (limit=200) | No | `hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<cid> --metric_name=business_concurrency --project_id=<pid> --from=<from_ts> --to=<to_ts> --offset=0 --limit=200` |
| Step 5b | cpu_io_diagnose_detail | Yes (limit=200, pagination required) | Filter by max_io_hosts | `hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<cid> --metric_name=cpu_io_diagnose_detail --project_id=<pid> --from=<from_ts> --to=<to_ts> --offset=0 --limit=200` |
| Step 5c | business_thread_wait | Yes (limit=200) | No | `hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<cid> --metric_name=business_thread_wait --project_id=<pid> --from=<from_ts> --to=<to_ts> --offset=0 --limit=200` |
| Step 5c | bussiness_conflict_lock | Yes (limit=200) | No | `hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<cid> --metric_name=bussiness_conflict_lock --project_id=<pid> --from=<from_ts> --to=<to_ts> --offset=0 --limit=200` |

## I/O Key Metric Thresholds

| Metric | Meaning | Threshold Judgment |
|--------|---------|-------------------|
| r/s, w/s | Read/Write IOPS | SSD upper limit 8000-20000/s; HDD sequential I/O upper limit 1000-2000/s, HDD random I/O upper limit 300-600/s (per RAID group) |
| rMB/s, wMB/s | Read/Write throughput | SSD upper limit 900-3500MB/s; HDD sequential I/O upper limit 250-800MB/s, HDD random I/O upper limit 130-240MB/s (per RAID group) |
| r_await, w_await | Average response time (ms) | Persistently > 100 indicates I/O bottleneck (occasional spikes are normal) |
| avgrq-sz | Average request size (KB) | Normal ~200; < 30 with high IOPS → highly suspect fragmented I/O |
| avgqu-sz | Average I/O queue depth | Persistently > 100 indicates severe I/O queue backlog, combined with await to judge I/O bottleneck |
| %util | Disk utilization | Only focus on whether persistently 99% or 100% |

## Three Major I/O Scenario Indicator Features

| Scenario | Features |
|----------|----------|
| **I/O Throughput Overload** | rMB/s+wMB/s reaching RAID group upper limit + util persistently 99%/100% + await persistently > 100 |
| **IOPS Overload** | r/s+w/s reaching RAID group upper limit + util persistently 99%/100% + await persistently > 100 |
| **I/O Anomaly** | IOPS and throughput far below minimum specification + await persistently > 100 + avgqu-sz persistently > 100 + util persistently 99%/100% |

## RAID Architecture Notes

- **System disks**: 2 disks in RAID1 (mirroring), specifications are already RAID group overall performance
- **Data disks**: 4-6 disks in RAID5 (parity), specifications are already RAID group overall performance
- **Key constraint**: iostat cannot precisely distinguish sequential I/O from random I/O ratio; each sdX device in iostat corresponds to one RAID group, thresholds are RAID group overall performance specifications, compare directly without multiplying by disk count
- **DWS data distribution is disk-based**: Data skew only causes single disk overload, not all disks overloaded simultaneously
