# Excel Report Template and Data Structure

> Extracted from SKILL.md Phase 6 + Phase 7.

## 1. Report Template (Markdown Format)

```markdown
# MRS Cluster Sizing Report

## 1. Component Investigation Summary

| Category | Component | Source | MRS Mapping |
|----------|-----------|--------|-------------|
| Compute | ... | ... | ... |
| Storage | ... | ... | ... |
| ... | ... | ... | ... |

### Workload Profile
- Data Volume: XX TB
- Daily Ingestion: XX GB/day
- Concurrency: XX concurrent jobs
- Latency: Batch / Near-real-time / Real-time
- Security: Kerberos enabled / disabled
- Storage Mode: HDFS / OBS / Mixed
- Original Cluster Cores: XX

## 2. Cluster Configuration

| Parameter | Value |
|-----------|-------|
| Cluster Type | Analysis / Streaming / Hybrid / Custom |
| MRS Version | MRS 3.3.0-LTS |
| Deployment Type | Compact / OMS-separate / Full-size |
| Components | Hadoop, Spark2x, Hive, HBase, ZooKeeper, ... |
| Security Mode | Kerberos: Yes/No, Ranger: Yes/No |
| Default ECS Series | aC9 (General Computing-plus) |

## 3. Node Specifications with Recommendation Reasons

> **Scope note**: the example below is the **elastic Task** variant (Core sized to the user-provided off-peak daily load, 40%; Task covers the peak). When elastic Task is disabled (`elastic_task.enabled = false`), the `Task (optional)` row is omitted and Core matches the original cluster in full — see §6, where `elastic_task.enabled` defaults to false.

| Node Group | Flavor | vCPU | Memory | System Disk | Data Disk (Shuffle) | Count | Role | Recommendation Reason |
|-----------|--------|------|--------|-------------|---------------------|-------|------|-----------------------|
| Master | ac9.8xlarge.4 | 32 | 128 GB | 480GB High IO | 1×600GB General SSD | 5 | Management/Control | [Reason: 1480 cores >= 100 -> 5 Master nodes (OMS-separate); OBS storage-compute separation -> NameNode heap requirement reduced 70% ≈7.5GB; but RM needs to schedule 1776 cores -> RM heap 8GB; total memory requirement ≈51GB -> select 128GB flavor to ensure scheduling; 1×600GB for NameNode metadata+edits log] |
| Core | ac9.32xlarge.4 | 128 | 512 GB | 480GB High IO | 8×640GB General SSD | 5 | Compute/Shuffle (monthly subscription) | [Reason: e.g., 40% of 1480=592 cores; 1:2 memory insufficient -> upgrade 1:4; 5×128=640>=592; shuffle 128×40=5120GB -> 8×640GB] |
| Task (optional) | ac9.32xlarge.4 | 128 | 512 GB | 480GB High IO | 8×640GB General SSD | 10 | Elastic Compute (on-demand) | [Reason: e.g., 60%+20%buffer=80% of original; 10×128=1280>=1184; same disk config as Core for Shuffle] |
| OBS Storage | - | - | - | - | OBS Standard Storage | 187TB (actual required) | - | Object Storage | [Reason: 560TB/3 replicas=187TB single replica -> OBS capacity 187TB actual required storage; Guardian unified access control] |

### Elastic Sizing Logic Detail
- **Original**: V vCPU, M GB memory
- **Buffer**: IF peak saturated -> Total = V×(1+B%), M×(1+B%); ELSE -> Total = V, M (no buffer)
- **Core**: V×L%, M×L%, where L% is the off-peak daily load ASKED from the user (based on ORIGINAL, NO buffer); peak demand is covered by Task nodes
- **Task**: Total - Core (buffer goes entirely to Task)
- **Data disk**: flexible, per-node shuffle = vCPU×40GB split into disks of 600-800GB per Core/Task node (identical config)

## 4. Source vs Target Resource Comparison

> **Scope note**: the `Core (40% daily)` / `Task (60%+buffer)` columns apply **only when elastic Task is enabled**. When elastic Task is disabled, the report uses `Core (full volume)` / `Task (no elastic)` headers and Core matches the original cluster in full.

| Resource | Original Cluster | Core (40% daily) | Task (60%+buffer) | Total Target | MRS Recommended | Growth % vs Original | Meets Requirement |
|----------|-----------------|-------------------|-------------------|-------------|-----------------|---------------------|-------------------|
| Total vCPU | 1,480 | 592 | 1,184 | 1,776 | 1,920 | +29.7% | ✓ Yes |
| Total Memory (GB) | 4,380 | 1,752 | 3,504 | 5,256 | 7,680 | +75.3% | ✓ Yes |
| Total Shuffle Storage | N/A | - | - | N/A | 60 TB | - | - |
| Total Nodes | - | - | - | - | 20 | - | - |
| Off-peak Daily Load (user-provided) | 40% | - | - | - | 40% (Core) | - | ✓ Yes |

### Comparison Notes
- **Buffer logic**: +20% buffer applied to TOTAL first, then split — Core gets original×40% (no buffer), Task gets the rest including buffer
- **CPU**: Core(640)+Task(1280)=1920 vCPU >= 1776 target (original+20%), +29.7% vs original
- **Memory**: Core(2560)+Task(5120)=7680 GB >= 5256 target, +75.3% vs original; surplus from 1:4 single-flavor constraint
- **Data disk**: Master has 1×600GB for metadata; Core and Task have identical 8×640GB for Shuffle
- **Shuffle total**: per-node disk total (8×640GB=5120GB) × node count

## 5. Recommendation Summary

| Decision Point | Candidate Options | Final Selection | Reasoning |
|---------------|-------------------|-----------------|-----------|
| ECS Series | aC9 / AC7 / C9 | aC9 | Default series, QingTian 1.0, 40%+ cost-performance improvement |
| Core Flavor Ratio | 1:2 / 1:4 | 1:4 | 1:2 (1280GB) fails memory target (1752GB); 1:4 (2560GB) satisfies both CPU and memory |
| **Core Flavor Size** | **ac9.32xlarge.4 ×12 / ac9.16xlarge.4 ×24 / ac9.32xlarge.2 ×18** | **ac9.32xlarge.4 ×12 (minimum surplus)** | **Single plan output: calculate Total_excess for each candidate flavor, select minimum; ac9.32xlarge.4×12 total excess 44.0% lowest with fewest nodes** |
| Master Node Count | 3 / 5-11 | 5 | Original cluster 1480 cores >= 100 -> OMS-separate mode, minimum 5 Master nodes |
| **Master Flavor** | **ac9.4xlarge.4 (16C/64G) / ac9.8xlarge.4 (32C/128G)** | **ac9.8xlarge.4 (32C/128G)** | **Based on industry NameNode heap calculation: OBS storage-compute separation -> NameNode heap ≈7.5GB; RM scheduling 1776 cores -> RM heap 8GB; total memory ≈51GB -> select 128GB to ensure scheduling** |
| **Buffer Logic** | **No buffer / +20% on Core / +20% on Total** | **+20% on Total** | **Peak resources continuously saturated -> total +20% buffer; buffer entirely to Task, Core based on original cluster 40% config without buffer** |
| **Core Sizing** | **Original×40% / (Original+20%)×40%** | **Original×40%** | **Core based on original cluster capacity: 1480×40%=592 cores, no buffer** |
| **Task Sizing** | **Total-Core / Original×60%** | **Total-Core** | **Task carries 60% peak +20% buffer =80%: 1776-592=1184 cores; single plan uses ac9.32xlarge.4 ×10 (1280C)** |
| **Master Data Disk** | **None / 1×600GB / flexible 600-800GB** | **1×600GB** | **Master for NameNode metadata and logs, single disk 600GB General SSD** |
| **Data Disk Planning** | **flexible 600-800GB per disk** | **8×640GB/node** | **shuffle=128×40=5120GB; N=floor(5120/600)=8; ceil(5120/8)=640GB (within 600-800 range)** |
| **Task Data Disk** | **None / Same as Core** | **Same as Core** | **Task needs Spark/Flink Shuffle spill disk, data disk config same as Core (8×640GB)** |
| **OBS Capacity** | **187TB actual / package tier** | **187TB actual required** | **560TB/3 replicas=187TB single replica; OBS capacity = actual required storage, no package tier rounding** |
| Deployment Mode | Compact / OMS-separate | OMS-separate | 1480 cores >= 100 -> mandatory OMS-separate for reliability |

```

