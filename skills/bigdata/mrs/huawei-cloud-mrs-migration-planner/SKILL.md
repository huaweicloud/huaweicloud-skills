---
name: huawei-cloud-mrs-migration-planner
description: |
  Huawei Cloud MRS migration planning. CDH/EMR migration to MRS, component investigation, cluster type and node spec matching, outputs report and Excel.
  Investigates existing cluster component usage and resource scale, matches MRS cluster type and node flavors, outputs migration planning report with minimum resource surplus.
  Applicable to MRS cluster planning, node spec selection, big data cluster migration, CDH/EMR migration, and resource planning scenarios.
  Trigger words: "MRS planning", "MRS sizing", "MRS cluster planning", "MRS node spec", "CDH migration to MRS", "EMR migration to MRS", "MRS resource planning", "Huawei Cloud MRS", "MapReduce Service", "big data cluster migration", "MRS spec recommendation", "migrate to MRS", "MRS规划", "MRS选型", "MRS集群规划", "MRS节点规格", "CDH迁移MRS", "EMR迁移MRS", "MRS资源规划", "华为云MRS", "大数据集群迁移", "MRS规格推荐", "迁移MRS"
tags:
  - huawei-cloud
  - MRS
  - migration
version: "1.0.0"
license: MIT
---

# Huawei Cloud MRS Cluster Migration Planning and Sizing

## Trigger Words

**Chinese triggers:** "MRS规划", "MRS选型", "MRS集群规划", "MRS节点规格", "CDH迁移MRS", "EMR迁移MRS", "MRS资源规划", "华为云MRS", "MapReduce Service", "大数据集群迁移", "MRS规格推荐", "迁移MRS"

**English triggers:** "MRS planning", "MRS sizing", "MRS cluster planning", "MRS node spec", "CDH migration to MRS", "EMR migration to MRS", "MRS resource planning", "Huawei Cloud MRS", "MapReduce Service", "big data cluster migration", "MRS spec recommendation", "migrate to MRS"

## Overview

For scenarios migrating big data clusters such as CDH / Tencent EMR / Alibaba EMR to Huawei Cloud MRS, this skill investigates existing cluster component usage and resource scale, matches MRS cluster type and node flavors, and outputs a migration planning report with minimum resource surplus. Functional boundary: component investigation -> cluster type matching -> node spec planning -> storage & disk planning -> report output -> Excel generation.

## Prerequisites

- Python3 + openpyxl (`pip install openpyxl`) — for generating multi-sheet Excel report



## Workflow

| Phase | Content | Output |
|-------|---------|--------|
| Phase 1 | Component investigation: collect existing big data component usage, workload characteristics, Master sizing info | Component list + workload profile |
| Phase 2 | Cluster type matching: select cluster type based on components, MRS version, dependency resolution | Cluster type + component dependencies |
| Phase 3 | Node spec planning: Master sizing (industry NameNode heap standards), Core/Task single-plan selection (minimum surplus) | Single-plan flavor + data disk config |
| Phase 4 | Storage & disk planning: system disk, data disk, OBS capacity calculation | Disk config + OBS plan |
| Phase 5 | Report output: structured Markdown report with flavor recommendation, resource comparison, decision rationale | Markdown report |
| Phase 6 | Excel report generation: 4-sheet multi-dimensional report (single plan) | MRS_Cluster_Sizing_Report.xlsx |

### Phase 1: Component Investigation

Collect existing big data component usage, workload characteristics, and Master sizing information. There are 18 key decision questions, including data volume, daily incremental data, data retention period, storage mode, elastic Task nodes, off-peak daily load (asked only when elastic Task is enabled; used to size Core nodes), elastic Task runtime hours, peak buffer confirmation, Master sizing info (HDFS total file count, HBase deployment, YARN concurrent container count), and migration scenario Master node utilization check (Q14, triggered only in migration scenarios, verifies whether the MRS planned Master spec is sufficient).

> When elastic Task nodes are enabled, the off-peak (non-peak) daily load MUST be explicitly asked of the user, and Core nodes are sized from this daily load. Peak demand is covered by elastic Task nodes.

> Full data volume = existing data + daily incremental data × retention period. All sizing (cores/memory/storage) is calculated on this full data volume, not on the incremental portion alone.

> Component mapping table and cluster type matching rules: [references/component-mapping.md](references/component-mapping.md)

### Phase 2: Cluster Type and Version Matching

Select cluster type (Analysis/Streaming/Hybrid/Custom) and MRS version based on component usage. Default recommendation: MRS 3.3.0-LTS.

> Detailed cluster type selection logic: [references/component-mapping.md](references/component-mapping.md)

### Phase 3: Node Spec Planning

