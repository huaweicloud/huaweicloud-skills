# Source MPP Cluster Survey Checklist (v2.4.0)

> Applicable scenarios: **Migration scenario** (competitor TD/GP/Doris → DWS), and **new-build scenario where the existing analytical workload is carried by an existing MPP cluster (e.g., Doris), and DWS will take over this workload** (in this case, deriving the target core count based on source-side workload equivalence is closer to reality than the "data volume/100GB" fallback).
> Purpose: ① Replace the target compute from the fallback formula with "source-side real workload equivalence derivation"; ② Verify the existing/daily increment/hot data caliber; ③ Provide a basis for architecture and cache policy values.
> This document is the full expansion of the Phase 1 "Source Cluster Survey Checklist" subsection. See SKILL.md for the main process.

---

## 1. Five Survey Groups (20 Questions)

### A. Data Scale and Increment (verify existing/daily increment caliber)

| # | Question | Corresponding DWS parameter | On-site remarks |
|---|------|--------------|---------|
| A1 | Is the existing data **logical data volume or physical occupancy including replicas**? (e.g., Doris defaults to 3 replicas) How large is each | Storage/cache calculation always uses **logical volume**; wrong caliber means the whole calculation is wrong | Can check `SHOW DATA` (Doris value includes replicas) / compare disk usage across BEs |
| A2 | How is the existing data distributed: number of databases/tables, proportion of Top large tables, ratio of detail tables vs summary (ADS) tables | Verify existing caliber, estimate migration workload | Focus on whether detail large tables can be trimmed (e.g., only migrate the last N years) |
| A3 | Confirm daily increment XX G/day: logical increment? From which import pipelines (real-time/batch)? Are there month-end/promotion **surges** (peak multiple) | Verify daily increment caliber; surges affect expansion pace and OBS package outlook | Distinguish logical/physical same as A1 |
| A4 | What is the source-side data compression ratio approximately? (e.g., Doris columnar storage compression is about 1:3~1:5 of original) | Indirectly validate the reasonable range of DWS storage estimation | Doris: `data_used/raw` per BE can be referenced |

### B. Compute Power and Resource Profile (core basis for equivalence-derived target core count)

| # | Question | Corresponding DWS parameter | On-site remarks |
|---|------|--------------|---------|
| B1 | Cluster topology: how many **BEs**? Per-unit specification (cores/memory)? **Total cores**? Is FE deployed independently | **Directly determines the equivalent target core count** | If there are multiple independent clusters, count the one whose workload will be taken over |
| B2 | BE node **CPU average/peak utilization**? (Key periods: morning reporting peak, end-of-month batch) | Equivalence conversion factor — cannot migrate total cores 1:1 when utilization is 30% | Can check monitoring/`SHOW BACKENDS` cpu field snapshots |
| B3 | Does CPU queuing/slowdown occur during peak? Is capacity currently loose or tight | Determine whether to add margin after equivalence | Loose → convert by peak utilization; tight → reserve 10~20% margin |
| B4 | Version? Is it **mixed-deployment/shared-cluster** (sharing BE with other workloads)? | If mixed, the dedicated core count for this workload needs conversion | When mixed, estimate the actual core usage of this workload |

### C. Query Workload and Concurrency (determines CPU memory ratio, whether compute-intensive, index reservation)

| # | Question | Corresponding DWS parameter | On-site remarks |
|---|------|--------------|---------|
| C1 | Query composition: proportions of **reporting (multi-table JOIN/aggregation) / ad-hoc analysis / point lookup** | More point lookups → index space +30%~50% | Doris wide-table JOINs are common → closer to DWS analytical workload |
| C2 | **Typical and peak concurrency** query counts (how many for BI reports + API services respectively) | Concurrency is the second check beyond core count | High peak concurrency but light single queries → core count can be less than total/100GB fallback |
| C3 | Is there **batch/ETL**? Running on source or downstream? Window duration | Whether "compute-intensive +30%, 1:8" | If ETL is handled by Flink/scheduling platform, DWS only handles analysis → no need to add |
| C4 | Proportion of large queries (full-table scans/long SQL)? Any query timeout/SLA requirements | Cache policy and high water level reference | Strict SLA → cache capacity at full (window/perf) |
| C5 | Source-side CPU memory ratio? (Doris BE commonly 1:8 or higher) How much is for **cache** (BE block cache etc.) | ⚠️ Do not copy directly — the bulk of memory is cache, DWS memory ratio is based on query profile | Reporting type usually 1:4 is sufficient |

