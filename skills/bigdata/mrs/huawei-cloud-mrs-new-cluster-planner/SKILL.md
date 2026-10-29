---
name: huawei-cloud-mrs-new-cluster-planner
description: |
  Huawei Cloud MRS new cluster spec planning. Derives YARN and storage requirements from business investigation, evaluates node specs, outputs Excel report.
  Automatically evaluates Master and Core node specs and quantities based on five load type models, and outputs a minimum-redundancy spec plan.
  Applicable to MRS new cluster planning, node spec selection, resource estimation, capacity planning, and OBS storage-compute separation scenarios.
  Trigger words: "new MRS", "new MRS cluster", "MRS new cluster planning", "MRS sizing", "MRS cluster planning", "MRS node spec", "MRS resource planning", "Huawei Cloud MRS", "MapReduce Service", "MRS spec recommendation", "new big data cluster", "新建MRS", "新建MRS集群", "MRS新集群规划", "MRS选型", "MRS集群规划", "MRS节点规格", "MRS资源规划", "华为云MRS", "MRS规格推荐", "新建大数据集群"
tags:
  - huawei-cloud
  - MRS
  - new-cluster
version: "1.0.0"
license: MIT
---

# Huawei Cloud MRS New Cluster Spec Planning

## Trigger Words

**Chinese triggers:** "新建MRS", "新建MRS集群", "MRS新集群规划", "MRS选型", "MRS集群规划", "MRS节点规格", "MRS资源规划", "华为云MRS", "MapReduce Service", "MRS规格推荐", "新建大数据集群"

**English triggers:** "new MRS", "new MRS cluster", "MRS new cluster planning", "MRS sizing", "MRS cluster planning", "MRS node spec", "MRS resource planning", "Huawei Cloud MRS", "MapReduce Service", "MRS spec recommendation", "new big data cluster"

## Overview

For **greenfield** MRS cluster scenarios, derives YARN vCPU/memory and storage requirements through business investigation (components, daily incremental data, compute window, concurrency, throughput), evaluates Master and Core node specs and quantities, and outputs a minimum-redundancy spec plan that fits business requirements. Key difference from the migration scenario skill (huawei-cloud-mrs-migration-planner): **no existing cluster resource benchmark; resource targets are derived from business load models**.

Security rule: Resource estimation coefficients are industry experience-based estimates and must be annotated as "estimated value" in the report. The report script only takes business data via `--input`/stdin and generates the Excel file locally — it accepts no arbitrary shell arguments, performs no shell execution, and makes no cloud resource write operations.

## Prerequisites

- Python3 + openpyxl (`pip install openpyxl`) — for generating multi-sheet Excel report
- Deployment region defaults to cn-north-4 (widest flavor availability); no need to ask user. If user explicitly specifies another region, verify aC9 and other series availability in that region before sizing


## Workflow

| Phase | Content | Output |
|-------|---------|--------|
| Phase 1 | Business investigation: component requirements, data scale, load characteristics (14 required + 4 estimation items) | Component list + business load profile |
| Phase 2 | Cluster type matching: select cluster type, MRS version, dependency resolution based on components | Cluster type + component dependencies |
| Phase 3 | Resource estimation: business requirements -> YARN vCPU/memory/storage (five load type models) | Estimated resource targets (annotated as estimated values) |
| Phase 4 | Node spec planning: Master (node count + vCPU + memory), Core (minimum-redundancy selection) | Master/Core specs and node counts |
| Phase 5 | Storage and disk planning: system disk, data disk, OBS capacity calculation | Disk configuration + OBS plan |
| Phase 6 | Report output + Excel generation: 4-sheet multi-dimensional report | MRS_Cluster_Sizing_Report.xlsx |

### Phase 1: Business Investigation

For greenfield scenarios there is no existing cluster; investigate **business requirements and load characteristics**. Questions fall into three categories:

