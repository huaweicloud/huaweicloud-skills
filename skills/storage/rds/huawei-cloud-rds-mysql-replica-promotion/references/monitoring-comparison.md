# Monitoring Comparison for Single-to-HA Conversion (RDS for MySQL)

> This reference supports the SKILL workflow monitoring steps: the pre-conversion baseline (Step 7) and the post-conversion comparison (Step 9). It documents the behavior of `scripts/rds_monitor.py` and the verified CES facts behind the comparison criteria.

## 1. Purpose

The monitoring comparison captures a CES metrics snapshot before conversion (baseline) and after conversion, then compares them to judge whether the converted instance is stable, following the criteria of SOP v3 section 7.3.

## 2. Script Behavior

Run the script with the default 300-second window:

```bash
python3 scripts/rds_monitor.py \
  --region <region> \
  --instance-id <iid> \
  --output rds_monitor_baseline.json
```

- Default window: `to=now`, `from=now-300000` (300 seconds, covering one full 5-minute CES collection cycle); `--period` defaults to 300 (5-minute aggregation)
- Metrics reported: `cpu_util`, `mem_util`, `disk_util`, `iops`, `connections.usage_percent`, `replication_delay` (the last one null for single instances)
- The value of each metric is the latest datapoint (`timestamp`-max) in the window; the unit is read from the response (`metrics[].unit`), so the actual unit is always reported
- Batch query uses `CES BatchListMetricData` (POST); if the whole batch fails the script degrades to per-metric `ShowMetricData`; if the batch succeeds but an individual metric is missing, only that metric is re-queried individually
- The dimension is `rds_cluster_id,<instance_id>` with a literal comma (hcloud handles URL encoding)

## 3. Verified CES Facts

- CES collection granularity is **5 minutes**: a 60-second window returns no data for CPU/memory/disk/IOPS/connections, while a 300-second window reliably returns 1-2 datapoints. This is why the default window is 300 seconds.
- Metric names (verified against `CES ListMetrics`): `rds001_cpu_util` (%), `rds002_mem_util` (%), `rds039_disk_util` (%), `rds003_iops` (Count), `rds072_conn_usage` (%) and `rds073_replication_delay`.
- `rds073_replication_delay` unit is `Second` (not milliseconds), so "delay is 0 or near 0" is judged in seconds.
- Connection-related metrics available in CES include `rds006_conn_count` (absolute count), `rds007_conn_active_count`, `rds072_conn_usage` (usage percentage), `rds_conn_active_usage` and `rds_aborted_connects`. The script uses `rds072_conn_usage`; absolute counts are out of scope.
- A 300-second window snapshot is stable across runs (verified: two runs 60 s apart gave near-identical values; replication delay stayed 0).

## 4. Comparison Criteria (SOP v3 section 7.3)

| Metric | Criterion |
| --- | --- |
| CPU utilization | returned to a normal level after conversion |
| Memory utilization | within the normal range |
| Disk space utilization | within the normal range |
| IOPS | within the normal range |
| Database connection count | roughly unchanged compared with before conversion |
| Replication delay | 0 or near 0 (unit: seconds) |

The SKILL presents the before/after values per metric and the pass status per criterion. A metric missing from either snapshot is recorded truthfully as "no data"; no comparison conclusion is fabricated for it. The SKILL does not hard-code absolute thresholds; the Agent may present typical reference ranges when explaining "normal".
