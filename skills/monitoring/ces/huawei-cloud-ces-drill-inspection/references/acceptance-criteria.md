# CES Drill Inspection Skill Acceptance Criteria

## Overview

This document defines the acceptance criteria for the CES Drill Inspection skill.
These criteria ensure the skill meets quality standards, functional requirements,
and user expectations before being considered complete and ready for use.

## Functional Acceptance Criteria

### 1. Prerequisites Verification

**AC-001**: The skill must verify Huawei Cloud CLI installation before execution.
- **Criteria**: Skill checks `hcloud --version` and provides installation instructions if CLI is not found
- **Validation**: Run skill without Huawei Cloud CLI installed, verify helpful error message
- **Success Metric**: 100% of users receive clear installation guidance

**AC-002**: The skill must validate Huawei Cloud credentials configuration.
- **Criteria**: Skill checks `hcloud configure list` and validates credentials
- **Validation**: Run with invalid/missing credentials, verify appropriate error handling
- **Success Metric**: Proper authentication error messages for all credential issues

**AC-003**: The skill must verify Python 3.10+ runtime.
- **Criteria**: Check Python version at startup, reject if below 3.10
- **Validation**: Run with Python 3.9, verify clear version error
- **Success Metric**: Clear version requirement messaging

### 2. Configuration Management

**AC-004**: The skill must generate a valid config template via `init-config`.
- **Criteria**: `python inspect_cli.py init-config --output my_config.json` creates a valid JSON file
- **Validation**: Verify generated config has all required fields (drill_name, phases, inspect_phase, targets)
- **Success Metric**: 100% valid config template generation

**AC-005**: The skill must validate config file before inspection.
- **Criteria**: Invalid config (missing fields, wrong types) produces clear validation errors
- **Validation**: Test with missing drill_name, empty phases, invalid inspect_phase
- **Success Metric**: All config errors caught with actionable messages

**AC-006**: The skill must auto-infer unspecified config fields.
- **Criteria**: Region list, service toggles, expected status, runtime params auto-inferred from targets
- **Validation**: Provide minimal config, verify all fields populated correctly
- **Success Metric**: Minimal user input produces complete inspection

### 3. Instance Status Collection

**AC-007**: The skill must collect instance status across all 19 supported cloud services.
- **Criteria**: For each service in targets, query instance status via hcloud in parallel
- **Validation**: Configure targets for ECS, RDS, DCS, ELB - verify all collected
- **Success Metric**: All 19 services supported with correct status mapping

**AC-008**: The skill must mark each instance with correct status indicator.
- **Criteria**: normal, warning, abnormal based on expected steady-state status
- **Validation**: Verify ECS=ACTIVE, RDS=ACTIVE+master, DCS=RUNNING
- **Success Metric**: 100% accurate status classification

**AC-009**: The skill must handle empty instance lists gracefully.
- **Criteria**: When no instances found for a service/region, report without error
- **Validation**: Configure a region with no ECS instances, verify graceful handling
- **Success Metric**: No crashes on empty results

### 4. Metric Collection

**AC-010**: The skill must collect CES metrics only for normal instances.
- **Criteria**: Abnormal instances are excluded from metric collection
- **Validation**: Mix of normal/abnormal instances, verify only normal ones have metrics
- **Success Metric**: Zero metric queries for abnormal instances

**AC-011**: The skill must collect metrics across all drill phases.
- **Criteria**: Metrics collected for baseline, fault, and recovery phases as configured
- **Validation**: Configure 3 phases, verify metrics collected for each phase time range
- **Success Metric**: Complete phase coverage in report

**AC-012**: The skill must support 238 metrics across 19 services.
- **Criteria**: All metrics in metrics.json are queryable
- **Validation**: Reference metrics-reference.md for full list, test representative metrics per service
- **Success Metric**: All documented metrics collectible

### 5. Steady-State Judgment

**AC-013**: The skill must judge instance-level steady state based on status.
- **Criteria**: Compare instance status against expected steady-state table
- **Validation**: Verify RDS primary role check, ECS ACTIVE check
- **Success Metric**: Correct status-based judgment for all services

**AC-014**: The skill must judge metric-level steady state by comparing phases.
- **Criteria**: Compare inspection phase metrics against baseline, mark per metric
- **Validation**: Configure baseline with normal values, recovery with anomalous values
- **Success Metric**: Accurate anomaly detection

### 6. Report Generation