## 2. Recommendation Decision Summary Template

| Decision Point | Candidate Options | Final Selection | Reasoning |
|---------------|-------------------|-----------------|-----------|
| ECS Series | aC9 / AC7 / C9 | aC9 | Default series, QingTian 1.0, 40%+ cost-performance improvement |
| Core Flavor Ratio | 1:2 / 1:4 | 1:4 | 1:2 (1280GB) fails memory target (1752GB); 1:4 (2560GB) satisfies both CPU and memory |
| **Core Flavor Size** | **ac9.32xlarge.4 ×12 / ac9.16xlarge.4 ×24 / ac9.32xlarge.2 ×18** | **ac9.32xlarge.4 ×12 (minimum surplus)** | **Single plan output: calculate Total_excess for each candidate flavor, select minimum; ac9.32xlarge.4×12 total excess 44.0% lowest with fewest nodes** |
| Master Node Count | 3 / 5-11 | 5 | Original cluster 1480 cores >= 100 -> OMS-separate mode, minimum 5 Master nodes |
| **Master Flavor** | **ac9.4xlarge.4 (16C/64G) / ac9.8xlarge.4 (32C/128G)** | **ac9.8xlarge.4 (32C/128G)** | **Based on industry NameNode heap calculation: OBS storage-compute separation -> NameNode heap ≈7.5GB; RM scheduling 1776 cores -> RM heap 8GB; total memory ≈51GB -> select 128GB to ensure scheduling** |
| **Buffer Logic** | **No buffer / +20% on Core / +20% on Total** | **+20% on Total** | **Peak resources continuously saturated -> total +20% buffer; buffer entirely to Task, Core based on original cluster 40% config without buffer** |
| **Core Sizing** | **Original×40% / (Original+20%)×40%** | **Original×40%** | **Core based on original cluster capacity: 1480×40%=592 cores, no buffer** |
| **Task Sizing** | **Total-Core / Original×60%** | **Total-Core** | **Task carries 60% peak +20% buffer =80%: 1776-592=1184 cores; single plan uses ac9.32xlarge.4 ×10 (1280C)** |
| **Master Data Disk** | **None / 1×600GB / flexible 600-800GB** | **1×600GB** | **Master for NameNode metadata and logs, single disk 600GB General SSD** |
| **Data Disk Planning** | **flexible 600-800GB per disk** | **8×640GB/node** | **shuffle=128×40=5120GB; N=floor(5120/600)=8; ceil(5120/8)=640GB (within 600-800 range)** |
| **Task Data Disk** | **None / Same as Core** | **Same as Core** | **Task needs Spark/Flink Shuffle spill disk, data disk config same as Core (8×640GB)** |
| **OBS Capacity** | **187TB actual / package tier** | **187TB actual required** | **560TB/3 replicas=187TB single replica; OBS capacity = actual required storage, no package tier rounding** |
| Deployment Mode | Compact / OMS-separate | OMS-separate | 1480 cores >= 100 -> mandatory OMS-separate for reliability |


