# Excel Report Template (Greenfield Scenario)

> This document defines the report_data data structure and 4-sheet output format for generate_mrs_report.py.

## File Naming

`MRS_Cluster_Sizing_Report_<YYYYMMDD>.xlsx`

## report_data Data Structure (Greenfield Scenario)

```python
report_data = {
    # Business requirements and estimated resources (core of greenfield scenario, replaces source_cluster in migration scenario)
    "business_requirements": {
        "workload_types": ["offline_batch", "streaming"],  # load types
        "daily_increment_tb": 5,          # daily incremental data TB
        "existing_data_tb": 50,           # existing data TB
        "retention_days": 180,            # data retention days
        "compression_ratio": 0.4,         # compression ratio
        "window_hours": 6,                # compute window hours
        "concurrency": 0,                 # concurrent users (query scenario)
        "throughput_mbps": 0,             # real-time throughput MB/s
        "partitions": 60,                 # Kafka partition count (streaming scenario)
        "qps_wan": 0,                     # HBase QPS (10K)
        "peak_buffer": False,             # whether peak sustains >90%
        "region": "cn-north-4",
        "storage_mode": "OBS"             # OBS or HDFS
    },
    # Estimated resources (Phase 3 result, used as selection target after user confirmation)
    "estimated_resources": {
        "total_cores": 752,               # estimated total vCPU
        "total_memory_gb": 3008,          # estimated total memory GB
        "storage_tb": 410,                # estimated total storage TB (logical volume)
        "estimation_basis": "Offline batch: 5TB x 40 / 6h = 34vCPU; Real-time streaming: 60 partitions = 60vCPU; off-peak x0.8; estimated value"
    },
    # Elastic Task (optional)
    "elastic_task": {"enabled": False},
    # Final plan (single plan)
    "plan_a": {
        "name": "...", "core_flavor": "ac9.16xlarge.4 (64C/256G)", "core_count": 12,
        "core_total_vcpu": 768, "core_total_mem_gb": 3072,
        "nodes_detail": [
            {"group": "Master", "flavor": "ac9.8xlarge.4 (32C/128G)", "count": 3, "reason": "..."},
            {"group": "Core", "flavor": "ac9.16xlarge.4 (64C/256G)", "count": 12, "reason": "..."}
        ]
    },
    "recommendation_reason": "...",
    "obs_storage": {
        "storage_tb": 410,                # actual required OBS capacity (no package tier)
        "savings_pct": 0                  # greenfield scenario can omit comparison
    },
    "decisions": [
        {"point": "...", "candidates": "...", "selected": "...", "reasoning": "...", "rejected": "..."}
    ]
}
```

## 4-Sheet Structure

### Sheet 1: Cluster Spec Recommendation

- A1:E2 single plan summary (plan name / Core spec / Core count / total vCPU / total memory GB)
- A4 selection explanation (recommendation_reason)
- A6 onwards 14-column detailed spec table: node group / flavor / vCPU / memory / system disk / data disk spec / Shuffle single disk / disk count / total Shuffle / node count / total vCPU / total memory GB / total Shuffle TB / recommendation reason
- `_enrich_node_detail()` auto-fills missing fields (parses vCPU from flavor to calculate disk count)

### Sheet 2: Resource Estimation Details (Greenfield Scenario, Replaces Migration Scenario "Resource Comparison")

Header: `['Estimated Resource Item', 'Business Input', 'Estimation Basis', 'Estimated Value', 'MRS Recommended Config', 'Redundancy %', 'Satisfied', 'Notes']`

| Estimated Resource Item | Business Input | Estimation Basis | Estimated Value | MRS Recommended | Redundancy | Satisfied |
|------------------------|---------------|-----------------|-----------------|-----------------|------------|-----------|
| Total vCPU | Daily 5TB / window 6h / 60 partitions | Batch 34 + Stream 60 = 94 x 0.8 (off-peak) | 76 | 768 | ... | Yes |
| Total Memory GB | vCPU x 4 | 136 + 240 = 376 x 0.8 | 301 | 3072 | ... | Yes |
| Storage TB | Existing 50 + daily 5 x 180 days x 0.4 | S = 50 + 360 | 410 | 410 (actual capacity) | ... | Yes |
| Shuffle Disk | Core vCPU x 40GB | 64C x 40 = 2560GB -> 5 disks | - | 5 x 600GB | - | - |
| Master | Core 12 nodes <= 20 | 16-core baseline + 64GB memory | - | 3 x (16C/64G) | - | - |

### Sheet 3: Selection Decision Rationale

Header: `['Decision Point', 'Candidate Options', 'Final Selection', 'Selection Rationale', 'Rejected Reason']`

Typical decision points in greenfield scenario:
1. Load estimation coefficient selection (simple / standard / complex)
2. Core spec selection (minimum redundancy: Total_excess comparison across candidates)
3. Flavor selection (by load type)
4. Master spec selection (by Core node count + metadata estimate)
5. Storage mode selection (OBS vs local HDFS)

### Sheet 4: OBS Storage Spec (Greenfield Scenario Estimation Version)

Header: `['Calculation Item', 'Business Input', 'Calculation Logic', 'Result', 'Notes']`

| Calculation Item | Business Input | Calculation Logic | Result |
|-----------------|---------------|-------------------|--------|
| Existing data | 50 TB | User input | 50 TB |
| Daily increment | 5 TB/day | User input | 5 TB/day |
| Retention days | 180 days | User input | 180 days |
| Compression ratio | 0.4 | ORC/Parquet | 0.4 |
| Total storage | - | 50 + 5 x 180 x 0.4 | 410 TB |
| OBS capacity | - | Use actual required storage (no package tier) | 410 TB |
