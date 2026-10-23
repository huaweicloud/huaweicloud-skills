# Verification Method

## Overview
This document describes how to verify that the alarm-bind-inspection skill is correctly installed, configured, and functioning. It covers environment verification, per-step output checks, and end-to-end validation.

## Verification Environment

### 1. Test Environment Setup

```bash
# Verify Python version (> 3.9)
python --version

# Install dependencies
python -m pip install -r requirements.txt

# Verify hcloud CLI is available
hcloud version

# Set AK/SK environment variables
export HW_ACCESS_KEY=your_ak
export HW_SECRET_KEY=your_sk
```

### 2. Test Data Requirements
- `assets/关键资源标记表.xlsx` — must contain sheet `关键资源标记` with columns: `region`, `resource_type`, `resource_id`, `是否核心业务`, and at least one data row where `是否核心业务` = `是`
- `assets/华为云租户面监控告警基线-V26.01-beta.xlsx` — must contain sheets: `CES指标基线`, `CES事件基线`, `AOM指标基线-CCE`, `AOM指标基线-其他服务`, `AOM-Modelarts事件`, `AOM事件基线-其他服务`

## Functional Verification

### 1. Environment Prerequisite Verification

| Check | Command | Expected Result |
|-------|---------|-----------------|
| Python version | `python --version` | Version > 3.9 |
| Dependencies installed | `python -c "import openpyxl, huaweicloudsdkces"` | No error |
| hcloud CLI available | `hcloud version` | Version string displayed |
| AK/SK set | `echo $HW_ACCESS_KEY` | Non-empty value |
| Excel files exist | `ls assets/*.xlsx` | Two files listed |

### 2. Step-by-Step Output Verification

#### Step 2: Core Instance Extraction
```bash
python scripts/generate_core_instance.py
```
**Verify**: `<WORKSPACE_DIR>/intermediate/core_instances.json` exists and contains `"instances"` key with non-empty service arrays.

```bash
python -c "
import json
data = json.load(open('intermediate/core_instances.json'))
assert 'instances' in data, 'Missing instances key'
total = sum(len(v) for v in data['instances'].values())
assert total > 0, 'No instances extracted'
print(f'OK: {total} core instances across {len(data[\"instances\"])} services')
"
```

#### Step 3: Alarm Baseline Extraction
```bash
python scripts/generate_alarm_baseline.py
```
**Verify**: Four JSON files exist in `<WORKSPACE_DIR>/intermediate/`:
- `indicator_baseline.json` — CES metric baseline (non-empty array)
- `event_baseline.json` — CES event baseline (non-empty array)
- `aom_indicator_baseline.json` — AOM metric baseline (non-empty array)
- `aom_event_baseline.json` — AOM event baseline (non-empty array)

#### Step 4: CES Alarm Rule Fetch
```bash
python scripts/main_alarm.py
```
**Verify**: `<WORKSPACE_DIR>/intermediate/online_alarm_rules.json` exists and contains alarm rules with `region` field.

#### Step 4b: AOM Alarm Rule Fetch
```bash
python scripts/main_aom_alarm.py
```
**Verify**: Two files exist:
- `<WORKSPACE_DIR>/intermediate/aom_alarm_rules.json` — AOM metric alarm rules
- `<WORKSPACE_DIR>/intermediate/aom_event_alarm_rules.json` — AOM event alarm rules

#### Step 5: Event-Type Rule Extraction
```bash
python scripts/main_event.py
```
**Verify**: `<WORKSPACE_DIR>/intermediate/online_notification_rules.json` exists and contains event-type rules only (type=EVENT_SYS or EVENT_CUSTOM).

#### Step 6: Metric Dimension Enrichment
```bash
python scripts/enrich_metric_dimension.py
```
**Verify**: `<WORKSPACE_DIR>/intermediate/core_instances.json` is updated — instances now have `metric_dimension` field.