## 3. Excel File Structure (4 Sheets)

The Excel file MUST contain **4 sheets**:

| Sheet # | Sheet Name | Content |
|---------|-----------|---------|
| Sheet 1 | Cluster Spec Recommendation | Single plan (minimum surplus) + OBS + recommendation reasons |
| Sheet 2 | Resource Comparison | Source cluster vs MRS recommended resources comparison |
| Sheet 3 | Selection Decision Rationale | Decision points, candidates, final selections, and reasoning |
| Sheet 4 | OBS Storage Spec | OBS storage capacity calculation and configuration details |

## 4. Detailed Sheet Definitions

### 4.1 Sheet 1: Cluster Spec Recommendation (Node Specifications)

**Top must include single plan summary** (1 row: final minimum-surplus plan), followed by **detailed specs of the plan**.

```
Top single plan summary (A1:E2):
  Plan | Core Flavor | Core Count | Total vCPU | Total Memory GB
  最终方案 (minimum surplus) | ac9.32xlarge.4 | 12 | 1536 | 6144

  Recommendation note: ac9.32xlarge.4×12 total excess 44.0% lowest (CPU+3.8% + Mem+40.2%); fewest nodes among tied candidates

Columns (detailed specs of the plan):
  A: Node Group
  B: Flavor
  C: vCPU (cores)
  D: Memory (GB)
  E: System Disk
  F: Data Disk (Shuffle)
  G: Per-Node Shuffle Disk Specification
  H: Data Disk Count (600-800GB each)
  I: Per-Node Shuffle Capacity (GB)
  J: Node Count
  K: Total vCPU
  L: Total Memory (GB)
  M: Total Shuffle Storage (TB)
  N: Recommendation Reason
  O: Q14 Check (Master utilization) — migration scenarios only; filled on the Master row, blank elsewhere

Example Row (Master - WITH data disk):
  Master | ac9.8xlarge.4 | 32 | 128 | 480GB High IO | 1×600GB General SSD | 600GB General SSD | 1 | 0 | 5 | 160 | 640 | 0 | Original cluster 1480 cores >= 100, need 5 Master nodes; OBS storage-compute separation -> NameNode heap requirement reduced 70% ≈7.5GB; RM needs to schedule 1776 cores -> RM heap 8GB; total memory requirement ≈51GB -> select 128GB flavor ac9.8xlarge.4 to ensure YARN scheduling | Q14: pass or "insufficient spec risk (…)" with original-vs-MRS utilization figures

Example Row (Core - single plan, WITH data disk):
  Core | ac9.32xlarge.4 | 128 | 512 | 480GB High IO | 8×640GB General SSD | 640GB General SSD | 8 | 5120 | 5 | 640 | 2560 | 25.0 | 40% original cluster load: 1480×40%=592 cores; single plan minimum surplus: ac9.32xlarge.4; 5×128=640>=592; shuffle 128×40=5120GB -> 8×640GB | (blank)

Example Row (Task - single plan, WITH data disk same as Core):
  Task | ac9.32xlarge.4 | 128 | 512 | 480GB High IO | 8×640GB General SSD | 640GB General SSD | 8 | 5120 | 10 | 1280 | 5120 | 50.0 | 80% target: 1776-592=1184 cores; 10×128=1280>=1184; data disk spec same as Core | (blank)
  Note: Task node flavor follows Core single plan selection (ac9.32xlarge.4)

Example Row (OBS Storage - actual required capacity):
  OBS Storage | - | - | - | - | OBS Standard Storage | - | - | 187TB (actual required) | - | - | 187 | Object Storage | 560TB/3 replicas=187TB -> OBS capacity 187TB actual required storage; Guardian unified access control
```

