# Metric Reference - DWS CPU High Diagnosis

## Key Fields per Metric

| Metric | Key Fields |
|--------|------------|
| CpuStat | ctime, host_id, usr, sys, idle, iowait → CPU usage = usr + sys |
| business_concurrency | ctime, concurrency_value, active_connections |
| cpu_io_diagnose_detail | Flat row structure: ctime, host_id, inst_name, username, cpu_rate, count, datname, io_read, io_write, query_id, query, duration_ms, state |
| node_process_cpu_top20 | ctime, host_id, processes[{pid, command, args, cpu_rate, memory_pct, username}] (may return null) |
| command_cpu_usage | ctime, host_id, command, args (command_detail), cpu_rate, username. command differentiates: `gaussdb-dn` (datanode main), `gaussdb-cn` (coordinator main), `gaussdb` (fenced UDF subprocess), `python3`, `java`, `sh`, `cm_agent`, `gs_gtm`, etc. username is OS user (e.g., Ruby, root). |

## Query Differences per Step

| Step | metric_name | Paginated | Filtering |
|------|-------------|-----------|-----------|
| Step 1 | CpuStat | Yes (limit=200) | No |
| Step 3 | business_concurrency | Yes (limit=200) | No |
| Step 4 | cpu_io_diagnose_detail | Yes (limit=200, pagination required) | Filter by nodes_to_analyze |
| Step 5 | node_process_cpu_top20 | Yes (limit=200) | Filter by nodes_to_analyze |
| Step 5.5 | command_cpu_usage | Yes (limit=200) | No |
