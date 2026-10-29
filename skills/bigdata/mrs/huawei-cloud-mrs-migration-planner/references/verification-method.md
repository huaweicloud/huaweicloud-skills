# Verification - MRS Migration Planner

## Overview

This document defines verification and validation methods for the MRS migration planner output. After generating the migration plan and Excel report, verify the following criteria to ensure output correctness.

## 1. Excel Report Verification

Execute `python scripts/generate_mrs_report.py` and verify the output Excel file contains 4 sheets:

| Sheet # | Sheet Name | Expected Content |
|---------|------------|------------------|
| 1 | Cluster Spec Recommendation | Recommended MRS cluster config (Master/Core/Task specs) |
| 2 | Resource Comparison | Original cluster vs MRS recommended config with difference values |
| 3 | Selection Decision Rationale | Decision points + candidate flavor comparison + selection reasoning |
| 4 | OBS Storage Spec | OBS capacity calculation (actual required storage, for decoupled storage-compute) |

Verification steps:

1. Open the generated `.xlsx` file and confirm 4 sheets exist
2. Check Sheet 1 contains single plan with Master/Core/Task node specs
3. Check Sheet 2 includes resource comparison table with difference values and growth percentages
4. Check Sheet 3 shows selection rationale for each node flavor
5. Check Sheet 4: if decoupled storage-compute, verify OBS spec; if coupled, verify N/A or not applicable

## 2. Hard Constraint Verification

After generating the plan, confirm the recommended spec satisfies all hard constraints:

| Constraint | Requirement | Verification Method |
|------------|-------------|---------------------|
| Master memory | >= 64GB (MRS 3.x) | Check recommended Master flavor spec |
| Core node uniformity | All Core nodes same flavor | Verify Core flavor list has single entry |
| Node count (HA) | >= 3 Master nodes | Check Master node count in the plan |
| Master node count | < 100 cores -> 3; >= 100 -> 5-11; > 500 Core -> 9-11 | Verify Master count matches cluster scale |

## 3. Resource Comparison Verification

Verify the resource comparison table is complete:

1. Original cluster config (CPU/memory/node count) is listed
2. MRS recommended config is listed
3. Difference values (absolute and percentage) are calculated correctly
4. Growth percentages are accurate

## 4. Migration Scenario Verification

For migration scenarios, verify Master utilization check has been executed:

1. Q14 is asked: original cluster Master node CPU/memory utilization
2. When MRS planned total memory < original cluster actual usage (total x utilization), verify "memory severely insufficient" annotation is present
3. Verify flavor upgrade recommendation is provided when memory insufficient
4. Verify Sheet 1 column O "Q14 Check (Master utilization)" is populated on the Master row (not only in the decisions table), and that it states either pass or the specific violated conditions
5. Verify `source_cluster` of `report.json` carries `node_count`, `master_node_count`, `master_node_memory_gb`, `master_node_vcpu`, `master_mem_utilization_pct`, `master_cpu_utilization_pct`

## 5. Single Plan Verification

Verify only one final plan is output (single-plan principle):

1. Excel report contains a single recommended plan (not multiple plans)
2. Minimum surplus selection: Total_excess = CPU_excess% + Mem_excess% is minimized
3. On tie, fewer nodes is selected
4. No dual-plan comparison or user selection required

## 6. Elastic Task Verification

When elastic Task nodes are used, verify:

1. The off-peak (non-peak) daily load is explicitly asked of the user (not silently derived from the task window)
2. Total buffer method is applied: Total = original x (1 + buffer%)
3. Core = original x off-peak daily load% (no buffer applied to Core); Core is sized for the off-peak daily load
4. Task = Total - Core (includes all buffer); peak demand is covered by elastic Task nodes
5. Buffer only added when user confirms "peak resources continuously saturated (>90%)"
6. Common error check: Core != total x load% x (1 + buffer%) — buffer must not be applied to Core

## 7. Data Volume, Disk and OBS Verification

1. Confirm the investigation asked for daily incremental data and data retention period
2. Confirm the full data volume = existing data + daily incremental data × retention period, and that sizing uses this full data volume
3. Confirm the shuffle disk is planned flexibly: per-node requirement = vCPU × 40GB, each disk within 600-800GB (640GB -> 1×640GB, 1400GB -> 2×700GB, 2400GB -> 4×600GB)
4. Confirm total shuffle = per-node disk total (disk size × disk count) × node count
5. Confirm OBS capacity is reported as the actual required storage (single-replica); no package tier rounding

## 8. Region ECS Flavor Availability Verification

This skill makes **no API calls** (see iam-policies.md — zero permissions required), so flavor availability cannot be checked programmatically. Verify it manually before delivering the report:

1. **Huawei Cloud console**: ECS -> Buy ECS -> select the target region -> search the recommended flavor (e.g. `ac9.8xlarge.4`); unavailable flavors do not appear in the region's flavor list
2. **hcloud CLI** (optional): `hcloud ECS ListFlavors --cli-region=<region>` and confirm the flavor name is present
3. **Dimensions to confirm per flavor**: availability in the target region, availability in the target AZ, and quota headroom for the planned node count
4. **If a recommended flavor is unavailable**: switch to the next tier in the same series, or to the alternate series in ecs-flavor-catalog.md §5, then recompute Total_excess
5. **If availability cannot be confirmed by the user**: keep the recommendation but annotate the report with "flavor availability to be confirmed in <region> before purchase"

The prices in ecs-flavor-catalog.md are baseline prices for North Beijing-4; prices in other regions differ and must be re-quoted.

## Verification Checklist Summary

- [ ] Excel report has 4 sheets with correct content
- [ ] Master >= 64GB RAM hard constraint satisfied
- [ ] Core nodes uniform (single flavor)
- [ ] Master node count matches cluster scale rules
- [ ] Resource comparison table complete with difference values
- [ ] Migration scenario Master utilization check executed (Q14) and Sheet 1 column O populated on the Master row
- [ ] Single plan output (minimum surplus, no dual-plan)
- [ ] Off-peak daily load explicitly asked (when elastic Task enabled) and used to size Core
- [ ] Elastic Task buffer applied to total, not Core
- [ ] Daily incremental data and data retention period asked; sizing based on full data volume
- [ ] Shuffle disks planned flexibly within 600-800GB per disk
- [ ] Total shuffle = per-node disk total × node count
- [ ] OBS capacity = actual required storage (single-replica), no package tier
- [ ] Region ECS flavor availability verified manually (see §8; console or hcloud CLI)