- **Required items (14)**: business type, daily incremental data (pre-compression logical volume), existing data + retention days, data compression format and ratio, data temperature distribution (hot:warm:cold ratio), business complexity, job concurrency, compute window, real-time throughput (streaming), concurrent users (OLAP), peak load description, business growth rate, storage mode, elastic Task requirement
- **Optional item**: deployment region (default cn-north-4, widest flavor availability; only ask if user explicitly needs another region)
- **Estimation items (4)**: streaming State size (default medium State coefficient 6), metadata file characteristics (default 500K/TB), whether load sustains >90% (default No), **hot data compute ratio (default 100%, 即所有热数据都可能参与计算)** — estimated using experience defaults and explicitly annotated; recalibrate with actual monitoring data after running
- **Deployment config items (moved out of Phase 1)**: Kerberos does not affect resource specs, moved to Phase 2

> Detailed component mapping table: [references/component-mapping.md](references/component-mapping.md)

### Phase 2: Cluster Type and Version Matching

Select cluster type (Analysis/Streaming/Hybrid/Custom) and MRS version based on business components. Default recommendation: MRS 3.3.0-LTS. Kerberos is a deployment config item that only affects Master node count and cluster security architecture.

> Detailed cluster type selection logic: [references/component-mapping.md](references/component-mapping.md)

### Phase 3: Resource Estimation (Core of Greenfield Scenario)

**Greenfield scenario has no existing cluster resource benchmark**; resource targets are derived from business load models. Select estimation model by load type:

| Load Type | Estimation Formula |
|-----------|-------------------|
| Offline batch | D_compute = daily_increment + existing_data × hot_ratio × hot_compute_ratio; vCPU = D_compute × unit_CPU_coefficient ÷ compute_window_hours; memory = vCPU × R |
| Real-time streaming | vCPU = partitions × 1 OR throughput_MBps ÷ 10; memory = vCPU × 4 |
| Interactive query | vCPU = concurrent_users × 4; memory = vCPU × 4 |
| HBase | vCPU = QPS_wan ÷ 0.6; memory = hot_data_TB × 16 OR vCPU × 8 |
| Kafka | vCPU = daily_messages_100M × 2; memory = vCPU × 4 |

Complexity coefficients: Simple ETL=20, Standard warehouse=40, Complex compute/ML=80 vCPU·h/TB. **离线批处理必须考虑热数据参与计算量，不能仅看增量数据**。Mixed loads are estimated per item then summed (peak off-peak can apply ×0.8 discount). All estimated resources must be annotated as "estimated value" with the estimation process shown; proceed to Phase 4 only after user confirmation.

> Full five load type estimation models: [references/business-to-resource-algorithm.md](references/business-to-resource-algorithm.md)

### Phase 4: Node Spec Planning

- **Master node evaluation**: Node count determined by planned Core total cores (<100 -> 3 nodes, >=100 -> 5 nodes, >500 Core nodes -> 9-11 nodes). vCPU selected by Core node count (<=20 -> 16 cores, 20-50 -> 32 cores, >50 -> 64 cores). Memory calculated by 6-step algorithm (industry NameNode heap standard), minimum 64GB hard constraint, OBS mode does not enforce 128GB
- **Core node evaluation**: All Core nodes use the same spec (uniform/isomorphic), minimum-redundancy selection. Data disk formula: `max(1, ceil(vCPU × 40 / 600))` × 600GB General SSD
- **Flavor selection**: Master and Core can use different flavors, Core must be isomorphic. Master selected by memory requirement, Core selected by load type. **Flavors MUST be chosen from the official MRS-supported ECS spec list (localized in the flavor catalog); do not recommend any series/flavor MRS does not support (e.g. s-series or 192-vCPU flavors)**

> Master 6-step algorithm: [references/master-sizing-algorithm.md](references/master-sizing-algorithm.md)
> Core selection algorithm: [references/core-sizing-algorithm.md](references/core-sizing-algorithm.md)
> ECS flavor catalog (MRS-supported, localized from official doc): [references/ecs-flavor-catalog.md](references/ecs-flavor-catalog.md)

### Phase 5: Storage and Disk Planning

System disk 480GB High IO, Master data disk 1×600GB General SSD, Core/Task data disk calculated by formula. OBS storage-compute separation: total storage = existing data + daily_increment × retention_days × compression_ratio, reported directly as the actual required capacity (no package tier rounding).