**AC-015**: The skill must generate an interactive HTML report.
- **Criteria**: Report includes AZ topology graph, status overview table, metric cards, Chart.js charts
- **Validation**: Open generated HTML in browser, verify all sections render
- **Success Metric**: Complete, viewable HTML report

**AC-016**: The skill must include AZ resource topology in the report.
- **Criteria**: Topology shows region to AZ to instance hierarchy with three-color status
- **Validation**: Verify topology graph matches actual resource distribution
- **Success Metric**: Accurate topology representation

**AC-017**: The skill must include monitoring line charts (Chart.js, inline, offline-capable).
- **Criteria**: Time-series charts render without external network dependency
- **Validation**: Open report with network disconnected, verify charts still render
- **Success Metric**: Offline chart rendering

**AC-018**: The skill must clean up old reports, keeping only the latest 10.
- **Criteria**: After generating 11+ reports, oldest are deleted
- **Validation**: Generate 12 reports, verify only 10 remain in templates/
- **Success Metric**: Automatic history cleanup

## Technical Acceptance Criteria

### 1. Performance Requirements

**AC-101**: Instance status collection must use parallel execution.
- **Criteria**: Multiple services/regions queried in parallel, not sequentially
- **Validation**: Time multi-service inspection, verify parallel speedup
- **Success Metric**: Inspection time scales with concurrency, not service count

**AC-102**: Metric collection must use parallel execution.
- **Criteria**: Multiple instances/metrics queried in parallel
- **Validation**: Time multi-instance metric collection, verify parallel speedup
- **Success Metric**: Metric collection time sub-linear with instance count

**AC-103**: Single-service inspection must complete within 30 seconds.
- **Criteria**: ECS-only inspection with < 50 instances completes in under 30s
- **Validation**: Time inspection with known instance count
- **Success Metric**: 95% of inspections complete within 30s

### 2. Reliability Requirements

**AC-104**: The skill must handle hcloud API errors gracefully.
- **Criteria**: API errors produce clear messages, not crashes
- **Validation**: Simulate API errors, verify graceful handling
- **Success Metric**: No unhandled exceptions from API errors

**AC-105**: The skill must handle partial failures across services.
- **Criteria**: If one service fails, other services still complete inspection
- **Validation**: Configure invalid region for one service, verify others succeed
- **Success Metric**: Partial results on partial failures

**AC-106**: The skill must validate all inputs before API calls.
- **Criteria**: Validate service names, region IDs, instance IDs, metric names, time ranges
- **Validation**: Test with invalid inputs, verify validation errors before API calls
- **Success Metric**: 100% input validation coverage

### 3. Security Requirements

**AC-107**: The skill must be strictly read-only.
- **Criteria**: No cloud resource modifications, no fault injection, no alarm creation
- **Validation**: Audit all hcloud commands used, verify all are list/get queries
- **Success Metric**: Zero write operations

**AC-108**: The skill must not expose credentials in logs or output.
- **Criteria**: No Access Key ID or Secret Access Key in any output or report
- **Validation**: Search all output for credential patterns
- **Success Metric**: Zero credential exposure

**AC-109**: The skill must enforce least privilege IAM permissions.
- **Criteria**: Document and verify minimum required read-only permissions
- **Validation**: Test with minimal IAM policy, verify all functions work
- **Success Metric**: Functionality with documented minimum permissions

## User Experience Acceptance Criteria

### 1. Documentation Quality

**AC-201**: All commands must have clear examples in documentation.
- **Criteria**: Every CLI command example in SKILL.md must be executable
- **Validation**: Copy-paste test of all documentation examples
- **Success Metric**: 100% of documentation examples execute successfully

**AC-202**: Error messages must be actionable and user-friendly.
- **Criteria**: Error messages include specific problem and resolution steps
- **Validation**: Test all error conditions, verify helpful messages
- **Success Metric**: Users can resolve errors using provided guidance

**AC-203**: Configuration guide must be complete with field reference.
- **Criteria**: All input.json fields documented with required/optional, description, examples
- **Validation**: Verify field reference table covers all config fields
- **Success Metric**: Complete configuration documentation

### 2. Output Quality

**AC-204**: CLI output must include report file path and brief conclusion.
- **Criteria**: After inspection, CLI prints report path and anomaly summary
- **Validation**: Run inspection, verify CLI output format
- **Success Metric**: Clear, concise CLI output

**AC-205**: HTML report must be self-contained (no external dependencies).
- **Criteria**: Chart.js inlined, all CSS inlined, no CDN references
- **Validation**: Open report with network disconnected, verify full rendering
- **Success Metric**: 100% offline-capable report