### 4.2 Sheet 2: Resource Comparison

```
Columns:
  A: Resource Item
  B: Original Cluster Config
  C: Core 40% Daily Load
  D: Task 60% + Buffer
  E: Total Target (with buffer)
  F: MRS Recommended Config
  G: Growth % vs Original
  H: Meets Target
  I: Notes

Example Rows:
  Total vCPU | 1480 | 592 | 1184 | 1776 | 1920 | +29.7% | ✓ | Core=original×40% no buffer; Task=Total-Core including buffer
  Total Memory (GB) | 4380 | 1752 | 3504 | 5256 | 7680 | +75.3% | ✓ | Memory excess due to 1:4 single flavor constraint
  Total Shuffle Storage (TB) | N/A | - | - | N/A | 75.0 | - | - | Core+Task per-node 5120GB × node count
  OBS Storage (TB) | 560 (3 replicas) | - | - | 187 (actual) | 187 | -66.6% | ✓ | 560÷3=187TB single replica -> 187TB actual required capacity
  Node Count | - | - | - | - | 20 | - | - | 5 Master+5 Core+10 Task
  Resource Summary | - | - | - | - | - | - | - | Core no buffer, buffer all to Task; meets +20% target
```

### 4.3 Sheet 3: Selection Decision Rationale

