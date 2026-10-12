---
name: huawei-cloud-dws-spec-planner
description: |
  Huawei Cloud DWS data warehouse configuration planning and sizing. Supports coupled/decoupled architecture, outputs minimum-spec plan and multi-sheet Excel report.
  Automatically calculates CPU cores, storage capacity, and generates structured report.
  Applicable to DWS cluster planning, node spec selection, data warehouse migration, capacity planning, and scale-out scenarios.
  Trigger words: "DWS planning", "DWS sizing", "DWS cluster planning", "DWS node spec", "data warehouse migration to DWS", "DWS scale-out", "DWS capacity planning", "DWS规划", "DWS选型", "DWS集群规划", "DWS节点规格", "数据仓库迁移DWS", "存算一体", "存算分离", "DWS扩容", "DWS容量规划"
tags:
  - huawei-cloud
  - DWS
  - sizing
version: "2.5.1"
license: MIT
---

# Huawei Cloud DWS Data Warehouse Configuration Planning and Sizing

## Trigger Words

**Chinese triggers:** "DWS规划", "DWS选型", "DWS集群规划", "DWS节点规格", "数据仓库迁移DWS", "华为云DWS", "Data Warehouse Service", "DWS sizing", "存算一体", "存算分离", "日增数据量", "DWS扩容", "DWS容量规划"

**English triggers:** "DWS planning", "DWS sizing", "DWS cluster planning", "DWS node spec", "data warehouse migration to DWS", "Huawei Cloud DWS", "Data Warehouse Service", "coupled storage-compute", "decoupled storage-compute", "daily incremental data", "DWS scale-out", "DWS capacity planning"

## Overview

Based on migration or greenfield scenarios, configuration planning is performed for both coupled and decoupled storage-compute architecture modes. The skill outputs **one** minimum-spec plan that satisfies requirements (minimum compute surplus under constraints), along with storage growth reserve and scale-out cadence recommendations based on daily incremental data. Functional boundary: requirement survey -> architecture mode confirmation -> CPU core calculation -> minimum-spec flavor selection -> hot data storage/cache capacity calculation -> (optional) growth reserve and scale-out cadence -> report output -> Excel generation.

Security rule: Specifications are sourced from Huawei Cloud official document dws_01_00018 (updated 2026-07-31). Scripts must be executed via skill action=exec; direct shell execution is prohibited.

## Prerequisites

- Python3 + openpyxl (`pip install openpyxl`)


## Workflow

### Phase 1: Requirement Survey

Collect the following key information (8 required + 2 optional):

| Category | Survey Item | Description |
|----------|------------|-------------|
| Scenario type | Migration / Greenfield | Determines CPU core calculation method |
| Data volume | Total data to warehouse (GB/TB) | Basis for CPU core and storage capacity calculation |
| Daily incremental (optional) | Daily average new data (GB/day) | Storage growth reserve and scale-out cadence; **does not change node spec** |
| Retention period (optional) | Retention cycle (months) | Growth prediction enabled only when daily incremental is also provided |
| Competitor info | Competitor CPU total, memory ratio | Migration scenario only; matching configuration |
| Source cluster survey (v2.4.0) | MPP cluster scale and utilization (5 groups, 20 questions) | Calibrate matching cores and hot data criteria when migrating or taking over source workload |
| Workload | Compute-intensive or not | Greenfield scenario +30% cores |
| Query characteristics | Many point queries or not | Index space +30%~50% |
| Architecture mode | Coupled / Decoupled | Determines storage calculation method and high watermark |
| Cache strategy | Cost-optimized / Performance-optimized / Hot window N days / Custom hot data volume | Decoupled only (v2.3.0) |
| Deployment region | Target region | Flavor availability |

> Source cluster survey checklist: [references/source-cluster-survey.md](references/source-cluster-survey.md)

### Phase 2: Architecture Mode Confirmation

