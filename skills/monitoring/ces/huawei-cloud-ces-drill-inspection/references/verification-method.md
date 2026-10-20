# CES Drill Inspection Skill Verification Method

## Overview

This document describes the verification methods for ensuring the CES Drill Inspection skill
functions correctly and meets quality standards. Verification includes prerequisite checks,
functional testing, integration testing, and output validation.

## Verification Environment

### 1. Test Environment Setup

```bash
# Prerequisites
- Huawei Cloud account with active subscription
- At least one running ECS instance in the target region
- At least one RDS or DCS instance (for multi-service verification)
- Huawei Cloud CLI (hcloud) installed and configured
- Python 3.10+ installed
- Proper IAM permissions (see iam-policies.md)

# Environment variables for testing
export HUAWEICLOUD_REGION="cn-north-4"  # Test region
export TEST_INSTANCE_ID="<instance-uuid>"  # Test ECS instance UUID
```

### 2. Test Data Requirements

- ECS instance must be in "ACTIVE" state
- Instance should have been running for at least 30 minutes to generate metrics
- CES monitoring data should be available for the test time range
- At least one drill phase (baseline/fault/recovery) with valid time range in input.json

## Functional Verification

### 1. Prerequisite Verification

```bash
# Test 1: Verify Huawei Cloud CLI installation
hcloud version
# Expected: CLI version information displayed without errors

# Test 2: Verify CLI configuration
hcloud configure list
# Expected: Valid credentials and region configuration displayed

# Test 3: Verify Python version
python3 --version
# Expected: Python 3.10 or higher
```

### 2. Config Initialization Verification

```bash
# Test 4: Initialize config template
cd scripts/
python inspect_cli.py init-config --output /tmp/test_config.json
# Expected: Config file created with template structure (drill_name, phases, targets, etc.)

# Test 5: Verify config template structure
cat /tmp/test_config.json | python3 -m json.tool
# Expected: Valid JSON with required fields (drill_name, phases, inspect_phase, targets)
```

### 3. Connectivity Check Verification

```bash
# Test 6: Run smoke test (connectivity check)
python inspect_cli.py smoke ../references/input.json
# Expected: All target regions report connectivity OK, no errors
```

### 4. Instance Status Collection Verification

```bash
# Test 7: Verify ECS instance listing via hcloud
hcloud ECS NovaListServers --cli-region=$HUAWEICLOUD_REGION --limit=50
# Expected: JSON array of ECS instances, including test instance

# Test 8: Verify RDS instance listing via hcloud
hcloud RDS ListInstances --cli-region=$HUAWEICLOUD_REGION
# Expected: JSON array of RDS instances (if RDS targets configured)
```

### 5. CES Metrics Verification

```bash
# Test 9: List available metrics
hcloud CES ListMetrics --namespace=SYS.ECS --cli-region=$HUAWEICLOUD_REGION
# Expected: List of available metrics for ECS namespace

# Test 10: Query metric data (cpu_util)
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$TEST_INSTANCE_ID" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=$HUAWEICLOUD_REGION
# Expected: Metric data points with timestamps and values
```

## Integration Verification

### 1. Full Inspection Workflow Verification

```bash
# Test 11: Run complete inspection
cd scripts/
python inspect_cli.py inspect ../references/input.json
# Expected:
# - CLI outputs report file path and brief conclusion
# - HTML report file generated in templates/ directory
# - Report contains: AZ topology graph, status overview table, metric cards, monitoring charts
# - No errors in CLI output
```

### 2. Report Output Verification

```bash
# Test 12: Verify report file exists
ls -la ../templates/inspection_report_*.html
# Expected: At least one HTML report file exists

# Test 13: Verify report file is valid HTML
head -1 ../templates/inspection_report_*.html | grep -q "<!DOCTYPE html>"
# Expected: File starts with HTML doctype declaration

# Test 14: Verify report contains key sections
REPORT=$(ls -t ../templates/inspection_report_*.html | head -1)
grep -q "topology" "$REPORT" && grep -q "status" "$REPORT" && grep -q "metric" "$REPORT"
# Expected: Report contains topology, status, and metric sections
```