### D. Hot Data and Lifecycle (verify "hot N days/common ratio" caliber)

| # | Question | Corresponding DWS parameter | On-site remarks |
|---|------|--------------|---------|
| D1 | How large is the hot data **frequently queried in the last N days** within the existing data? (e.g., proportion of partitions queried in the last 7 days) | Verify hot data volume/hot window days (window/custom mode) | Can use FE audit logs/slow query statistics to see the freshness of partitions hit by queries |
| D2 | Data retention/archival strategy: how long are partitions kept? Any auto eviction/hot-cold tiering | OBS long-term capacity outlook and package pace | Doris has no built-in hot-cold; can ask the business side about cleanup tasks |
| D3 | Do queries mainly land on "the last N days"? Is old data almost never queried | Verify hot window assumption (e.g., 7 days) | The larger N → the larger hot data → more local cache disk needed |

### E. Migration Scope and Future Planning

| # | Question | Corresponding DWS parameter | On-site remarks |
|---|------|--------------|---------|
| E1 | Is the source-side data **fully migrated to DWS** or only partial workloads/tables? Confirm other sources (business databases etc.) | Determine total warehouse data volume | Consistent with multi-source aggregation caliber for new-build scenarios |
| E2 | After migration, will the source be **decommissioned / dual-run / partial scenarios retained**? | Determines whether equivalent core count is fully taken over | Dual-run period doubles the load, needs assessment |
| E3 | Data/business growth expectations over the next 1~3 years (new data sources, business expansion) | Growth forecast and OBS package outlook reasonableness | |
| E4 | Downstream users: BI platform/report/API service user scale | Corroborates concurrency and core count | |

---

## 2. Three Caliber Pitfalls (must verify on-site)

1. **Logical volume vs physical volume including replicas**: Doris 9T if including 3 replicas then logical is about 3T, which may conflict with the "9T corresponds to 70G/day" profile — DWS storage/cache calculation always uses **logical data volume**, the caliber must be nailed down on-site.
2. **CPU utilization conversion**: Equivalent core count ≠ source-side total cores 1:1. When Doris utilization is only 20~30% normally, equivalent core count ≈ total cores × peak/average utilization, to avoid over-provisioning DWS (this is the same conversion logic as "ignore Flink specification first").
3. **Do not copy memory ratio**: Doris BE memory is largely allocated to cache (block cache, executor memory often 1:8 or higher), DWS determines memory ratio by **query profile**: reporting type 1:4, deep analysis/high concurrency memory-sensitive type 1:8.

---

## 3. Answers → Planning Parameter Mapping

| Survey answer | Consumption entry (engine/stage) |
|---------|----------------------|
| B1×B2 (source-side total cores × utilization conversion, can add margin per B3) | Phase 3 migration branch `competitor_cores` (equivalent core count); fallback when not surveyed = data volume/100GB |
| C5/load profile (reporting type vs deep analysis) | Phase 3 CPU memory ratio `ratio` (1:4 default / 1:8 compute-intensive +30%) |
| C1 (point lookup proportion) | Phase 5 index space `index_pct` (+30%~50%, default 30%) |
| A1/A3 (logical existing volume and daily increment) | `data_total_gb` / `daily_increment_gb` (storage and growth/OBS outlook) |
| D1/D2/D3 (hot window and retention) | `hot_data_days` (window) or converted `hot_data_gb` (custom, multi-source mixed) |
| E1 (warehouse scope) | Final caliber of total warehouse data volume (sum across sources, e.g., Doris 9T + business 5T) |

---

## 4. "Must-ask 8 items" when on-site time is limited

A1 (logical/physical caliber) → B1 (total cores and topology) → B2 (CPU utilization) → C2 (typical/peak concurrency) → C1 (query composition) → C5 (memory ratio and cache proportion) → D1 (hot data scale) → E1 (migration scope). Remaining questions can be supplemented by follow-up email/remote.
