# Metric Reference - DWS Memory High Diagnosis

## Key Fields per Metric

| Metric | Key Fields |
|--------|------------|
| MemStat | ctime, host_id, mem_total, mem_free, mem_available, cached, buffers, swap_total, swap_free, watermark_high, watermark_min, hardware_corrupted, virtual_cluster_id → memory usage = (mem_total - mem_free - cached - buffers) / mem_total * 100% |
| InstanceMemory | ctime, host_id, inst_name, dynamic_used_memory, max_dynamic_memory, dynamic_peak_memory, dynamic_used_shrctx, dynamic_peak_shrctx, process_used_memory, max_process_memory, shared_used_memory, max_shared_memory, comm_used_memory, max_comm_memory, cstore_used_memory, max_cstore_memory, topsql_used_memory, max_topsql_memory, other_used_memory, udf_reserved_memory, mmap_used_memory, storage_compress_memory, pooler_conn_memory, pooler_freeconn_memory → dynamic memory usage = (dynamic_used_memory / max_dynamic_memory) * 100%; process memory usage = (process_used_memory / max_process_memory) * 100% |
| memory_diagnose_detail | ctime, host_id, instance_name, active_sessions[{query, query_id, userName, mem_used, state, duration_ms, plan_type}], memory_pool{work_mem_used/total, shared_pool_used/total} |

## Query Differences per Step

| Step | metric_name | Paginated | Filtering | hcloud Command |
|------|-------------|-----------|-----------|----------------|
| Step 1 | MemStat | Yes (limit=200) | No | `hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<cid> --metric_name=MemStat --project_id=<pid> --from=<from_ts> --to=<to_ts> --offset=0 --limit=200` |
| Step 3 | InstanceMemory | Yes (limit=200) | Filter by inst_name | `hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<cid> --metric_name=InstanceMemory --project_id=<pid> --from=<from_ts> --to=<to_ts> --offset=0 --limit=200` |
| Step 4 | memory_diagnose_detail | Yes (limit=200, pagination required) | Filter by max_mem_hosts | `hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<cid> --metric_name=memory_diagnose_detail --project_id=<pid> --from=<from_ts> --to=<to_ts> --offset=0 --limit=200` |

## Memory Key Thresholds

| Metric | Threshold | Description |
|--------|-----------|-------------|
| System memory usage | > 80% | Node memory too high |
| System memory usage (all nodes) | > 70% | Cluster memory globally high |
| Inter-node memory deviation | > 30% | Memory imbalance, possible data skew |
| Dynamic memory usage | > 80% (persistent) | Instance memory configuration unreasonable |
| Single SQL memory proportion | > 20% | Single SQL causing high memory |
| omm/Ruby user memory proportion | > 30% | System internal tasks consuming high memory |
| work_mem usage rate | > 80% | work_mem configuration too large or SQL sort/hash spill |
| shared_pool usage rate | > 80% | Shared cache pressure, excessive connections |

## CN/DN Instance Distinction

| inst_name Pattern | Instance Type | Memory High Focus |
|-------------------|---------------|-------------------|
| Contains "cn" or "coordinator" | CN (Coordinator Node) | Connection skew, non-pushdown SQL, parsing pressure |
| Contains "dn" or "datanode" | DN (Data Node) | Data skew, computation skew, sort/hash spill |

## Memory Type Determination

| Memory Type | Condition | Focus |
|-------------|-----------|-------|
| Dynamic memory high | dynamic_used_memory proportion relatively high | Business SQL, work_mem configuration |
| Process memory high | process_used_memory proportion relatively high | Excessive connections, process leak |