> Full disk configuration: [references/storage-disk-planning.md](references/storage-disk-planning.md)

### Phase 6: Report Output + Excel Generation

Generate Markdown report (5 sections: business investigation summary, resource estimation details, cluster config and spec recommendation, estimated resources vs MRS comparison, decision summary) and 4-sheet Excel report.

> Full sheet column definitions: [references/excel-report-template.md](references/excel-report-template.md)
> Python script implementation: [scripts/generate_mrs_report.py](scripts/generate_mrs_report.py)

## Output Rules

- **Single plan output**: Output only 1 final plan (minimum redundancy); no dual-plan comparison
- **Minimum-redundancy selection**: Using estimated resources as target, calculate Total_excess = CPU_excess% + Mem_excess% for candidate specs; select the minimum. Ties prefer fewer nodes
- **Estimation confirmation mechanism**: Phase 3 estimation results must be shown to user first (formula + coefficients + results + estimated value annotation); proceed to Phase 4 only after user confirms or corrects
- **Core node isomorphic constraint**: All Core nodes must use the same spec; heterogeneous configs are not allowed
- **Greenfield scenario does not enforce minimum scale limit**: Does not enforce minimum 3 Core nodes; output per algorithm N value. N=1 no HA (test only), N=2 has HA but Shuffle marginal (acceptable with OBS), N>=3 standard HA
- **Master memory per algorithm (avoid over-provisioning)**: Strictly select spec by 6-step algorithm result. Algorithm <=64GB uses 64GB (satisfies MRS hard constraint); only upgrade when algorithm value > spec memory
- **Four estimation items annotation**: Streaming State size (A1), metadata file characteristics (A2), load sustains >90% (A3), hot data compute ratio (A4, default 100%) estimated with defaults and annotated; recommend recalibrating with monitoring data after 1-2 weeks of running
- **Data retention and compression must be confirmed**: Affects OBS capacity by 50%+; when not provided, estimate with retention 180 days / compression 0.5 and annotate
- **Shuffle disk configuration**: Excel report must list Shuffle disk details
- **Functional boundary**: MRS new cluster planning (business investigation -> resource estimation -> spec selection -> Excel report); does not include deployment ops, performance tuning, or data migration implementation

## Core Commands

### Report Generation

```bash
python scripts/generate_mrs_report.py --input <report_data.json>
```

`<report_data.json>` 为业务调研 + 资源推算 + 方案选型结果汇总的 JSON 文件，结构见 [references/excel-report-template.md](references/excel-report-template.md)（完整示例见 [references/example-report-data.json](references/example-report-data.json)），必需字段：`business_requirements` / `estimated_resources` / `plan_a`。另支持 stdin 管道输入（`--input -`）、`--output <FILE>` 指定输出路径；`--example` 可生成内置示例（仅供测试/演示）。

File naming: `MRS_Cluster_Sizing_Report_<YYYYMMDD>.xlsx`

## Parameter Confirmation

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| Deployment region | Optional | Target region; for confirming ECS flavor availability | cn-north-4 (widest flavor availability) |
| Business type | Required | Offline batch / streaming / interactive query / HBase / Kafka / mixed | N/A |
| Daily incremental data | Required | TB/day, pre-compression logical volume | N/A |
| Existing data + retention days | Required | Existing data TB + retention days; affects OBS capacity | N/A |
| Compression format and ratio | Required | ORC/Parquet/TextFile etc.; affects storage calculation | Estimated 0.5 with annotation |
| Data temperature distribution | Required | Hot/warm/cold data ratio | N/A |
| Business complexity | Required | Simple ETL / standard warehouse / complex compute; determines W_CPU coefficient | N/A |
| Job concurrency | Required | Concurrent job count | N/A |
| Compute window | Required | Hours/day available for compute | N/A |
| Real-time throughput | Conditional | MB/s; streaming scenarios only | N/A |
| Concurrent users | Conditional | Concurrent query users; OLAP scenarios only | N/A |
| Peak load description | Required | Whether load sustains >90% | No (no +20% buffer) |
| Business growth rate | Required | Annual/monthly growth rate | N/A |
| Storage mode | Required | OBS or local HDFS | N/A |
| Elastic Task requirement | Required | Whether elastic Task nodes needed | No |
| Streaming State size (A1) | Estimation | Streaming State size; medium State coefficient 6 | Default 6, annotated |
| Metadata file characteristics (A2) | Estimation | Files per TB | Default 500K/TB, annotated |
| Load sustains >90% (A3) | Estimation | Whether peak load sustains >90% | Default No, annotated |
| Hot data compute ratio (A4) | Estimation | 热数据参与计算比例；影响CPU/内存选型 | Default 100%, annotated |
| Estimation confirmation | Required | Phase 3 results must be confirmed by user before Phase 4 | N/A |
| Data retention and compression | Conditional | Affects OBS capacity 50%+ | Retention 180 days / compression 0.5, annotated |