| Architecture | Applicable Scenario | High Watermark | Cache Strategy |
|-------------|---------------------|----------------|----------------|
| Coupled | <20TB, high performance | 70% | N/A (all data on local SSD) |
| Decoupled | >=20TB or low hot data ratio / fast growth | 80% | Cost-optimized 50% / Performance-optimized 100% / Hot window N days / Custom (v2.3.0) |

> Storage calculation rules: [references/storage-calculation.md](references/storage-calculation.md)

### Phase 3: CPU Core Calculation

- **Migration scenario**: Total CPU = competitor CPU total (matching configuration); memory ratio follows competitor; when competitor cores not provided, fallback to **ceil(data volume/100GB)**
- **Greenfield scenario**: Base cores = **ceil(total warehouse data/100GB)**; compute-intensive x1.3 (memory ratio 1:8), otherwise 1:4
- **Both decoupled and coupled use total warehouse data for CPU derivation** (v2.5.1); cache ratio only affects storage/cache capacity allocation, not CPU cores
- Constraints: single node >=16vCPU/64GB, node count >=3 (high availability)
- Daily incremental data **does not participate** in CPU/node derivation; only used for Phase 5 growth reserve

> Full CPU calculation logic: [references/cpu-sizing-algorithm.md](references/cpu-sizing-algorithm.md)

### Phase 4: Node Flavor Planning (Single Minimum-Spec Plan)

Iterate through DWS dedicated flavor catalog (dwsx2/dwsx3/dwsax3 series), satisfying hard constraints (>=16 cores/>=64GB/>=3 nodes), select the combination with **minimum compute surplus** (nodes + storage). Selection rationale is auto-generated via four-step formula chain: (1) compute derivation -> (2) memory ratio -> (3) concurrency/HA -> (4) storage verification.

> Flavor catalog: [references/ecs-flavor-catalog.md](references/ecs-flavor-catalog.md)
> Selection algorithm: [references/single-plan-algorithm.md](references/single-plan-algorithm.md)

### Phase 5: Storage Capacity Calculation and Growth Reserve

1. **Storage capacity** (based on current warehouse volume):
   - Coupled: Effective capacity = total / high watermark (70%); many point queries x(1+index%); per node = ceil(total/nodes, round up to 100GB)
   - Decoupled: Hot data calculated by cache policy -> effective cache = hot data / high watermark (80%) -> same as above
   - Cache policy priority: custom (custom hot data volume) > window (hot window N days) > cost/performance (50%/100%)

2. **Growth reserve** (optional, requires both daily incremental + retention period):
   - Planning period new data = daily incremental x 30 days/month x retention months; end-of-period total = current + new
   - Scale-out line (90% utilization) capacity -> net growth headroom -> estimated scale-out time point
   - Growth prediction **does not change recommended spec**; only outputs scale-out recommendations

> Growth calculation and Excel template: [references/excel-report-template.md](references/excel-report-template.md)

### Phase 6: Report Output

Generate structured Markdown report + 5-sheet Excel report:

| Sheet | Name | Content |
|-------|------|---------|
| 1 | Config Recommendation Overview | Single plan summary + detailed spec |
| 2 | Resource and Storage Calculation | CPU derivation + storage capacity calculation process |
| 3 | Selection Decision Rationale | Decision points + candidate flavor comparison table |
| 4 | Capacity Growth and Scale-out Recommendations | Daily incremental x retention period -> scale-out time point |
| 5 | Decoupled OBS Spec | OBS capacity calculation |

> Common scenarios: [references/sizing-scenarios.md](references/sizing-scenarios.md)

## Output Rules

- Output only **one plan** (minimum spec satisfying requirements, minimum compute surplus); no Plan A/B comparison
- CPU/nodes derived from current warehouse volume; daily incremental does not inflate initial spec (minimum spec philosophy)
- Both decoupled and coupled CPU calculated from total warehouse data (v2.5.1); cache ratio only affects storage/cache capacity allocation
- Missing info handled with defaults but must be annotated (e.g., index space default +30%, cache strategy default performance-optimized 100%)
- Excel report must generate 5 sheets; when daily incremental and retention period not provided, Sheet 4 outputs N/A
- Key decision points must be proactively asked: scenario type, data volume, competitor CPU/memory ratio, compute-intensive, point queries, architecture mode, cache strategy, deployment region

