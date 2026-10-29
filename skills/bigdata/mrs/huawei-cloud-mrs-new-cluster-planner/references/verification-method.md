# Verification - MRS New Cluster Planner

## Overview

This document defines verification and validation methods for the MRS new cluster planner output. This skill handles greenfield scenarios with no existing cluster benchmark; resource targets are derived from business load models. After generating the cluster plan and Excel report, verify the following criteria to ensure output correctness.

## 1. Excel Report Verification

Execute `python scripts/generate_mrs_report.py` and verify the output Excel file contains 4 sheets:

| Sheet # | Sheet Name | Expected Content |
|---------|------------|------------------|
| 1 | Cluster Spec Recommendation | Recommended MRS cluster config (Master/Core/Task specs) |
| 2 | Resource Estimation Details | Business load model + estimation formulas + coefficients + results |
| 3 | Selection Decision Rationale | Decision points + candidate flavor comparison + selection reasoning |
| 4 | OBS Storage Spec | OBS capacity calculation (actual required storage, no package tier; for decoupled storage-compute) |

Verification steps:

1. Open the generated `.xlsx` file and confirm 4 sheets exist
2. Check Sheet 1 contains single plan with Master/Core/Task node specs
3. Check Sheet 2 shows estimation formulas, coefficients, and results with "estimated value" annotations
4. Check Sheet 3 shows selection rationale for each node flavor
5. Check Sheet 4: if decoupled storage-compute, verify OBS spec; if coupled, verify N/A or not applicable

## 2. Hard Constraint Verification

After generating the plan, confirm the recommended spec satisfies all hard constraints:

| Constraint | Requirement | Verification Method |
|------------|-------------|---------------------|
| Master memory | >= 64GB (MRS 3.x) | Check recommended Master flavor spec |
| Core node isomorphic | All Core nodes same flavor | Verify Core flavor list has single entry |
| Node count (HA) | N=1 no HA (test only), N=2 HA with marginal Shuffle, N>=3 standard HA | Check node count in the plan |
| Master node count | Per 6-step algorithm result | Verify Master count matches algorithm output |

Note: Greenfield scenario does not enforce minimum 3 Core nodes; output per algorithm N value and annotate HA capability.

## 3. Redundancy Rate Verification

Verify the redundancy rate between estimated resources and recommended spec is minimized:

1. For each candidate flavor, calculate N = max(ceil(V/flavor_vCPU), ceil(M/flavor_memory))
2. Calculate Total_excess = CPU_excess% + Mem_excess%
3. Verify the selected flavor has the minimum Total_excess
4. On tie, verify fewer nodes is selected
5. Verify single plan output (no dual-plan comparison)

## 4. Estimation Annotation Verification

Verify all estimated values are annotated with "estimated value" label:

| Estimation Item | Default | Annotation Required |
|-----------------|---------|---------------------|
| Streaming State size | Experience-based estimate | Yes, in Sheet 2 |
| Metadata file characteristics | Experience-based estimate | Yes, in Sheet 2 |
| Load sustain rate | Experience-based estimate | Yes, in Sheet 2 |
| Data retention days | 180 days | Yes, when not user-provided |
| Compression coefficient | 0.5 | Yes, when not user-provided |
| Region coefficients | Experience-based estimates | Yes, in Sheet 2 |

Silent use of estimates is not allowed; all estimated values must be visible in the report.

## 5. Estimation Confirmation Verification

Verify Phase 3 estimation results were shown to user for confirmation:

1. Estimation formulas + coefficients + results + "estimated value" annotation are displayed
2. User confirmation or correction is obtained before proceeding to Phase 4
3. Skipping estimation confirmation is prohibited
4. Three estimation items (streaming State, metadata characteristics, load sustain rate) should be recalibrated with monitoring data after 1-2 weeks of running

## 6. Elastic Task Verification

When elastic Task nodes are used, verify:

1. Total buffer method is applied: Total = estimated resources x (1 + buffer%)
2. Core = estimated resources x daily load% (no buffer applied to Core)
3. Task = Total - Core (includes all buffer)
4. Buffer only added when user describes "sustained peak" (estimation item A3)
5. Greenfield scenario defaults to "No (no +20% buffer)"
6. Task on-demand billing: monthly fee = unit_price/730 x 1.2 x monthly running hours

## Verification Checklist Summary

- [ ] Excel report has 4 sheets with correct content
- [ ] Master >= 64GB RAM hard constraint satisfied
- [ ] Core nodes isomorphic (single flavor)
- [ ] Node count matches HA requirements (with annotation for N<3)
- [ ] Redundancy rate (Total_excess) is minimum
- [ ] All estimated values annotated with "estimated value" label
- [ ] Phase 3 estimation confirmation executed (not skipped)
- [ ] Elastic Task buffer applied to total, not Core
- [ ] Region ECS flavor availability verified
- [ ] Single plan output (minimum redundancy, no dual-plan)