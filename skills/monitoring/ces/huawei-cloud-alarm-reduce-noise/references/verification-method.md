# Verification Method

## Overview
This document describes how to verify that the alarm-reduce-noise skill is correctly installed, configured, and functioning. It covers environment verification, per-step output checks, and end-to-end validation.

## Verification Environment

### 1. Test Environment Setup

```bash
# Verify Python version (>= 3.10)
python3 --version

# Install dependencies
pip install -r requirements.txt

# Verify hcloud CLI is available
hcloud version

# Set AK/SK environment variables
export HW_ACCESS_KEY=your_ak
export HW_SECRET_KEY=your_sk
```

### 2. Core Instance Discovery
- Run `python3 scripts/generate_instance.py` to discover core instances via RMS API
- This generates `core_instances.json` in the workspace directory, containing resource IDs grouped by region
- Regions and core resources are automatically discovered — no manual Excel maintenance needed

## Functional Verification

### 1. Environment Prerequisite Verification

| Check | Command | Expected Result |
|-------|---------|-----------------|
| Python version | `python3 --version` | Version >= 3.10 |
| Dependencies installed | `python3 -c "import dotenv"` | No error |
| hcloud CLI available | `hcloud version` | Version string displayed |
| AK/SK set | `echo $HW_ACCESS_KEY` | Non-empty value |
| RMS API accessible | `hcloud RMS CollectAllResourcesSummary --cli-region=cn-north-4` | JSON output with provider list |

### 2. Step-by-Step Output Verification

#### Step 1: Environment Check

```bash
python3 scripts/check_env.py
```

**Verify**: Output contains `[OK]` for Python version, dependencies, and hcloud CLI. Exit code 0.

#### Step 2: Core Instance Discovery

```bash
python3 scripts/generate_instance.py
```

**Verify**: `core_instances.json` is generated in the workspace directory with `{"resources": {region: [resource_ids]}}` structure.

#### Step 3: Alarm Data Collection

```bash
python3 scripts/alarm.py --days 7
```

**Verify**: A workspace directory is created under `/root/workspace/alarm-reduce-noise-workspace_YYYYMMDD_HHMMSS/` containing:
- `alarm_result.json` — multi-region alarm data with `{"alarms": {region_name: {...}}}` structure
- `ces_alarm_rules.json` — multi-region alarm rules with `{region_name: [rules]}` structure

```bash
# Verify output structure
python3 -c "
import json, glob
files = glob.glob('/root/workspace/alarm-reduce-noise-workspace_*/alarm_result.json')
assert files, 'No alarm_result.json found'
data = json.load(open(files[-1]))
assert 'alarms' in data, 'Missing alarms key'
for region, info in data['alarms'].items():
    assert 'alarm_history' in info, f'Missing alarm_history for {region}'
    print(f'OK: {region} — {len(info[\"alarm_history\"])} alarms')
"
```

#### Step 4: Alarm Analysis & Report Generation

```bash
# Use the same workspace directory from Step 3
export ALARM_REDUCE_NOISE_WORKSPACE_DIR=$(ls -d /root/workspace/alarm-reduce-noise-workspace_* | tail -1)
python3 scripts/analyze_alarm.py
```

**Verify**: `$ALARM_REDUCE_NOISE_WORKSPACE_DIR/alarm-noise-report.html` exists and:
- Opens correctly in a browser
- Contains region switcher at the top
- Shows health score, alarm overview, four analysis dimensions
- Includes降噪建议 (noise reduction suggestions) section

```bash
# Verify report exists and has content
python3 -c "
import os
report = os.path.join(os.environ['ALARM_REDUCE_NOISE_WORKSPACE_DIR'], 'alarm-noise-report.html')
assert os.path.exists(report), 'Report not found'
size = os.path.getsize(report)
assert size > 10000, f'Report too small ({size} bytes)'
print(f'OK: report size {size} bytes')
"
```