## Notes

1. **MRS 3.x Master nodes** must have >= 64 GB RAM — hard requirement. Greenfield scenario does not enforce 128GB; select spec per algorithm result
2. **Master node count (greenfield scenario)**: Determined by planned Core total cores — <100 -> 3 nodes; >=100 -> 5 nodes; Core node count >500 -> 9-11 nodes
3. **Master vCPU selection rule (by Core node count)**: <=20 -> 16 cores, 20-50 -> 32 cores, >50 -> 64 cores. Memory by 6-step algorithm (minimum 64GB); only upgrade when algorithm value > spec memory
4. **Default ECS series**: aC9 (AMD General Computing-plus; official name AC9). Master and Core can use different flavors; Core nodes must be isomorphic. All flavors must come from the official MRS-supported ECS spec list (localized in the flavor catalog, source: support.huaweicloud.com/api-mrs/mrs_01_9006.html)
5. **Data disk formula**: 灵活计算，单盘600~800GB，Shuffle需求=vCPU×40GB；需求≤800GB用1块盘，需求是600倍数用600GB/块，否则减少盘数单盘≤800GB
6. **Resource estimation coefficients are experience-based**: All coefficients (vCPU·h/TB etc.) are industry experience estimates; must be annotated as "estimated value" in report
7. **Kerberos does not affect resource specs**: Only affects Master node count (OMS-separate scenario) and cluster security architecture; moved to Phase 2 as deployment config item
8. **OBS storage-compute separation**: Significantly reduces storage cost. OBS capacity = actual required storage (existing data + daily_increment × retention_days × compression_ratio); report the actual capacity directly, no package tier rounding
9. **Elastic Task algorithm (total buffer method)**: Total = estimated resources × (1 + buffer%); Core = estimated resources × daily load% (no buffer); Task = Total - Core (includes all buffer). Task on-demand billing: monthly fee = unit_price/730 × 1.2 × monthly running hours
10. **Buffer determination (estimation item A3)**: Greenfield scenario defaults to "No (no +20% buffer)"; only consider adding buffer when user explicitly describes "sustained peak"
11. **ZooKeeper** is auto-included. **DBService** dependencies are auto-configured
12. **Region handling**: Defaults to cn-north-4 (widest flavor availability) without asking user. Only verify ECS flavor availability when user explicitly specifies another region. Region coefficients are experience-based estimates
13. **Excel report (Phase 6)**: Must generate 4-sheet Excel file: Cluster Spec Recommendation / Resource Estimation Details / Selection Decision Rationale / OBS Storage Spec

## References

| Document | Description |
|----------|-------------|
| [Business-to-Resource Algorithm](references/business-to-resource-algorithm.md) | Business requirements -> resource estimation models (five load types, core of greenfield scenario) |
| [Component Mapping](references/component-mapping.md) | Component mapping table and cluster type matching rules |
| [ECS Flavor Catalog](references/ecs-flavor-catalog.md) | MRS-supported ECS flavor catalog (localized from official doc) and flavor selection matrix |
| [Master Sizing Algorithm](references/master-sizing-algorithm.md) | Master spec 6-step selection algorithm |
| [Core Sizing Algorithm](references/core-sizing-algorithm.md) | Core node selection algorithm |
| [Storage Disk Planning](references/storage-disk-planning.md) | Storage and disk planning |
| [Excel Report Template](references/excel-report-template.md) | Excel report template and data structure |
| [IAM Policies](references/iam-policies.md) | IAM permission requirements (no API permissions needed for this planning skill) |
| [Verification Methods](references/verification-method.md) | Output verification and validation methods |