**AC-206**: Report must include inspection conclusion with recommendations.
- **Criteria**: Anomaly count, affected services, and actionable recommendations
- **Validation**: Verify conclusion section in report
- **Success Metric**: Clear, actionable inspection conclusions

### 3. Usability Requirements

**AC-207**: The skill must support natural language config generation.
- **Criteria**: User describes scenario in natural language, model generates input.json
- **Validation**: Test with natural language prompt, verify generated config is valid
- **Success Metric**: Valid config from natural language description

**AC-208**: The skill must support multi-fault scenarios.
- **Criteria**: Multiple overlapping fault phases (cascading, concurrent faults)
- **Validation**: Configure overlapping phases, verify all collected correctly
- **Success Metric**: Correct multi-fault handling

**AC-209**: The skill must support DMS engine specification.
- **Criteria**: Kafka, RabbitMQ, RocketMQ engines with different metric sets
- **Validation**: Configure DMS with each engine, verify correct metrics collected
- **Success Metric**: All DMS engines supported

## Integration Acceptance Criteria

### 1. CLI Integration

**AC-301**: The skill must work with hcloud CLI multi-profile configuration.
- **Criteria**: Support `--cli-profile` for different environments
- **Validation**: Test with dev/prod profiles
- **Success Metric**: Multi-environment support

**AC-302**: The skill must support all Huawei Cloud regions.
- **Criteria**: Any valid region ID works for inspection targets
- **Validation**: Test with cn-north-4, cn-east-2, ap-southeast-1
- **Success Metric**: Multi-region support

### 2. Report Integration

**AC-303**: The HTML report must be openable in standard browsers.
- **Criteria**: Compatible with Chrome, Firefox, Edge, Safari
- **Validation**: Open report in each browser, verify rendering
- **Success Metric**: Cross-browser compatibility

**AC-304**: The report must include Chart.js inline for offline capability.
- **Criteria**: No external script tags, Chart.js embedded in HTML
- **Validation**: Inspect HTML source for inline Chart.js
- **Success Metric**: Fully offline-capable charts

## Quality Assurance Acceptance Criteria

### 1. Testing Coverage

**AC-401**: Core scripts must handle edge cases.
- **Criteria**: Empty instances, missing metrics, invalid time ranges, service unavailable
- **Validation**: Test each edge case, verify graceful handling
- **Success Metric**: All edge cases handled

**AC-402**: All 19 services must have status collection support.
- **Criteria**: status_collector.py handles all 19 service types
- **Validation**: Test each service type, verify status collected
- **Success Metric**: 19/19 services supported

**AC-403**: All 238 metrics must have metadata in metrics.json.
- **Criteria**: Every metric in metrics-reference.md has corresponding entry in metrics.json
- **Validation**: Cross-reference metrics-reference.md with metrics.json
- **Success Metric**: 100% metric metadata coverage

### 2. Code Quality

**AC-404**: Code must follow Python best practices.
- **Criteria**: PEP 8 style, type hints, docstrings for public functions
- **Validation**: Code review, lint with flake8/pylint
- **Success Metric**: Clean lint results

**AC-405**: Error handling must be comprehensive.
- **Criteria**: All possible errors caught and handled gracefully
- **Validation**: Error injection testing
- **Success Metric**: No unhandled exceptions

**AC-406**: Documentation must be complete and accurate.
- **Criteria**: All functions, parameters, and examples documented
- **Validation**: Documentation review against implementation
- **Success Metric**: 100% documentation accuracy

## Compliance Acceptance Criteria

### 1. Huawei Cloud Standards

**AC-501**: The skill must comply with Huawei Cloud API conventions.
- **Criteria**: Use official Huawei Cloud CLI patterns and endpoints
- **Validation**: API usage review
- **Success Metric**: Compliance with Huawei Cloud standards

**AC-502**: The skill must respect Huawei Cloud rate limits.
- **Criteria**: Parallel execution with controlled concurrency (default 10/8)
- **Validation**: Verify concurrency limits in config
- **Success Metric**: No rate limit violations in normal use

### 2. Security Standards

**AC-503**: The skill must not store credentials persistently.
- **Criteria**: Use Huawei Cloud CLI credential management only
- **Validation**: Audit credential handling code
- **Success Metric**: No credential storage in skill code