## Integration Verification

### End-to-End Workflow

```bash
# Set shared workspace
export ALARM_REDUCE_NOISE_WORKSPACE_DIR="/root/workspace/alarm-reduce-noise-workspace_$(date +%Y%m%d_%H%M%S)"

# Run full pipeline
python3 scripts/check_env.py
python3 scripts/generate_instance.py
python3 scripts/alarm.py --days 7
python3 scripts/analyze_alarm.py

# Verify all outputs
echo "=== Workspace contents ==="
ls -la "$ALARM_REDUCE_NOISE_WORKSPACE_DIR"
echo "=== Report size ==="
wc -c "$ALARM_REDUCE_NOISE_WORKSPACE_DIR/alarm-noise-report.html"
```

### Multi-region Verification
- Verify `alarm_result.json` contains alarms from multiple regions (auto-discovered via RMS API)
- Verify HTML report has a region switcher dropdown with all regions
- Verify switching regions updates all report sections

### Core Resource Filtering Verification
- Verify only alarms for core resources (discovered via RMS API) are analyzed
- Verify non-core resource alarms are filtered out
- Verify report shows "核心资源告警" statistics

## Verification Criteria

### Success Criteria
1. `check_env.py` exits with code 0 and all checks pass
2. `core_instances.json` is generated with resource IDs grouped by region
3. `alarm_result.json` is generated with multi-region alarm data
4. `ces_alarm_rules.json` is generated with multi-region alarm rules
5. `alarm-noise-report.html` is generated and renders correctly in a browser
6. Report contains all four analysis dimensions (告警治理, 告警收敛, 告警关联, 长久未恢复告警)
7. Report includes health score (0-100) for each region
8. Report includes降噪建议 with priority levels (高/中/长期)

### Output Quality Criteria
1. HTML report has a responsive layout with region switcher
2. Health score is calculated from 5 weighted dimensions
3. TOP10 high-frequency alarms are listed (core resources only)
4. Daily alarm trend chart is present
5. 降噪建议 are actionable with specific resource IDs and metrics

### Read-Only Safety Criteria
1. No cloud resources are created, modified, or deleted
2. All API calls are list/get operations only (ListAlarmHistories, ListAlarmRules, ListMetricOrEventAlarmRule, RMS CollectAllResourcesSummary, RMS ListAllResources)
3. No state changes to alarm rules or monitoring configurations

## Test Cases Summary

| ID | Test Case | Input | Expected Output |
|----|-----------|-------|-----------------|
| TC-01 | Environment check | Python, hcloud, AK/SK | All prerequisites met |
| TC-02 | Instance discovery | RMS API accessible | core_instances.json with resources by region |
| TC-03 | Alarm collection (1 day) | `--days 1` | alarm_result.json with alarm_history |
| TC-04 | Alarm collection (7 days) | `--days 7` | alarm_result.json with more alarms than TC-03 |
| TC-05 | Alarm collection (30 days) | `--days 30` | alarm_result.json with more alarms than TC-04 |
| TC-06 | Custom date range | `--start-date 2026-10-20 --end-date 2026-10-27` | alarm_result.json for specified range |
| TC-07 | Analysis & report | alarm_result.json | alarm-noise-report.html with all sections |
| TC-08 | Multi-region | RMS API returns 2+ regions | Report with region switcher |
| TC-09 | Core resource filter | core_instances.json with resource IDs | Only core resource alarms analyzed |
| TC-10 | Empty alarms | Region with no alarms | Report shows 0 alarms, no crash |
| TC-11 | Workspace sharing | ALARM_REDUCE_NOISE_WORKSPACE_DIR set | All scripts use same directory |

## References

- SKILL.md: Main skill documentation with full workflow
- iam-policies.md: Required permissions for verification
- cli-installation-guide.md: hcloud CLI setup for testing
- alarm-analysis.md: Detailed analysis methodology