## Code Structure

```text
scripts/
└── generate_mrs_report.py            # Excel report generation (4 sheets, single plan + estimation details)
references/
├── business-to-resource-algorithm.md # Business requirements -> resource estimation models (five load types)
├── component-mapping.md              # Component mapping table and cluster type matching rules
├── core-sizing-algorithm.md          # Core node selection algorithm (minimum redundancy + elastic Task)
├── ecs-flavor-catalog.md             # MRS-supported ECS flavor catalog (localized) and flavor selection matrix
├── excel-report-template.md          # Excel report template and report_data data structure
├── iam-policies.md                   # IAM permission requirements (no API permissions needed)
├── master-sizing-algorithm.md        # Master spec 6-step selection algorithm
├── storage-disk-planning.md          # Storage and disk planning (system/data disk, OBS capacity)
├── example-report-data.json          # Example report_data JSON for --input (demo/test only)
└── verification-method.md            # Output verification and validation methods
```

## Verification

- Execute `python scripts/generate_mrs_report.py --input <report_data.json>` to generate Excel report; confirm 4 sheets output (Cluster Spec Recommendation / Resource Estimation Details / Selection Decision Rationale / OBS Storage Spec)
- Verify recommended spec satisfies hard constraints: Master >= 64GB RAM, Core nodes isomorphic, node count meets HA requirements
- Verify redundancy rate between estimated resources and recommended spec (Total_excess = CPU_excess% + Mem_excess%) is minimum
- Confirm all estimated values are annotated with "estimated value" label

## Best Practices

- Phase 3 estimation results must be shown to user for confirmation first; do not skip estimation confirmation and proceed directly to spec selection
- Four estimation items (streaming State, metadata characteristics, load sustain rate, hot data compute ratio) should be recalibrated with monitoring data after 1-2 weeks of running
- OBS storage-compute separation can significantly reduce storage cost; prioritize recommendation when hot data ratio is low
- Data retention and compression coefficient affect OBS capacity by 50%+; must confirm with user
- Greenfield scenario does not enforce minimum 3 Core nodes; output per algorithm N value and annotate HA capability

## Edge Cases

- **No existing cluster benchmark**: Greenfield scenario has no existing cluster resource reference; resource targets are entirely derived from business load models; estimation coefficients are experience-based estimates that must be annotated
- **Master memory not enforced 128GB**: Greenfield scenario selects spec per 6-step algorithm result; algorithm <=64GB uses 64GB (satisfies MRS hard constraint); only upgrade when algorithm value > spec memory, avoiding over-provisioning
- **Estimation item recalibration**: Four estimation items (streaming State size, metadata file characteristics, load sustain rate, hot data compute ratio) estimated with experience defaults; recommend recalibrating with actual monitoring data after 1-2 weeks of running
- **Data retention and compression impact**: Data retention days and compression coefficient affect OBS capacity by 50%+; when not provided, estimate with retention 180 days / compression 0.5 and annotate
- **Core node count and HA capability**: N=1 no HA (test scenario only), N=2 has HA but Shuffle marginal (acceptable with OBS), N>=3 standard HA. Greenfield scenario does not enforce minimum 3 Core nodes
- **Estimation confirmation mechanism**: Phase 3 estimation results must be shown to user first (formula + coefficients + results + estimated value annotation); proceed to Phase 4 only after user confirms or corrects; skipping is prohibited
- **Mixed load summation**: Multiple load types are estimated per item then summed; peak off-peak can apply ×0.8 discount. Complexity coefficients: Simple ETL=20, Standard warehouse=40, Complex compute/ML=80 vCPU·h/TB
- **Region flavor availability**: Defaults to cn-north-4 (widest flavor availability) without asking. aC9 and other series are not available in all regions; only verify flavor availability when user explicitly specifies a non-default region
