# Acceptance Criteria

## Overview
This document defines the quality standards and acceptance criteria for the alarm-bind-inspection skill. All criteria must be met before the skill is considered production-ready.

## Functional Acceptance Criteria

### 1. Excel Parsing

| Criterion | Description | Verification |
|-----------|-------------|--------------|
| AC-1.1 | `关键资源标记表.xlsx` is correctly parsed | `core_instances.json` contains instances with `region`, `resource_type`, `resource_id` fields |
| AC-1.2 | Only rows with `是否核心业务` = `是` are extracted | No non-core instances in output |
| AC-1.3 | `华为云租户面监控告警基线-V26.01-beta.xlsx` is correctly parsed | 4 baseline JSON files generated with expected record counts |
| AC-1.4 | CES metric baseline filters `指标级别=底线指标` | No non-baseline metrics in `indicator_baseline.json` |
| AC-1.5 | CES event baseline filters `事件级别=底线事件` | No non-baseline events in `event_baseline.json` |
| AC-1.6 | AOM baselines extracted from 4 sheets | `aom_indicator_baseline.json` and `aom_event_baseline.json` non-empty |

### 2. CES Alarm Rule Fetch

| Criterion | Description | Verification |
|-----------|-------------|--------------|
| AC-2.1 | CES SDK authenticates with AK/SK | No auth errors in `main_alarm.py` output |
| AC-2.2 | Alarm rules fetched for all regions in `core_instances.json` | Rules tagged with multiple `region` values |
| AC-2.3 | Each rule has resource dimensions and policy metrics | `resources[].dimensions` and `policies[].metric_name` present |
| AC-2.4 | Project ID auto-fetched via hcloud | No manual Project ID configuration required |

### 3. AOM Alarm Rule Fetch

| Criterion | Description | Verification |
|-----------|-------------|--------------|
| AC-3.1 | AOM metric alarm rules fetched | `aom_alarm_rules.json` non-empty |
| AC-3.2 | AOM event alarm rules fetched | `aom_event_alarm_rules.json` non-empty |
| AC-3.3 | Multi-region supported | Rules from multiple regions present |

### 4. Binding Analysis

| Criterion | Description | Verification |
|-----------|-------------|--------------|
| AC-4.1 | CES metric binding rates calculated | `indicator_bind_report.json` contains per-instance binding rates |
| AC-4.2 | CES event binding rates calculated | `event_bind_report.json` contains per-instance binding rates |
| AC-4.3 | AOM metric binding rates calculated | `aom_indicator_bind_report.json` non-empty |
| AC-4.4 | AOM event binding rates calculated | `aom_event_bind_report.json` non-empty |
| AC-4.5 | Binding rates are 0-100% | All rate values in [0, 100] range |
| AC-4.6 | Wildcard rules cover all instances | Instances without explicit rules show wildcard coverage |
| AC-4.7 | Dimension subset matching works | Instance with `dcs_instance_id,dcs_cluster_redis_node` matches baseline `dcs_instance_id` |

### 5. Report Generation

| Criterion | Description | Verification |
|-----------|-------------|--------------|
| AC-5.1 | Metric Excel report generated | `indicator_bind_report.xlsx` exists and opens correctly |
| AC-5.2 | Event Excel report generated | `event_bind_report.xlsx` exists and opens correctly |
| AC-5.3 | HTML suggestion report generated | `suggestion_report.html` exists and renders in browser |
| AC-5.4 | Excel contains CES + AOM sheets | Both monitoring systems represented in separate sheets |
| AC-5.5 | HTML includes overview + per-service stats | Report shows summary and detailed sections |
| AC-5.6 | Remediation suggestions are actionable | Specific unbound metrics/events listed with instance IDs |

## Technical Acceptance Criteria

### 1. Multi-region Support

| Criterion | Description |
|-----------|-------------|
| AC-T1.1 | Regions auto-extracted from `core_instances.json` |
| AC-T1.2 | Single region override via `--region` parameter works |
| AC-T1.3 | hcloud CLI uses `--cli-region` for region-specific API calls |
| AC-T1.4 | Project ID fetched per region via `hcloud IAM KeystoneListProjects` |

### 2. Authentication

| Criterion | Description |
|-----------|-------------|
| AC-T2.1 | AK/SK read from `HW_ACCESS_KEY` / `HW_SECRET_KEY` env vars |
| AC-T2.2 | Security token supported via `HW_SECURITY_TOKEN` |
| AC-T2.3 | Project ID override via `HW_PROJECT_ID` env var |
| AC-T2.4 | No credentials hardcoded in source code |

### 3. Error Handling

| Criterion | Description |
|-----------|-------------|
| AC-T3.1 | Missing Excel files produce clear error messages |
| AC-T3.2 | Invalid Excel format produces actionable error |
| AC-T3.3 | API failures (CES/AOM) are logged and don't crash the pipeline |
| AC-T3.4 | Empty alarm rules result in 0% binding, not a crash |

### 4. Workspace Management

| Criterion | Description |
|-----------|-------------|
| AC-T4.1 | Timestamped workspace directory created automatically |
| AC-T4.2 | `ALARM_WORKSPACE_DIR` env var enables shared directory across scripts |
| AC-T4.3 | Intermediate files in `intermediate/` subdir, final outputs at root |

## Output Quality Acceptance Criteria

### 1. Excel Report Quality
- Headers are clear and in Chinese where appropriate
- Data rows are properly aligned with correct data types
- Binding rate column shows percentage values
- Service and metric columns are human-readable (not raw codes)
- CES and AOM data in separate sheets or distinguished by column

### 2. HTML Report Quality
- Responsive layout that works on desktop and mobile
- Overview section shows aggregate binding rates
- Per-service breakdown table with sortable columns
- Remediation section lists specific unbound items with instance IDs
- "Monitoring system" column distinguishes CES vs AOM
- Color coding for binding rate levels (green/yellow/red)

### 3. Data Accuracy
- Binding rate = (bound baseline items / total baseline items) × 100%
- No duplicate instances in reports
- Instance IDs match those in `core_instances.json`
- Metric names match those in baseline Excel

## Compliance Acceptance Criteria

### 1. Huawei Cloud Standards
- Uses official CES SDK (`huaweicloudsdkces`) for CES API calls
- Uses official hcloud CLI for AOM and instance detail queries
- Follows Huawei Cloud region naming conventions

### 2. Security Standards
- Read-only operations only — no resource creation, modification, or deletion
- AK/SK never logged or written to output files
- No sensitive data in generated reports

## Acceptance Testing Process

### Pre-Acceptance Checklist
- [ ] Python 3.9+ installed
- [ ] hcloud CLI installed and configured
- [ ] AK/SK with required IAM permissions configured
- [ ] `assets/关键资源标记表.xlsx` with valid data rows
- [ ] `assets/华为云租户面监控告警基线-V26.01-beta.xlsx` with all 6 sheets
- [ ] `requirements.txt` dependencies installed

### Acceptance Test Execution
1. Run the full end-to-end workflow as described in `verification-method.md`
2. Verify all functional criteria (AC-1.x through AC-5.x)
3. Verify all technical criteria (AC-T1.x through AC-T4.x)
4. Inspect output files for quality criteria
5. Confirm no cloud resources were modified (read-only)

## References

- verification-method.md: Step-by-step verification procedures
- iam-policies.md: Required permissions for acceptance testing
- design.md: Architecture and data flow documentation