## Core Commands


### Report Generation

```bash
python scripts/generate_dws_report.py
```

File naming: `DWS_Sizing_Report_<YYYYMMDD>.xlsx`

## Parameter Confirmation

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| Scenario type | Required | Migration / Greenfield; determines CPU core calculation method | N/A |
| Total warehouse data | Required | GB/TB; basis for CPU core and storage capacity calculation | N/A |
| Competitor CPU total and memory ratio | Conditional | Migration scenario only; matching configuration; fallback to ceil(data/100GB) when not provided | Uses fallback formula when not provided |
| Source cluster survey | Conditional | Calibrate matching cores and hot data caliber when migrating | N/A |
| Workload | Required | Compute-intensive or not; greenfield compute-intensive x1.3 | Non-compute-intensive |
| Query characteristics | Required | Many point queries or not; index space +30%~50% | Default +30% with annotation |
| Architecture mode | Required | Coupled / Decoupled; determines storage calculation and high watermark | N/A |
| Cache strategy | Conditional | Decoupled only; cost-optimized 50% / performance-optimized 100% / hot window N days / custom hot data volume | Performance-optimized 100% |
| Deployment region | Required | Target region | N/A |
| Daily incremental data | Optional | Daily new data GB/day; for storage growth reserve and scale-out cadence only; does not change node spec | N/A |
| Data retention period | Optional | Retention cycle (months); growth prediction enabled only when daily incremental also provided | N/A |

## Notes

1. **Production single node** >= 16vCPU and >= 64GB (hard requirement); **node count >= 3** (high availability)
2. **DWS != general ECS**: Uses dedicated flavor names (dwsx2/dwsx3/dwsax3 etc.); cannot use MRS aC9/ac7
3. **Migration scenario cores**: Match competitor cores; no hard >=96 floor; when competitor cores not provided, fallback to **ceil(data volume/100GB)**
4. **CPU-memory ratio**: Migration follows competitor; greenfield non-compute-intensive -> 1:4, compute-intensive -> 1:8
5. **CPU derived from current warehouse volume**: Daily incremental does not inflate initial spec; both decoupled and coupled use total warehouse data (v2.5.1); cache ratio does not affect CPU
6. **Coupled high watermark 70%** (SSS cloud disk), **decoupled high watermark 80%** (local cache disk)
7. **Index space**: Many point queries +30%~50%; default +30% with annotation
8. **Cache policy (v2.3.0)**: cost -> total x50%, performance -> total x100% (default), window -> min(daily incremental x N, total), custom -> given value (<= total)
9. **Storage/cache capacity**: Configured disk size = actual usable capacity; no replica space reservation needed
10. **Source survey caliber (v2.4.0)**: (1) Distinguish logical volume vs physical volume with replicas (Doris default 3 replicas); (2) Matching cores calculated from source CPU utilization; (3) Memory ratio based on DWS query profile, not copied from source

## References

| Document | Description |
|----------|-------------|
| [Acceptance Criteria](references/acceptance-criteria.md) | Spec output acceptance criteria |
| [CPU Sizing Algorithm](references/cpu-sizing-algorithm.md) | CPU core calculation algorithm (migration/greenfield) |
| [ECS Flavor Catalog](references/ecs-flavor-catalog.md) | DWS dedicated flavor catalog (dwsx2/dwsx3/dwsax3 series 1:4/1:8) |
| [IAM Policies](references/iam-policies.md) | IAM permission requirements (no API permissions needed for this planning skill) |
| [Single Plan Algorithm](references/single-plan-algorithm.md) | Single-plan minimum-spec selection algorithm and candidate comparison |
| [Storage Calculation](references/storage-calculation.md) | Storage capacity calculation (coupled/decoupled, high watermark, index space) |
| [Excel Report Template](references/excel-report-template.md) | Excel report template and report_data data structure |
| [Sizing Scenarios](references/sizing-scenarios.md) | Common planning scenarios (Scenario A-F, with daily incremental growth examples) |
| [Source Cluster Survey](references/source-cluster-survey.md) | Source cluster survey checklist (5 groups, 20 items, v2.4.0) |
| [Verification Methods](references/verification-method.md) | Output verification and validation methods |