- **Master sizing**: Based on industry NameNode heap memory standards (Cloudera: 1GB/M blocks; Aliyun: (Files_M+Blocks_M)×512MB). Master memory >= 64GB (MRS 3.x hard constraint). 7-step algorithm includes migration scenario utilization check (Step 7).
- **Core/Task single-plan selection**: All Core nodes use the same flavor (uniform), minimum surplus principle (Total_excess = CPU_excess% + Mem_excess% minimized). Data disk is planned flexibly: per-node shuffle requirement = vCPU × 40 GB, disk size 600 GB minimum and never above 800 GB; use the fewest disks that fit (e.g. 640 GB -> 1×640 GB, 1400 GB -> 2×700 GB, 2400 GB -> 4×600 GB).
- **Flavor selection**: Master and Core can use different series. Master selected by memory requirement, Core selected by workload (Spark/Flink -> aC9, HBase -> m6, Kafka -> i3, cost-sensitive -> s7). Core nodes must be uniform.

> Master 7-step algorithm: [references/master-sizing-algorithm.md](references/master-sizing-algorithm.md)
> Core/Task single-plan algorithm: [references/core-task-single-plan-algorithm.md](references/core-task-single-plan-algorithm.md)
> ECS flavor catalog and series selection matrix: [references/ecs-flavor-catalog.md](references/ecs-flavor-catalog.md)

### Phase 4: Storage and Disk Planning

System disk 480GB High IO, Master data disk 1×600GB General SSD, Core/Task data disk calculated by formula. OBS storage-compute separation: OBS capacity = actual required storage (single-replica); total shuffle = per-node disk total × node count.

> Full disk config and OBS capacity calculation: [references/storage-disk-planning.md](references/storage-disk-planning.md)

### Phase 5: Report Output

Generate structured Markdown report with 5 sections: component investigation summary, cluster configuration, node specs and recommendation rationale, original cluster vs MRS resource comparison, recommendation decision summary.

> Report template: [references/excel-report-template.md](references/excel-report-template.md)

### Phase 6: Excel Report Generation

Agent writes Phase 1-4 investigation results (source cluster info, single plan, recommendation reason, OBS storage, decisions) to `report.json`, then generates 4-sheet Excel report: cluster spec recommendation, resource comparison, selection decision rationale, OBS storage spec.

For migration scenarios, `source_cluster` MUST also carry the Q14 inputs (`node_count`, `master_node_count`, `master_node_memory_gb`, `master_node_vcpu`, `master_mem_utilization_pct`, `master_cpu_utilization_pct`) so the script can render the Sheet 1 "Q14 Check (Master utilization)" column objectively instead of relying on prose in the decisions table.

> Full sheet column definitions: [references/excel-report-template.md](references/excel-report-template.md)
> Python script implementation: [scripts/generate_mrs_report.py](scripts/generate_mrs_report.py)

## Output Rules

- **Single-plan output**: Output only 1 final plan (minimum surplus); no dual-plan comparison; no user selection needed
- **Minimum surplus selection**: For each candidate flavor calculate N = max(ceil(V/flavor_vCPU), ceil(M/flavor_memory)), Total_excess = CPU_excess% + Mem_excess%, select the minimum. On tie, select fewer nodes
- **Migration scenario Master utilization check (Q14)**: Migration scenarios must ask current Master node CPU/memory utilization. When MRS planned total memory < original cluster actual usage (total × utilization), must annotate "memory severely insufficient" and upgrade flavor. The conclusion MUST be recorded in Sheet 1 column O "Q14 Check (Master utilization)" on the Master row (rendered by the script from the `source_cluster` Q14 inputs) — not only as prose inside the decisions table
- **Core node uniform constraint**: All Core nodes must use the same flavor; heterogeneous deployment not allowed
- **Shuffle disk config**: Excel report must list Shuffle disk details: per-node shuffle requirement = vCPU × 40 GB, single disk 600-800 GB (flexible: fewest disks that fit), disk count = the planned flexible count
- **Shuffle total**: Total shuffle = per-node data disk total (disk size × disk count) × node count
- **OBS capacity**: OBS storage size = actual required storage (single-replica), no package tier rounding
- **Full data volume basis**: All sizing (cores, memory, storage) is based on full data volume = existing data + daily incremental data × retention period
- **Resource comparison table**: Report must include original cluster vs MRS recommended config comparison table, with difference values and growth percentages
- **Recommendation decision rationale**: Each node flavor and decision point must include clear reasoning text
- **Functional boundary**: MRS cluster full-process planning (component investigation -> spec selection -> Excel report); excludes deployment/operations, performance tuning, data migration implementation, price estimation

## Core Commands

### Report Generation

Agent writes Phase 1-4 investigation results to `report.json`, then generates Excel:

```bash
python scripts/generate_mrs_report.py --input report.json
```

