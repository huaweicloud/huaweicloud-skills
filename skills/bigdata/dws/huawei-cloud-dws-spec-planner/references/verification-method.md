# Verification - DWS Spec Planner

## Overview

This document defines verification and validation methods for the DWS spec planner output. After generating the sizing plan and Excel report, verify the following criteria to ensure output correctness.

## 1. Hard Constraint Verification

After generating the sizing plan, confirm the recommended spec satisfies all hard constraints:

| Constraint | Requirement | Verification Method |
|------------|-------------|---------------------|
| Single node vCPU | >= 16 | Check recommended flavor spec in flavor catalog |
| Single node memory | >= 64GB | Check recommended flavor spec in flavor catalog |
| Node count | >= 3 | Check recommended node count in the plan |
| HA requirement | >= 3 nodes | Verify node count satisfies high availability |

## 2. Excel Report Verification

Execute `python scripts/generate_dws_report.py` and verify the output Excel file contains 5 sheets:

| Sheet # | Sheet Name | Expected Content |
|---------|------------|------------------|
| 1 | Config Recommendation Overview | Single plan summary + detailed spec |
| 2 | Resource and Storage Calculation | CPU derivation + storage capacity calculation process |
| 3 | Selection Decision Rationale | Decision points + candidate flavor comparison table |
| 4 | Capacity Growth and Scale-out Recommendations | Daily incremental x retention period -> scale-out time point (N/A if not provided) |
| 5 | Decoupled OBS Spec | OBS capacity calculation |

Verification steps:

1. Open the generated `.xlsx` file and confirm 5 sheets exist
2. Check Sheet 1 contains a single recommended plan (not multiple plans)
3. Check Sheet 2 shows CPU derivation formula and storage calculation steps
4. Check Sheet 3 includes candidate comparison table with selection rationale
5. Check Sheet 4: if daily incremental + retention period provided, verify scale-out time point; otherwise verify N/A is shown
6. Check Sheet 5: if decoupled architecture, verify OBS spec; if coupled, verify N/A or not applicable

## 3. Architecture-Specific Verification

### Coupled Architecture

- Verify CPU cores calculated from total warehouse data (not hot data volume)
- Verify high watermark = 70% (SSS cloud disk)
- Verify storage capacity = total data / 0.7 (adjusted for index space if applicable)

### Decoupled Architecture

- Verify CPU cores calculated from total warehouse data (same as coupled, v2.5.1)
- Verify cache ratio does NOT affect CPU cores (only affects storage/cache allocation)
- Verify high watermark = 80% (local cache disk)
- Verify cache policy priority: custom > window > cost/performance

## 4. Growth Reserve Verification

When daily incremental data and retention period are both provided:

1. Verify planning period new data = daily incremental x 30 days/month x retention months
2. Verify end-of-period total = current data + new data
3. Verify scale-out line (90% utilization) capacity is calculated correctly
4. Verify growth prediction does NOT change the recommended spec (only outputs scale-out recommendations)

## 5. Default Value Annotation Verification

When missing info is handled with defaults, verify each default is explicitly annotated in the report:

| Missing Info | Default | Annotation Required |
|--------------|---------|---------------------|
| Index space | +30% | Yes, in Sheet 2 |
| Cache strategy | Performance-optimized 100% | Yes, in Sheet 2 |
| Memory ratio (greenfield) | 1:4 (non-compute-intensive) | Yes, in Sheet 2 |

Silent use of defaults is not allowed; all defaults must be visible in the report.

## 6. Source Cluster Survey Verification (Migration Scenario)

When migrating from an existing cluster, verify:

1. Logical volume vs physical volume distinction (with replicas, e.g., Doris default 3 replicas)
2. Matching cores calculated from source CPU utilization (not raw total)
3. Memory ratio based on DWS query profile (not copied from source)
4. Source survey checklist completed (5 groups, 20 items, v2.4.0)

## Verification Checklist Summary

- [ ] Hard constraints satisfied (>= 16vCPU, >= 64GB, >= 3 nodes)
- [ ] Excel report has 5 sheets with correct content
- [ ] CPU calculated from total warehouse data (both architectures)
- [ ] Cache ratio does not affect CPU (decoupled only)
- [ ] Growth reserve does not change initial spec
- [ ] All default values annotated in report
- [ ] Source survey caliber correct (migration scenario)
