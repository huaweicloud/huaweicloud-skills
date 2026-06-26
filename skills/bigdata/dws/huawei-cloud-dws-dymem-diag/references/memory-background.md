# Memory Background Knowledge - DWS Memory High Diagnosis

## Memory Usage Formulas

- **System Memory Usage** = (mem_total - mem_free - cached - buffers) / mem_total * 100%
  - mem_total: Total physical memory (MB)
  - mem_free: Free memory (MB)
  - cached: Page cache (MB)
  - buffers: Buffer cache (MB)

- **Dynamic Memory Usage** = (dynamic_used_memory / max_dynamic_memory) * 100%
  - dynamic_used_memory: Currently used dynamic memory
  - max_dynamic_memory: Maximum dynamic memory limit

- **Process Memory Usage** = (process_used_memory / max_process_memory) * 100%
  - process_used_memory: Currently used process memory
  - max_process_memory: Maximum process memory limit

## CN/DN Instance Distinction

Based on `inst_name` field in InstanceMemory (no instance_type field available):

| inst_name Pattern | Instance Type | Memory High Focus |
|-------------------|---------------|-------------------|
| Contains "cn" or "coordinator" | CN (Coordinator Node) | Connection skew, non-pushdown SQL, parsing pressure |
| Contains "dn" or "datanode" | DN (Data Node) | Data skew, computation skew, sort/hash spill |

## memory_pool Analysis

From memory_diagnose_detail's memory_pool field:

- **work_mem**: Memory for SQL sort/hash operations
  - work_mem usage rate = (work_mem_used / work_mem_total) * 100%
  - work_mem usage rate > 80% → SQL sort/hash operations consuming large memory, or work_mem configuration too large

- **shared_pool**: Shared cache for tables/indexes
  - shared_pool usage rate = (shared_pool_used / shared_pool_total) * 100%
  - shared_pool usage rate > 80% → Shared cache pressure, excessive connections

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
| Session duration | > 30 minutes | Long transaction / session leak |

## Memory Type Determination

Based on InstanceMemory dynamic memory vs process memory ratio:

| Memory Type | Condition | Focus |
|-------------|-----------|-------|
| Dynamic memory high | dynamic_used_memory proportion relatively high | Business SQL, work_mem configuration |
| Process memory high | process_used_memory proportion relatively high | Excessive connections, process leak |

## Node Scope Classification

| Scope | Condition | Tendency |
|-------|-----------|----------|
| All nodes memory high | High memory node ratio >= 80% | Business-side causes (high concurrency, complex SQL) |
| Single node memory high | High memory node count = 1 | Data skew, connection skew, abnormal process |
| Partial nodes memory high | 1 < count < most nodes | New/old node differences, head DN skew, local data skew |

## Important Principles

1. **Memory usage calculation excludes cached and buffers**: Linux uses free memory for page cache and buffer cache; these can be reclaimed when needed, so they should not be counted as used memory
2. **CN/DN distinction is essential**: CN and DN have different memory usage patterns; CN memory high usually relates to connection/SQL parsing, DN memory high usually relates to data/computation
3. **User identity judgment**: Database user is omm or Ruby → system cause (e.g., autovacuum, topsql, system tasks); other users → customer-side cause
4. **Session leak detection**: idle state but holding large memory is a key indicator of session leak; must check idle_session_with_high_mem data
5. **Memory leak detection**: Must compare multiple ctime data points; monotonically increasing trend without fallback is the key feature; single data point cannot determine memory leak
6. **Single SQL and multi-user concurrent are not mutually exclusive**: Both can be matched simultaneously, each listed as an independent anomaly item
