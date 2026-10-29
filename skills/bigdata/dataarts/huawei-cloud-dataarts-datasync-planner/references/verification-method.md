# Verification - DataArts DataSync Planner

## Overview

This document defines verification and validation methods for the DataArts data sync planner output. After generating the sync plan and Excel report, verify the following criteria to ensure output correctness.

## 1. Excel Report Verification

Execute `python scripts/generate_datasync_report.py --input report.json` and verify the output Excel file contains the expected sheets. The report contains 3 sheets (Sheet 3 is generated on demand only when pipelines that cannot be directly matched exist):

| Sheet # | Sheet Name | Expected Content |
|---------|------------|------------------|
| 1 | 源端数据链路 (Source Data Pipelines) | All identified pipelines: id/name/source(type,version,deploy)/target(type,version,deploy)/sync mode/daily volume/frequency/latency/existing tool |
| 2 | 华为云侧同步链路 (Huawei Cloud Sync Pipelines) | Per pipeline: integration mode/scheme type/recommended product/pipeline topology/daily volume/config/constraints/alternative |
| 3 | 无法直接对标方案 (No-Direct-Match Solutions) | Conditionally generated: reason/Huawei Cloud feasible solution + topology/third-party solution + topology/pros-cons comparison |

Verification steps:

1. Open the generated `.xlsx` file and confirm Sheet 1 (源端数据链路) and Sheet 2 (华为云侧同步链路) always exist
2. Check Sheet 1 contains all user-provided pipelines with complete fields (source/target version + deploy + sync mode + daily volume + latency)
3. Check Sheet 2 shows Huawei Cloud solution per pipeline: integration mode, scheme type (color-coded), recommended product, topology, config, constraints, alternative
4. Check Sheet 3 (无法直接对标方案) is generated only when pipelines with `no_direct_match` data and scheme type ≠ "直接对标" exist; verify it contains reason, Huawei Cloud feasible solution, third-party solution, and pros-cons comparison
5. Verify scheme type color coding: 直接对标/Direct match → green, 华为云可行方案(间接)/Huawei Cloud feasible solution (indirect) → yellow, 三方软件方案/Third-party software solution → orange (script accepts both Chinese and English values)

## 2. Classification Verification

Verify each pipeline has completed real-time/offline classification:

| Criterion | Real-time | Offline |
|-----------|-----------|---------|
| Latency requirement | Seconds/milliseconds | Hours/days |
| Trigger mode | Event-driven | Scheduled |
| Sync mode | CDC/streaming | Full/incremental batch |

- Each pipeline must have a classification result with explicit rationale
- Minutes-level latency requires combining trigger mode for comprehensive judgment

## 3. Read/Write Matrix Validation

After product matching, verify read/write capability validation has been executed:

1. Confirm source data source read capability is supported by matched product
2. Confirm target data source write capability is supported by matched product
3. When not supported, verify alternative product is recommended with annotation
4. Verify source database exact version number is confirmed as feasibility basis

## 4. DWS Target Solution Verification

Verify DWS target solutions uniformly use DataArts Studio:

- Offline sync: uses CDM jobs or offline jobs (not DRS)
- Real-time sync: uses migration (not DRS)
- DRS is prohibited for DWS target (stopped sale 2025-08-31)

## 5. Instance Spec Verification

Verify instance spec conclusion is output for each solution:

| Product | Valid Specs | Selection Basis |
|---------|-------------|-----------------|
| CDM | cdm.large (8C16G) / xlarge (16C32G) / 4xlarge (64C128G) | Concurrency + table count |
| Migration | 16CU (7 jobs) / 64CU (32 jobs) / 96CU (48 jobs) / 128CU (64 jobs) | Job count + HA requirement |

- Spec cannot be changed after creation; verify selection rationale is documented
- Single job minimum 2CU, maximum 200 tables

## 6. Source Version Verification

Verify source database exact version number is confirmed:

1. Source data source type + exact version + deployment mode is collected
2. Version feasibility check is executed against read/write matrix
3. When version not supported, annotation and alternative recommendation are provided

## Verification Checklist Summary

- [ ] Excel report generated with all expected sheets
- [ ] Each pipeline has classification result with rationale
- [ ] Read/write matrix validation executed for all matched products
- [ ] DWS target solutions use DataArts Studio (not DRS)
- [ ] Instance spec conclusion output with selection rationale
- [ ] Source database exact version confirmed
- [ ] All constraint conditions annotated (Kerberos, decoupled storage, version requirements)