If no `--input` provided, runs built-in demo data (1480 cores CDH migration):

```bash
python scripts/generate_mrs_report.py
```

Optional `--output` to specify output path:

```bash
python scripts/generate_mrs_report.py --input report.json --output MRS_Report.xlsx
```

File naming: `MRS_Cluster_Sizing_Report_<YYYYMMDD>.xlsx`

## Parameter Confirmation

The following parameters must be confirmed with the user before entering spec selection:

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| Data volume | Required | Existing data volume (GB/TB); basis for storage and Master sizing | N/A |
| Daily incremental data | Required | Daily incremental data volume (GB/day); full data volume = existing data + daily incremental × retention period | N/A |
| Data retention period | Required | Data retention period (days); full data volume = existing data + daily incremental × retention days | N/A |
| Storage mode | Required | HDFS / OBS storage-compute separation / Mixed | N/A |
| Elastic Task nodes | Required | Whether elastic Task nodes are needed; peak/off-peak scaling | No |
| Off-peak daily load | Conditional | Non-peak daily workload level (% of original cluster resources); used to size Core nodes; peak demand is covered by elastic Task nodes; only asked when elastic Task enabled | N/A |
| Task runtime hours | Conditional | Elastic Task node daily runtime hours for on-demand billing cost estimation; only asked when elastic Task enabled | 8h/day |
| Peak buffer confirmation | Conditional | Only when user confirms "peak resources continuously saturated (>90%)" add 20% buffer | No buffer |
| HDFS total file count | Required | For NameNode heap calculation (Master sizing) | N/A |
| HBase deployment | Required | Whether HBase is deployed; affects Master flavor selection | No |
| YARN concurrent container count | Required | For ResourceManager heap estimation | N/A |
| Migration scenario Master utilization (Q14) | Conditional | Migration scenarios must ask current Master node CPU/memory utilization to verify MRS planned Master spec sufficiency | N/A |

## Notes

1. **MRS 3.x Master nodes** must have >= 64 GB RAM — hard requirement. Master node count: original cluster < 100 cores -> 3 nodes; >= 100 cores -> 5-11 nodes; > 500 Core nodes -> 9-11 nodes
2. **Master vCPU selection rule (by Core node count)**: <= 20 -> 16 cores, 20-50 -> 32 cores, > 50 -> 64 cores. OBS mode minimum 128GB to ensure ResourceManager scheduling
3. **Default ECS series**: aC9 (General Computing-plus, QingTian 1.0). Master and Core can use different series, but Core nodes must be uniform
4. **Data disk planning (flexible)**: per-node shuffle requirement = vCPU × 40 GB; single disk between 600 GB and 800 GB; use the fewest disks that fit (640 GB -> 1×640 GB, 1400 GB -> 2×700 GB, 2400 GB -> 4×600 GB). No fixed minimum of 4 disks
5. **Elastic Task algorithm (total buffer method)**: Ask the user for the off-peak daily load L% first; Total = original × (1 + buffer%); Core = original × L% (off-peak daily load, no buffer); Task = Total - Core (includes all buffer). Core is sized for the non-peak daily load, and peak demand is covered by elastic Task nodes
6. **OBS storage-compute separation**: NameNode heap requirement reduced 50-70%. OBS capacity = actual required storage (single-replica); no package tier rounding
7. **Shuffle total**: Total shuffle = per-node disk total (disk size × disk count) × node count
8. **Buffer determination**: Only when user confirms "peak resources continuously saturated (>90%)" add 20% buffer; buffer applied to total resources then split into Core and Task
9. **Kerberos** does not affect resource spec; only affects Master node count and cluster security architecture. Production/finance scenarios recommend enabling
10. **ZooKeeper** is automatically included in all cluster plans. **DBService** is auto-configured as a dependency
11. **Excel report (Phase 6)**: Must generate 4-sheet Excel file. generate_mrs_report.py _enrich_node_detail() auto-parses vCPU from flavor and calculates disk count and capacity

## References

| Document | Description |
|----------|-------------|
| [Component Mapping](references/component-mapping.md) | Component mapping table and cluster type matching rules |
| [ECS Flavor Catalog](references/ecs-flavor-catalog.md) | ECS flavor catalog and series selection matrix |
| [Master Sizing Algorithm](references/master-sizing-algorithm.md) | Master 7-step sizing algorithm |
| [Single Plan Algorithm](references/core-task-single-plan-algorithm.md) | Core/Task single-plan selection algorithm |
| [Storage Disk Planning](references/storage-disk-planning.md) | Storage and disk planning |
| [Sizing Scenarios](references/sizing-scenarios.md) | Common spec selection scenarios |
| [Excel Report Template](references/excel-report-template.md) | Excel report template and data structure |
| [IAM Policies](references/iam-policies.md) | IAM permission requirements (no API permissions needed for this planning skill) |
| [Verification Methods](references/verification-method.md) | Output verification and validation methods |