```
Columns:
  A: Decision Point
  B: Candidate Options
  C: Final Selection
  D: Selection Reasoning
  E: Rejected Reason

Example Rows:
  ECS Series | aC9 / AC7 / C9 | aC9 | Default General Computing-plus, QingTian 1.0 architecture | AC7 previous gen; C9 no enhanced features
  Buffer Logic | No buffer / +20% on Core / +20% on Total | +20% on Total | Peak resources saturated -> total +20%; buffer all to Task | Adding directly to Core causes Core spec waste
  Core Calculation Basis | Original cluster / After buffer | Original cluster | Core=original×40%=592 cores, no buffer | After buffer ×40% logic error
  Task Calculation Logic | Total-Core / Original×60% | Total-Core | Task=1776-592=1184 cores, including buffer | Original×60% excludes buffer
  Core Flavor Ratio | 1:2 / 1:4 | 1:4 | 1:2 (5×256=1280GB) only 73% memory; 1:4 (2560GB) satisfies both | 1:2 memory insufficient
  Master Node Count | 3 / 5-11 | 5 | 1480 cores >= 100 -> OMS-separate | 3 nodes only for <100 cores
  Master Flavor | ac9.4xlarge.4 (16C/64G) / ac9.8xlarge.4 (32C/128G) | ac9.8xlarge.4 (32C/128G) | OBS storage-compute separation -> NameNode heap ≈7.5GB; RM heap 8GB; total memory ≈51GB -> select 128GB | 64GB meets minimum but RM scheduling for large cluster tight
  Master Data Disk | None / 1×600GB | 1×600GB | NameNode metadata+logs | No disk -> insufficient metadata storage
  Task Data Disk | None / Same as Core | Same as Core (8×640GB) | Spark/Flink Shuffle spill | No disk -> Shuffle on system disk insufficient
  OBS Capacity | Actual required / package tier | Actual required (187TB) | 560TB/3 replicas=187TB single replica; report actual required storage directly | Package tier not used
  Data Disk Planning | flexible 600-800GB per disk | 8×640GB | shuffle=128×40=5120GB; N=floor(5120/600)=8; ceil(5120/8)=640GB (600-800 range) | Fixed 600GB or fewer-than-8 disks would exceed the 800GB per-disk cap
  Shuffle Total | Requirement only / per-node disk total × nodes | per-node disk total × nodes | 8×640GB=5120GB per node × node count = total shuffle | Requirement-only figure ignores disk granularity
  Storage Mode | Local HDFS / OBS | OBS storage-compute separation | 560TB storage-compute separation saves 95%+ | Local HDFS high cost
```

### 4.4 Sheet 4: OBS Storage Spec

```
Columns:
  A: Calculation Item
  B: Original Value
  C: Calculation Logic
  D: Result
  E: Notes

Example Rows:
  Data Source Type | HDFS (3 replicas) | - | - | User CDH cluster HDFS data
  HDFS Data Volume | 560 TB | - | 560 TB | Total capacity with 3 replicas
  Replica Count | 3 | - | 3 | HDFS default replica count
  Actual Required Capacity | - | 560 / 3 | 187 TB | OBS stores a single replica
  OBS Capacity (actual) | - | use actual required capacity directly | 187 TB | No package tier rounding
  OBS Storage Type | - | Standard Storage | 187 TB | Frequently accessed data
```

## 5. Excel Generation Rules

When generating the Excel file, follow these rules:

1. **File naming**: `MRS_Cluster_Sizing_Report_<YYYYMMDD>.xlsx`
2. **Use openpyxl library** (Python) to generate the file
3. **Formatting requirements**:
   - Header row: bold, background color #4472C4 (blue), white font
   - Column widths: auto-fit based on content
   - "Recommendation Reason" column: wider (40+ chars), wrap text
   - "Meets Target" column: green ✓ or red ✗
   - Total/Summary rows: bold with light gray background
   - Freeze top row for scrolling
4. **Sheet 2 (Resource Comparison)**: Highlight the Growth % column — green if meets target, red if not
5. **Sheet 3 (Selection Decision Rationale)**: Wrap text in "Selection Reasoning" and "Rejected Reason" columns
6. **Save location**: User's working directory or specified path
7. **4-sheet structure**: Sheets: Cluster Spec Recommendation, Resource Comparison, Selection Decision Rationale, OBS Storage Spec. Single plan output only; no dual plan comparison sheet.
8. **Q14 utilization check (migration scenarios)**: Sheet 1 column O MUST be populated on the Master row whenever the source cluster is known AND `master_mem_utilization_pct` / `master_cpu_utilization_pct` are provided. The conclusion MUST compare MRS planned Master spec against the original cluster's actual usage and flag "insufficient spec risk" when any of the Step 7 conditions is violated. Populate `source_cluster.node_count` / `master_node_count` / `master_node_memory_gb` / `master_node_vcpu` so the figures are exact rather than inferred.