**AC-504**: The skill must validate all inputs for security.
- **Criteria**: Input validation to prevent injection attacks
- **Validation**: Security testing with malformed inputs
- **Success Metric**: No security vulnerabilities

## Performance Benchmarks

### 1. Response Time Benchmarks

| Operation | Target | Acceptable | Unacceptable |
|-----------|--------|------------|--------------|
| Smoke test (connectivity) | < 5s | < 10s | > 20s |
| Single-service inspection | < 15s | < 30s | > 60s |
| Multi-service inspection (5 services) | < 30s | < 60s | > 120s |
| Full inspection (19 services) | < 60s | < 120s | > 300s |

### 2. Resource Usage Benchmarks

| Resource | Target | Acceptable | Unacceptable |
|----------|--------|------------|--------------|
| Memory (per inspection) | < 100MB | < 200MB | > 500MB |
| CPU (peak) | < 10% | < 20% | > 50% |
| HTML report size | < 5MB | < 10MB | > 20MB |

## Acceptance Testing Process

### 1. Pre-Acceptance Checklist

- [ ] All functional acceptance criteria met (AC-001 to AC-018)
- [ ] All technical acceptance criteria met (AC-101 to AC-109)
- [ ] All user experience acceptance criteria met (AC-201 to AC-209)
- [ ] All integration acceptance criteria met (AC-301 to AC-304)
- [ ] All quality assurance acceptance criteria met (AC-401 to AC-406)
- [ ] All compliance acceptance criteria met (AC-501 to AC-504)
- [ ] Performance benchmarks achieved
- [ ] Documentation complete and accurate
- [ ] Security review completed (read-only verified)

### 2. Acceptance Test Execution Example

```bash
#!/bin/bash
# Acceptance test execution example script

echo "=== CES Drill Inspection Skill Acceptance Test ==="
echo "Start time: $(date)"

# 1. Set up test environment
export HUAWEICLOUD_REGION="${HUAWEICLOUD_REGION:-cn-north-4}"
export TEST_OUTPUT_DIR="acceptance-test-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$TEST_OUTPUT_DIR"

# 2. Run prerequisite checks
echo "Test 1: Verifying hcloud CLI installation..."
hcloud version && echo "PASS" > "$TEST_OUTPUT_DIR/test-01.result" || echo "FAIL" > "$TEST_OUTPUT_DIR/test-01.result"

echo "Test 2: Verifying Python version..."
python3 --version | grep -qE "3\.(1[0-9]|[2-9][0-9])" && echo "PASS" > "$TEST_OUTPUT_DIR/test-02.result" || echo "FAIL" > "$TEST_OUTPUT_DIR/test-02.result"

# 3. Run config initialization
echo "Test 3: Verifying config template generation..."
cd scripts/
python inspect_cli.py init-config --output /tmp/test_config.json && echo "PASS" > "$TEST_OUTPUT_DIR/test-03.result" || echo "FAIL" > "$TEST_OUTPUT_DIR/test-03.result"

# 4. Run connectivity check
echo "Test 4: Verifying connectivity check..."
python inspect_cli.py smoke ../references/input.json && echo "PASS" > "$TEST_OUTPUT_DIR/test-04.result" || echo "FAIL" > "$TEST_OUTPUT_DIR/test-04.result"

# 5. Run full inspection
echo "Test 5: Verifying full inspection..."
python inspect_cli.py inspect ../references/input.json && echo "PASS" > "$TEST_OUTPUT_DIR/test-05.result" || echo "FAIL" > "$TEST_OUTPUT_DIR/test-05.result"

# 6. Verify report output
echo "Test 6: Verifying HTML report..."
REPORT=$(ls -t ../templates/inspection_report_*.html 2>/dev/null | head -1)
if [ -n "$REPORT" ] && head -1 "$REPORT" | grep -q "<!DOCTYPE html>"; then
    echo "PASS" > "$TEST_OUTPUT_DIR/test-06.result"
else
    echo "FAIL" > "$TEST_OUTPUT_DIR/test-06.result"
fi

echo "Acceptance test execution completed"
echo "Results: $TEST_OUTPUT_DIR"
```

## References

- [Huawei Cloud CLI Documentation](https://support.huaweicloud.com/usermanual-hcli/)
- [CES Monitoring Metrics](https://support.huaweicloud.com/usermanual-ces/ces_01_0001.html)
- [CES API Reference](https://support.huaweicloud.com/api-ces/ces_03_0041.html)
- [IAM Policy Documentation](https://support.huaweicloud.com/usermanual-iam/)