## Code Structure

```text
scripts/
└── generate_mrs_report.py            # Excel report generation (4 sheets, single plan)
references/
├── component-mapping.md              # Component mapping table and cluster type matching rules
├── core-task-single-plan-algorithm.md # Core/Task single-plan selection algorithm
├── ecs-flavor-catalog.md             # ECS flavor catalog and series selection matrix
├── excel-report-template.md          # Excel report template and data structure
├── iam-policies.md                   # IAM permission requirements (no API permissions needed)
├── master-sizing-algorithm.md        # Master 7-step sizing algorithm
├── sizing-scenarios.md               # Common spec selection scenarios
├── storage-disk-planning.md          # Storage and disk planning
└── verification-method.md            # Output verification and validation methods
```

## Verification

- Execute `python scripts/generate_mrs_report.py` to generate Excel report; confirm 4 sheets output (cluster spec recommendation / resource comparison / selection decision rationale / OBS storage spec)
- Verify recommended spec satisfies hard constraints: Master >= 64GB RAM, Core nodes uniform, node count meets HA requirements
- Verify resource comparison table includes original cluster vs MRS recommended config comparison, with difference values and growth percentages
- Migration scenario confirms Master utilization check has been executed (Q14) and that Sheet 1 column O "Q14 Check (Master utilization)" is populated on the Master row
- Verify `report.json` carries the Q14 inputs (`master_node_count`, `master_node_memory_gb`, `master_node_vcpu`, `master_mem_utilization_pct`, `master_cpu_utilization_pct`) in migration scenarios; column O renders "-" when they are absent

## Best Practices

- Migration scenarios must ask Master node CPU/memory utilization; when MRS planned memory < original cluster actual usage, must annotate "memory severely insufficient"
- When elastic Task is enabled, ask the user for the non-peak (off-peak) daily load; size Core from that daily load and cover peak demand with elastic Task nodes (never silently derive the load)
- Elastic Task split uses total buffer method: buffer applied to total resources then split into Core and Task; do not add buffer to Core
- OBS storage-compute separation can reduce NameNode heap requirement 50-70%; preferred for large-capacity scenarios
- OBS capacity is given as the actual required storage (single-replica); do not round up to a package tier
- Core/Task shuffle disks are planned flexibly within 600-800 GB per disk; total shuffle = per-node disk total × node count
- All sizing uses the full data volume (existing data + daily incremental × retention period)
- Peak buffer only added when user confirms "resources continuously saturated > 90%"; no buffer by default
- Kerberos does not affect resource spec; only affects Master node count and security architecture

## Edge Cases

- **Master memory hard constraint**: MRS 3.x Master nodes must have >= 64GB RAM; cannot be lower regardless of cluster size
- **Core node heterogeneous prohibition**: All Core nodes must use the same flavor; heterogeneous mixing not allowed. Master and Core can use different series
- **Elastic Task buffer position**: Buffer applied to total resources then split into Core and Task; prohibited from adding buffer to Core nodes (common error: Core = total × load% × (1 + buffer%))
- **Off-peak daily load must be asked**: When elastic Task is enabled, the non-peak (off-peak) daily load MUST be explicitly asked of the user and used to size Core; do not silently derive it from the task window. Peak demand is covered by elastic Task nodes
- **OBS storage-compute separation NameNode optimization**: OBS mode reduces NameNode heap requirement 50-70%; Master memory spec can be appropriately reduced
- **Peak buffer trigger condition**: Only when user explicitly confirms "peak resources continuously saturated (>90%)" add 20% buffer; no buffer by default
- **Migration scenario Master utilization check**: Migration scenarios must ask original cluster Master node CPU/memory utilization (Q14); when MRS planned total memory < original cluster actual usage, annotate "memory severely insufficient" and upgrade flavor
- **Small cluster Master node count**: Original cluster < 100 cores -> 3 Master nodes; >= 100 cores -> 5-11 nodes; > 500 Core nodes -> 9-11 nodes. Prohibit 1480-core cluster selecting 3 Master nodes
- **Flexible shuffle disk**: per-node shuffle requirement = vCPU × 40 GB, split into disks of 600-800 GB; 640 GB -> 1×640 GB, 1400 GB -> 2×700 GB, 2400 GB -> 4×600 GB. There is no fixed minimum disk count
- **Shuffle total calculation**: Total shuffle = per-node disk total (disk size × disk count) × node count; do not report shuffle total from the raw vCPU × 40 requirement alone
- **OBS capacity**: OBS storage size = actual required storage (single-replica); package tiers are not used
- **Data volume basis**: Sizing uses the full data volume = existing data + daily incremental data × retention period