## Code Structure

```text
scripts/
└── generate_dws_report.py          # Excel report generation (5 sheets, single plan + growth analysis)
references/
├── acceptance-criteria.md          # Spec output acceptance criteria
├── cpu-sizing-algorithm.md         # CPU core calculation algorithm (migration/greenfield)
├── ecs-flavor-catalog.md           # DWS dedicated flavor catalog (dwsx2/dwsx3/dwsax3 series 1:4/1:8)
├── excel-report-template.md        # Excel report template and report_data data structure
├── iam-policies.md                 # IAM permission requirements (no API permissions needed)
├── single-plan-algorithm.md        # Single-plan minimum-spec selection algorithm and candidate comparison
├── sizing-scenarios.md             # Common planning scenarios (Scenario A-F, with daily incremental growth examples)
├── source-cluster-survey.md        # Source cluster survey checklist (5 groups, 20 items, v2.4.0)
├── storage-calculation.md          # Storage capacity calculation (coupled/decoupled, high watermark, index space)
└── verification-method.md          # Output verification and validation methods
```

## Verification

- Execute `python scripts/generate_dws_report.py` to generate Excel report; confirm 5 sheets output (Config Recommendation Overview / Resource and Storage Calculation / Selection Decision Rationale / Capacity Growth and Scale-out Recommendations / Decoupled OBS Spec)
- Verify recommended spec satisfies hard constraints: single node >= 16vCPU and >= 64GB, node count >= 3
- Verify decoupled scenario CPU calculated from total warehouse data (same as coupled); cache ratio adjustment does not affect CPU cores
- Confirm daily incremental data does not inflate initial spec (only used for Phase 5 growth reserve)

## Best Practices

- DWS uses dedicated flavor names (dwsx2/dwsx3/dwsax3); cannot use MRS aC9/ac7 general-purpose ECS flavors
- Decoupled suitable for >=20TB or low hot data ratio / fast growth scenarios; coupled suitable for <20TB high-performance scenarios
- Cache policy priority: custom > window > cost/performance; select based on business hot data characteristics
- Source survey distinguishes logical volume vs physical volume with replicas (Doris default 3 replicas); matching cores calculated from CPU utilization
- Daily incremental data does not change node spec; only affects scale-out cadence recommendations

## Edge Cases

- **DWS dedicated flavors**: DWS uses dedicated PaaS flavor names (dwsx2/dwsx3/dwsax3 etc.); cannot use general-purpose ECS flavors (e.g., MRS aC9/ac7); must confirm target region DWS flavor availability before sizing
- **Architecture switch**: Decoupled suitable for >=20TB or low hot data ratio / fast growth; coupled suitable for <20TB high performance. When switching architecture, CPU calculation caliber unchanged (both use total warehouse data); only storage/cache capacity calculation changes (total -> hot data volume)
- **Daily incremental boundary**: Daily incremental does not participate in CPU/node derivation; only used for Phase 5 growth reserve and scale-out cadence. When daily incremental + retention period not provided, Sheet 4 outputs N/A
- **Missing info handling**: Missing info handled with defaults but must be annotated (index space default +30%, cache strategy default performance-optimized 100%); silent use of defaults is not allowed
- **Source survey caliber distinction**: Migration scenario must distinguish logical volume vs physical volume with replicas (e.g., Doris default 3 replicas); matching cores calculated from source CPU utilization; memory ratio based on DWS query profile, not copied from source
- **Cache policy priority conflict**: custom > window > cost/performance; when multiple strategies provided, use by priority; explain actual effective strategy to user
- **Very small data volume**: When data <100GB, fallback to **ceil(data/100GB)** = 1 core; but constrained by single node >=16vCPU hard requirement; actual minimum spec is 16 cores