### 3. Error Handling Verification

```bash
# Test 15: Invalid config file
python inspect_cli.py inspect /tmp/nonexistent.json
# Expected: Clear error message about missing config file

# Test 16: Invalid region in config
# Edit input.json to use an invalid region, then run:
python inspect_cli.py smoke ../references/input.json
# Expected: Appropriate error message about region connectivity

# Test 17: Empty targets list
# Edit input.json to have empty targets array, then run:
python inspect_cli.py inspect ../references/input.json
# Expected: Warning about no inspection targets, graceful handling
```

### 4. Multi-Service Verification

```bash
# Test 18: Multi-service inspection (ECS + RDS + DCS)
# Configure input.json with targets for ecs, rds, and redis services
python inspect_cli.py inspect ../references/input.json
# Expected:
# - All three services appear in the report
# - Instance status collected for each service
# - Metrics collected only for normal (✅) instances
# - Abnormal instances (❌/⚠️) excluded from metric collection
```

### 5. Performance Verification

```bash
# Test 19: Response time test
time python inspect_cli.py inspect ../references/input.json
# Expected: Inspection completes within reasonable time (depends on instance count)

# Test 20: Large instance count test
# Configure input.json with instance_ids=[] (all instances in region)
python inspect_cli.py inspect ../references/input.json
# Expected: Parallel execution handles multiple instances efficiently
```

## Verification Criteria

### 1. Success Criteria

- All functional tests pass (100% success rate)
- Smoke test reports all regions as connected
- Inspection generates valid HTML report
- Report contains all expected sections (topology, status, metrics, conclusion)
- Error handling works correctly for invalid inputs
- Multi-service inspection works for all 19 supported services

### 2. Output Quality Criteria

- HTML report is well-formed and openable in browser
- AZ topology graph renders correctly with three-color status indicators
- Instance status table shows all inspected instances with correct ✅/⚠️/❌ marks
- Metric cards show per-instance, per-metric detail with ✅/❌ judgment
- Monitoring line charts render with time-series data (Chart.js inline, offline-capable)
- Inspection conclusion includes anomaly count and affected services

### 3. Read-Only Safety Criteria

- No cloud resources are modified during inspection
- No faults are injected
- No alarms are created or modified
- All hcloud commands are read-only (list/get queries only)

### 4. Security Criteria

- No hardcoded credentials in code
- Proper IAM permission validation
- Secure credential handling via hcloud CLI profile
- No sensitive data exposure in logs or reports

## Test Cases Summary

| Test # | Category | Description | Expected Result |
|--------|----------|-------------|-----------------|
| 1-3 | Prerequisites | CLI, Python, config verification | All pass |
| 4-5 | Config | Template init and validation | Valid JSON output |
| 6 | Connectivity | Smoke test | All regions OK |
| 7-8 | Status | Instance listing | Instances returned |
| 9-10 | Metrics | CES metric query | Data points returned |
| 11 | Integration | Full inspection | HTML report generated |
| 12-14 | Output | Report validation | Valid HTML with all sections |
| 15-17 | Error handling | Invalid inputs | Graceful error messages |
| 18 | Multi-service | ECS+RDS+DCS | All services in report |
| 19-20 | Performance | Time and scale | Completes in reasonable time |

## References

- [Huawei Cloud CLI Documentation](https://support.huaweicloud.com/usermanual-hcli/)
- [CES Monitoring Metrics](https://support.huaweicloud.com/usermanual-ces/ces_01_0001.html)
- [CES API Reference](https://support.huaweicloud.com/api-ces/ces_03_0041.html)
- [IAM Policy Documentation](https://support.huaweicloud.com/usermanual-iam/)