## 6. Report Data Structure (Python dict)

The `report_data` dict passed to the Excel generator contains a **single plan** (minimum surplus).
No `plan_b` or `recommended_plan` field; no user selection needed.

```python
report_data = {
    "peak_saturated": True,
    "source_cluster": {
        "total_cores": 1480,
        "total_memory_gb": 4380,
        "node_count": 30,               # original cluster node count
        "master_node_count": 3,         # optional: nodes actually carrying master roles (Q14)
        "master_node_memory_gb": 128,   # optional: per-node memory of those master nodes (Q14)
        "master_node_vcpu": 32,         # optional: per-node vCPU of those master nodes (Q14)
        "master_mem_utilization_pct": 45,  # conditional: required for migration scenarios (Q14)
        "master_cpu_utilization_pct": 30,  # conditional: required for migration scenarios (Q14)
        "hdfs_capacity_tb": 560,        # existing (full) data volume
        "hdfs_replicas": 3,
        "daily_increment_gb": 500,      # daily incremental data
        "retention_days": 365,          # data retention period
        "full_data_volume_tb": 560,     # existing data + daily_increment × retention (single-replica calculation base)
        "hdfs_file_count_million": 20,  # 20 million files
        "yarn_containers_peak": 2000  # concurrent container count
    },
    "target": {
        "buffer_pct": 20,
        "total_with_buffer_cores": 1776,
        "total_with_buffer_memory_gb": 5256,
        "core_cores": 592, "core_memory_gb": 1752,
        "task_cores": 1184, "task_memory_gb": 3504
    },
    "elastic_task": {"enabled": True, "daily_load_pct": 40, "runtime_hours": 10, "runtime_hours_month": 300},  # daily_load_pct = off-peak load (user-provided), used to size Core
    "obs_storage": {
        "enabled": True, "actual_capacity_tb": 187,   # full_data_volume / replicas, no package tier
        "single_replica_tb": 187
    },

    # ======================= Single Plan (Minimum Surplus) =======================
    "plan_a": {  # Single final plan — minimum Total_excess
        "name": "最小冗余方案 — ac9.32xlarge.4 × 12",
        "core_flavor": "ac9.32xlarge.4", "core_vcpu": 128, "core_mem_gb": 512,
        "core_count": 12,
        "core_data_disk_count": 8,
        "core_data_disk_size_gb": 640,  # flexible: 5120GB need -> 8×640GB (600-800 range)
        "core_total_vcpu": 1536, "core_total_mem_gb": 6144,
        "core_fault_impact": "-8.3% vCPU",
        "total_nodes": 17,  # M5+C12
        "hdfs_datanodes": 12,
        "nodes_detail": [
            {"group": "Master", "flavor": "ac9.8xlarge.4", "count": 5, "reason": "..."},
            {"group": "Core", "flavor": "ac9.32xlarge.4", "count": 12, "reason": "..."}
        ]
    },

    "recommendation_reason": (
        "ac9.32xlarge.4×12: CPU+3.8%+内存+40.2%=总冗余44.0% lowest; "
        "vs ac9.32xlarge.2×18: 总冗余60.9%; vs ac9.16xlarge.4×24: 总冗余44.0% but more nodes. "
        "Select minimum Total_excess; on tie prefer fewer nodes."
    ),

    # Decision rationale (for Sheet 3)
    "decisions": [
        {"point": "Core规格选择(最小冗余)",
         "candidates": "ac9.32xl.4×12(冗余44.0%) / ac9.32xl.2×18(冗余60.9%) / ac9.16xl.4×24(冗余44.0%但更多节点)",
         "selected": "ac9.32xlarge.4 × 12 (最小冗余方案)",
         "reasoning": "CPU+3.8%+内存+40.2%=总冗余44.0%最低; vs 1:2方案总冗余60.9%; vs 64C规格冗余相同但节点翻倍",
         "rejected": "ac9.32xl.2×18: CPU+55.7%内存浪费严重; ac9.16xl.4×24: 冗余相同但24节点系统盘/管理费更高"},
        # ... other decision points as above
    ]
}
```