#### Step 7: Binding Analysis
```bash
python scripts/bind_analysis.py
python scripts/event_bind_analysis.py
python scripts/aom_bind_analysis.py
python scripts/aom_event_bind_analysis.py
```
**Verify**: Four report JSON files exist:
- `indicator_bind_report.json` — CES metric binding rates
- `event_bind_report.json` — CES event binding rates
- `aom_indicator_bind_report.json` — AOM metric binding rates
- `aom_event_bind_report.json` — AOM event binding rates

#### Step 8: Report Generation
```bash
python scripts/generate_excel_report.py
python scripts/generate_event_excel_report.py
python scripts/generate_suggestion.py
```
**Verify**: Three final output files exist in `<WORKSPACE_DIR>/`:
- `indicator_bind_report.xlsx` — opens correctly, contains CES + AOM sheets
- `event_bind_report.xlsx` — opens correctly, contains CES + AOM sheets
- `suggestion_report.html` — opens in browser, shows metric + event sections

## Integration Verification

### End-to-End Workflow

```bash
# Set shared workspace
export ALARM_WORKSPACE_DIR="/root/workspace/alarm-test-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ALARM_WORKSPACE_DIR/intermediate"

# Run full pipeline
python scripts/generate_core_instance.py
python scripts/generate_alarm_baseline.py
python scripts/main_alarm.py
python scripts/main_aom_alarm.py
python scripts/main_event.py
python scripts/enrich_metric_dimension.py
python scripts/bind_analysis.py
python scripts/event_bind_analysis.py
python scripts/aom_bind_analysis.py
python scripts/aom_event_bind_analysis.py
python scripts/generate_excel_report.py
python scripts/generate_event_excel_report.py
python scripts/generate_suggestion.py

# Verify all outputs
echo "=== Final outputs ==="
ls -la "$ALARM_WORKSPACE_DIR"/*.xlsx "$ALARM_WORKSPACE_DIR"/*.html
echo "=== Intermediate files ==="
ls -la "$ALARM_WORKSPACE_DIR/intermediate/"*.json
```

### Multi-region Verification
- Verify `core_instances.json` contains instances from multiple regions
- Verify `online_alarm_rules.json` contains rules tagged with different `region` values
- Verify binding reports correctly attribute instances to their respective regions

## Verification Criteria

### Success Criteria
1. All 13 intermediate JSON files are generated without errors
2. All 3 final output files (2 Excel + 1 HTML) are generated and openable
3. Binding rate values are between 0% and 100%
4. HTML report renders correctly in a browser
5. Excel reports contain both CES and AOM data sheets

### Output Quality Criteria
1. Excel reports have proper headers and formatted data
2. HTML report includes overview statistics and per-service breakdowns
3. Remediation suggestions are actionable and reference specific unbound metrics/events
4. "Monitoring system" column correctly distinguishes CES vs AOM data

### Read-Only Safety Criteria
1. No cloud resources are created, modified, or deleted
2. All API calls are list/get operations only
3. No state changes to alarm rules or monitoring configurations

## Test Cases Summary

| ID | Test Case | Input | Expected Output |
|----|-----------|-------|-----------------|
| TC-01 | Environment check | Python, hcloud, AK/SK | All prerequisites met |
| TC-02 | Core instance extraction | 关键资源标记表.xlsx | core_instances.json with instances |
| TC-03 | Baseline extraction | 告警基线.xlsx | 4 baseline JSON files |
| TC-04 | CES alarm fetch | AK/SK + regions | online_alarm_rules.json |
| TC-05 | AOM alarm fetch | AK/SK + regions | aom_alarm_rules.json + aom_event_alarm_rules.json |
| TC-06 | Metric enrichment | core_instances + baseline | Updated core_instances with metric_dimension |
| TC-07 | Binding analysis | All intermediate files | 4 binding report JSONs |
| TC-08 | Report generation | Binding reports | 2 Excel + 1 HTML |
| TC-09 | Multi-region | Instances in 2+ regions | Reports cover all regions |
| TC-10 | Empty alarm rules | Account with no alarms | Reports show 0% binding, no crash |

## References

- SKILL.md: Main skill documentation with full workflow
- iam-policies.md: Required permissions for verification
- cli-installation-guide.md: hcloud CLI setup for testing
