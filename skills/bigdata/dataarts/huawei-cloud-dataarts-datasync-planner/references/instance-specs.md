# DataArts Studio Instance Spec Constraints (CDM / migration Resource Group)

> This document is referenced by SKILL.md and defines all specs, constraints, spec selection algorithms, survey question checklists, and solution output templates for batch integration instance packages (CDM) and integration resource group instance packages (migration).
> **Data Source**: Huawei Cloud official documentation (retrieved 2026-09-10)
> - Create batch data migration instance package: https://support.huaweicloud.com/usermanual-dataartsstudio/dataartsstudio_01_0119.html
> - Purchase data integration resource group instance package: https://support.huaweicloud.com/usermanual-dataartsstudio/dataartsstudio_01_0145.html

---

## 1. Batch Data Migration Instance Package (CDM Cluster) Specs

Used for **offline batch integration**. After creating an on-demand instance package, the system automatically creates a CDM cluster according to the selected spec; supports single-table, whole-database, incremental, and periodic data integration, and can also serve as an Agent proxy connected to the management center (providing network channel between DataArts Studio instance and data sources).

| Spec | CPU/Memory | Max Bandwidth/Base Bandwidth | Max Job Concurrency | Applicable Scenario |
|------|-----------|------------------------------|---------------------|---------------------|
| cdm.large | 8 cores / 16G | 3 / 0.8 Gbps | 16 | Regular-scale migration |
| cdm.xlarge | 16 cores / 32G | 10 / 4 Gbps | 32 | 10GE high-speed bandwidth TB-level+ migration |
| cdm.4xlarge | 64 cores / 128G | 40 / 36 Gbps | 128 | Large-scale concurrent migration |

**Constraints and Notes**:
- ⚠️ Some older/international-site documentation marks concurrency as 20/100/300; **the domestic-site current documentation (16/32/128) shall prevail**.
- DataArts Studio basic package includes one CDM cluster, but with limited spec, **only for testing/trial; production business must purchase instance package**.
- Job concurrency is the cluster limit (shared by all jobs); when planning multiple pipelines sharing a cluster, aggregate concurrency requirements.
- Base bandwidth is the sustained throughput guarantee; max bandwidth is peak; batch migration window estimation should conservatively use **base bandwidth**.
- Multiple offline pipelines can share one CDM cluster (multi-pipeline unified planning, see SKILL.md Notes 14).

## 2. Data Integration Resource Group Instance Package (migration, Real-time Jobs) Specs

Used for **real-time integration/real-time data warehousing** (single-table, whole-database, sharded-database, full+incremental, incremental sync). On-demand instance package automatically creates a resource group; specs are divided by **CU count**.

| Spec | CU Count | Max Job Count | High Availability | Notes |
|------|----------|---------------|-------------------|-------|
| Small | 16 CU | 7 | ❌ Not supported | Only for testing, **not recommended for production** |
| Medium | 64 CU | 32 | ✓ | Common production starting spec |
| Large | 96 CU | 48 | ✓ | — |
| Extra Large | 128 CU | 64 | ✓ | — |

**Hard Constraints (must be validated and explicitly annotated in solution)**:
- A single real-time job **requires a minimum of 2 CU**.
- A single job supports a maximum of **200 tables** — if a single task exceeds 200 tables, it must be split into multiple jobs, which in turn affects job count limit and spec tier.
- **Resource group spec cannot be modified after creation** — higher spec requires recreating; first selection should reserve growth margin.
- Network segment must **not overlap** with source/target network segments (otherwise peering connection fails); mask maximum **19 bits** (limited by CCE, 20+ bits not selectable).
- migration real-time jobs are currently only available in Beijing-4/Shanghai-1/Guangzhou and require whitelist application (see SKILL.md Notes).

## 3. Spec Selection Algorithm (Derived from Survey Data)

### 3.1 CDM Spec Selection (Offline)

```
Input: single batch max data volume V(GB), expected migration window T(hours), concurrent job count N, network bandwidth condition

Step1: Calculate required sustained throughput
  throughput_needed(Gbps) = V × 8 / (T × 3600) × redundancy_factor (recommended 1.5~2)
Step2: Validate bandwidth — select minimum spec with base_bandwidth >= throughput_needed
  (cdm.large base 0.8 / cdm.xlarge base 4 / cdm.4xlarge base 36 Gbps)
Step3: Validate concurrency — cluster job concurrency limit >= N (16/32/128)
Step4: Validate network — if cross-IDC via public internet/VPN, actual throughput capped by dedicated line bandwidth
  (e.g., dedicated line only 100Mbps ≈ 0.1Gbps, then cdm.large is sufficient, no need to upgrade spec for bandwidth)
Step5: Output spec
```

**Experience Reference** (conservative estimate with 1.5x redundancy):
| Single Batch Data Volume | 4-hour Window | 8-hour Window |
|--------------------------|---------------|---------------|
| ≤100GB | cdm.large | cdm.large |
| 100GB~500GB | cdm.large~xlarge | cdm.large |
| 500GB~2TB | cdm.xlarge | cdm.xlarge |
| >2TB or concurrency>32 | cdm.4xlarge | cdm.xlarge~4xlarge |

### 3.2 migration Resource Group Spec Selection (Real-time)

```
Input: real-time sync task count M, table count per task (max tables per task max_tables), HA requirement, growth reserve

Step1: Split validation — IF max_tables > 200: split tasks, M = ceil(table_count/200) aggregate
Step2: Validate job count limit — select minimum spec with job_limit >= M
  (Small 16CU/7 jobs, Medium 64CU/32 jobs, Large 96CU/48 jobs, Extra Large 128CU/64 jobs)
Step3: HA validation — IF HA required: exclude Small spec (no HA support)
Step4: Growth reserve — production environment recommended to go one tier higher (spec cannot be changed after creation)
Step5: Region validation — Beijing-4/Shanghai-1/Guangzhou + whitelist (see SKILL.md Notes)
Step6: Network segment validation — no overlap with source/target, mask <= 19 bits
```

### 3.3 Decision Examples

- 3 real-time pipelines, max 150 tables per task, HA required → Medium 64CU (32 jobs, HA supported)
- 50 sharded-database real-time tasks → Extra Large 128CU (64 jobs) or split into two resource groups
- Daily 2:00 batch 200GB, dedicated line 200Mbps, 8 jobs → cdm.large (base 0.8Gbps > dedicated line 0.2Gbps, concurrency 16 >= 8)

---

## 4. Survey Question Checklist (Phase 1 Supplement, Mandatory for Spec Derivation)

In addition to the SKILL.md Phase 1 basic survey items, supplement the following questions by integration mode for deriving instance package spec:

### Offline Pipeline (Deriving CDM Spec)
1. What is the **max single batch data volume** per batch schedule (GB/TB)? (Full initialization batch is usually much larger than daily incremental)
2. What is the **allowed migration window** for batch jobs (e.g., 0:00-6:00 AM)?
3. Estimated **concurrent job count** (concurrency)?
4. What is the **network bandwidth** from existing IDC to cloud (dedicated line/VPN bandwidth value)?
5. Is CDM needed as **Agent proxy** for network connectivity (management center connecting to data sources)?

### Real-time Pipeline (Deriving migration Resource Group Spec)
6. How many **real-time sync tasks** are needed (task count = job count)?
7. Does the **max table count** per real-time task exceed 200?
8. Do all sync tables have **primary keys** (migration only syncs tables with primary keys)?
9. Is **high availability** required (excludes Small spec)?
10. Is the deployment region Beijing-4/Shanghai-1/Guangzhou, and can whitelist application be accepted?

> If the user cannot answer, take conservative values per 3.1/3.2 experience reference and annotate assumptions in the solution.

---

## 5. Solution Output Template (Spec Section)

For each pipeline's Huawei Cloud-side solution, the "Configuration Recommendations/Spec Recommendations" must output the spec conclusion in the following format (example):

```
Spec Recommendation:
- Product: CDM (batch data migration instance package)
- Spec: cdm.xlarge (16 cores 32G, base bandwidth 4Gbps, concurrency limit 32)
- Selection Rationale: single batch 500GB/6-hour window → needs 0.3Gbps (with 1.5x redundancy) < 4Gbps base;
            concurrent jobs 12 < 32; dedicated line 1Gbps is actual limit constraint
```

```
Spec Recommendation:
- Product: migration (data integration resource group instance package)
- Spec: Medium 64CU (job limit 32, HA supported)
- Selection Rationale: 5 real-time tasks (max 180 tables per task < 200, no split needed); HA required → exclude Small;
            growth reserve → 64CU leaves 27 job margin
- Constraints: Beijing-4 region + whitelist; resource group network segment 172.16.0.0/19 (no overlap with source 10.x); spec cannot be changed after creation
```
