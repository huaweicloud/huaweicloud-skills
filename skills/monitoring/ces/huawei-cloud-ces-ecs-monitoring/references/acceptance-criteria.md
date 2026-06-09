# Huawei Cloud ECS Monitoring Skill Acceptance Criteria

## Overview

This document defines the acceptance criteria for the Huawei Cloud ECS Monitoring skill.
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

### 2. ECS Instance Management

**AC-003**: The skill must list all ECS instances in the specified region.

- **Criteria**: `hcloud ECS NovaListServers --cli-region=<region-id>` executes successfully
- **Validation**: Verify instance listing includes name, ID, status, and creation time
- **Success Metric**: 100% accurate instance listing with no missing data

**AC-004**: The skill must retrieve detailed ECS instance information.

- **Criteria**: `hcloud ECS NovaShowServer --server_id=<instance-uuid> --cli-region=<region-id>` returns complete instance details
- **Validation**: Verify all instance attributes are accessible (flavor, image, addresses, etc.)
- **Success Metric**: Complete instance metadata retrieval

### 3. Metric Query Capabilities

**AC-005**: The skill must list available CES metrics for ECS instances.

- **Criteria**: `hcloud CES ListMetrics --namespace="SYS.ECS"` returns all available metrics
- **Validation**: Verify CPU, memory, disk, and network metrics are listed
- **Success Metric**: All standard ECS metrics accessible

**AC-006**: The skill must query metric data with flexible time ranges.

- **Criteria**: Support for last 1 hour, 6 hours, 24 hours, 7 days, and custom ranges
- **Validation**: Test each time range option with valid metric data returned
- **Success Metric**: 100% time range flexibility

**AC-007**: The skill must support multiple aggregation methods.

- **Criteria**: Support for average, max, min, sum, and sampleCount statistics
- **Validation**: Verify each aggregation method produces correct results
- **Success Metric**: All aggregation methods functional

### 4. Core Monitoring Metrics

**AC-008**: The skill must monitor CPU utilization.

- **Criteria**: Query `cpu_util` (SYS.ECS) or `cpu_usage` (AGT.ECS) metric with proper dimensions and formatting
- **Validation**: Verify CPU percentage values are within 0-100% range
- **Success Metric**: Accurate CPU monitoring with trend analysis

**AC-009**: The skill must monitor memory utilization.

- **Criteria**: Query `mem_util` (SYS.ECS) or `mem_usedPercent` (AGT.ECS) metric with proper dimensions
- **Validation**: Verify memory percentage values are within 0-100% range
- **Success Metric**: Accurate memory monitoring

**AC-010**: The skill must monitor disk metrics.

- **Criteria**: Query disk usage, read/write rates with proper mount point dimensions
- **Validation**: Verify disk metrics include mount point specification
- **Success Metric**: Complete disk monitoring across all mounted filesystems

**AC-011**: The skill must monitor network metrics.

- **Criteria**: Query network inbound/outbound rates with proper NIC dimensions
- **Validation**: Verify network metrics include NIC specification
- **Success Metric**: Complete network interface monitoring

### 5. Data Presentation

**AC-012**: The skill must present data in clear, actionable format.

- **Criteria**: Output includes timestamps, metric values, and human-readable units
- **Validation**: Verify output is understandable without additional processing
- **Success Metric**: 100% user comprehension of presented data

**AC-013**: The skill must identify performance trends and anomalies.

- **Criteria**: Analysis of metric trends over time with threshold comparisons
- **Validation**: Verify trend detection for increasing/decreasing patterns
- **Success Metric**: Accurate trend identification

**AC-014**: The skill must provide optimization recommendations.

- **Criteria**: Suggestions based on metric thresholds (e.g., CPU > 80%, Memory > 85%)
- **Validation**: Verify recommendations are appropriate for detected issues
- **Success Metric**: Actionable recommendations for all common issues

## Technical Acceptance Criteria

### 1. Performance Requirements

**AC-101**: Response time for single metric query must be under 5 seconds.

- **Criteria**: `hcloud CES BatchListMetricData` completes within 5 seconds for single metric
- **Validation**: Measure response time across 100 queries, calculate 95th percentile
- **Success Metric**: 95% of queries complete within 5 seconds

**AC-102**: Response time for multiple metrics query must be under 10 seconds.

- **Criteria**: Query with 6+ metrics completes within 10 seconds
- **Validation**: Test with CPU, memory, disk, and network metrics combined
- **Success Metric**: 95% of multi-metric queries complete within 10 seconds

**AC-103**: Instance listing must complete within 3 seconds.

- **Criteria**: `hcloud ECS NovaListServers --cli-region=<region-id>` returns results within 3 seconds
- **Validation**: Test with varying numbers of instances (1-100)
- **Success Metric**: 99% of instance listings complete within 3 seconds

### 2. Reliability Requirements

**AC-104**: The skill must handle API rate limits gracefully.

- **Criteria**: Implement retry logic with exponential backoff for rate limit errors
- **Validation**: Simulate rate limiting, verify retry behavior
- **Success Metric**: Automatic recovery from rate limiting

**AC-105**: The skill must handle network timeouts and failures.

- **Criteria**: Implement timeout handling and connection failure recovery
- **Validation**: Simulate network failures, verify graceful degradation
- **Success Metric**: Clear error messages for network issues

**AC-106**: The skill must validate all inputs before API calls.

- **Criteria**: Validate instance IDs, metric names, time ranges, and regions
- **Validation**: Test with invalid inputs, verify validation errors
- **Success Metric**: 100% input validation coverage

### 3. Security Requirements

**AC-107**: The skill must not expose credentials in logs or output.

- **Criteria**: No Access Key ID or Secret Access Key in any output
- **Validation**: Search all output for credential patterns
- **Success Metric**: Zero credential exposure incidents

**AC-108**: The skill must enforce least privilege IAM permissions.

- **Criteria**: Document and verify minimum required permissions
- **Validation**: Test with minimal IAM policy, verify all functions work
- **Success Metric**: Functionality with documented minimum permissions

**AC-109**: The skill must validate IAM permissions before execution.

- **Criteria**: Check required permissions and provide clear error if missing
- **Validation**: Test with insufficient permissions, verify helpful error messages
- **Success Metric**: Clear permission guidance for all permission errors

## User Experience Acceptance Criteria

### 1. Documentation Quality

**AC-201**: All commands must have clear examples in documentation.

- **Criteria**: Every CLI command example in documentation must be executable
- **Validation**: Copy-paste test of all documentation examples
- **Success Metric**: 100% of documentation examples execute successfully

**AC-202**: Error messages must be actionable and user-friendly.

- **Criteria**: Error messages include specific problem and resolution steps
- **Validation**: Test all error conditions, verify helpful messages
- **Success Metric**: Users can resolve errors using provided guidance

**AC-203**: Installation and setup instructions must be complete.

- **Criteria**: Step-by-step guide from zero to functional skill
- **Validation**: Fresh environment test following documentation
- **Success Metric**: New users can install and use skill within 15 minutes

### 2. Output Quality

**AC-204**: Metric data must include proper units and formatting.

- **Criteria**: Percentages shown as %, bytes as KB/MB/GB, rates as per-second
- **Validation**: Verify all metric values have appropriate units
- **Success Metric**: 100% of metric values properly formatted

**AC-205**: Time-based data must include timestamps in local timezone.

- **Criteria**: Convert UTC timestamps to user's local timezone when displaying
- **Validation**: Verify timestamp conversion accuracy
- **Success Metric**: Correct timezone handling

**AC-206**: Tabular data must be properly aligned and readable.

- **Criteria**: Use consistent column widths, proper alignment, clear headers
- **Validation**: Visual inspection of table outputs
- **Success Metric**: Readable tables on terminals 80+ characters wide

### 3. Usability Requirements

**AC-207**: The skill must support both interactive and scripted use.

- **Criteria**: Human-readable output for interactive use, JSON for scripting
- **Validation**: Test both `--output table` and `--output json` formats
- **Success Metric**: Both formats produce valid, complete data

**AC-208**: Common workflows must be streamlined.

- **Criteria**: Default to common metrics when none specified
- **Validation**: Test skill with minimal input, verify useful default behavior
- **Success Metric**: Useful output with minimal user input

**AC-209**: The skill must provide progress indicators for long operations.

- **Criteria**: Show progress for queries taking > 3 seconds
- **Validation**: Test with large time ranges, verify progress indication
- **Success Metric**: Users aware of operation progress

## Integration Acceptance Criteria

### 1. CLI Integration

**AC-301**: The skill must work with standard Huawei Cloud CLI output formats.

- **Criteria**: Support json, table, text, and yaml output formats
- **Validation**: Test each output format with jq/grep validation
- **Success Metric**: All output formats produce valid, parseable data

**AC-302**: The skill must support command piping and redirection.

- **Criteria**: Output can be piped to other commands (grep, awk, jq, etc.)
- **Validation**: Test common pipe patterns
- **Success Metric**: Seamless integration with shell pipelines

**AC-303**: The skill must support environment variable configuration.

- **Criteria**: Use HUAWEICLOUD_ACCESS_KEY_ID, HUAWEICLOUD_SECRET_ACCESS_KEY, etc.
- **Validation**: Test configuration via environment variables
- **Success Metric**: Flexible credential management

### 2. Monitoring System Integration

**AC-304**: The skill must export data in monitoring-friendly formats.

- **Criteria**: Support Prometheus, Graphite, or other monitoring formats
- **Validation**: Verify format compatibility with common monitoring tools
- **Success Metric**: Direct integration with monitoring systems

**AC-305**: The skill must support alert threshold configuration.

- **Criteria**: Allow users to set custom thresholds for alerts
- **Validation**: Test threshold-based alerting functionality
- **Success Metric**: Configurable alerting

## Quality Assurance Acceptance Criteria

### 1. Testing Coverage

**AC-401**: Unit tests must cover 80% of core functionality.

- **Criteria**: Code coverage report showing >= 80% line coverage
- **Validation**: Run coverage tools, generate report
- **Success Metric**: 80%+ test coverage

**AC-402**: Integration tests must cover all Huawei Cloud API interactions.

- **Criteria**: Test all ECS and CES API calls with mock responses
- **Validation**: Verify API error handling and response parsing
- **Success Metric**: 100% API interaction coverage

**AC-403**: End-to-end tests must validate complete workflows.

- **Criteria**: Test from authentication to data presentation
- **Validation**: Complete workflow tests with real Huawei Cloud environment
- **Success Metric**: All user workflows functional

### 2. Code Quality

**AC-404**: Code must follow Huawei Cloud CLI best practices.

- **Criteria**: Consistent with hcloud command patterns and conventions
- **Validation**: Code review against Huawei Cloud CLI style guide
- **Success Metric**: Adherence to established patterns

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

- **Criteria**: Implement rate limiting and backoff as per Huawei Cloud guidelines
- **Validation**: Load testing within rate limits
- **Success Metric**: No rate limit violations in normal use

### 2. Security Standards

**AC-503**: The skill must not store credentials persistently.

- **Criteria**: Use Huawei Cloud CLI credential management only
- **Validation**: Audit credential handling code
- **Success Metric**: No credential storage

**AC-504**: The skill must validate all inputs for security.

- **Criteria**: Input validation to prevent injection attacks
- **Validation**: Security penetration testing
- **Success Metric**: No security vulnerabilities

## Performance Benchmarks

### 1. Response Time Benchmarks

| Operation | Target | Acceptable | Unacceptable |
|-----------|--------|------------|--------------|
| List instances | < 2s | < 3s | > 5s |
| Single metric query | < 3s | < 5s | > 10s |
| Multiple metrics (6) | < 6s | < 10s | > 15s |
| Historical data (7 days) | < 8s | < 12s | > 20s |

### 2. Resource Usage Benchmarks

| Resource | Target | Acceptable | Unacceptable |
|----------|--------|------------|--------------|
| Memory (per query) | < 50MB | < 100MB | > 200MB |
| CPU (peak) | < 5% | < 10% | > 20% |
| Network (per query) | < 100KB | < 500KB | > 1MB |

## Acceptance Testing Process

### 1. Pre-Acceptance Checklist

- [ ] All functional acceptance criteria met
- [ ] All technical acceptance criteria met  
- [ ] All user experience acceptance criteria met
- [ ] All integration acceptance criteria met
- [ ] All quality assurance acceptance criteria met
- [ ] All compliance acceptance criteria met
- [ ] Performance benchmarks achieved
- [ ] Documentation complete and accurate
- [ ] Test coverage reports generated
- [ ] Security review completed

### 2. Acceptance Test Execution Example

The following is an example of acceptance test execution commands and process:

```bash
#!/bin/bash
# Acceptance test execution example script
# Note: This is an example process that needs to be adjusted based on actual test scripts

echo "=== Huawei Cloud ECS Monitoring Skill Acceptance Test ==="
echo "Start time: $(date)"

# 1. Set up test environment
echo "1. Setting up test environment..."
export HUAWEICLOUD_REGION="${HUAWEICLOUD_REGION:-cn-north-1}"
export TEST_INSTANCE_ID="${TEST_INSTANCE_ID:-}"
export TEST_OUTPUT_DIR="acceptance-test-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$TEST_OUTPUT_DIR"

# 2. Run acceptance test suite
echo "2. Running acceptance test suite..."
# This should call actual acceptance test scripts
# Example test commands:
echo "Test 1: Verifying Huawei Cloud CLI installation..."
if command -v hcloud &> /dev/null; then
    echo "✓ Huawei Cloud CLI is installed"
    echo "PASS" > "$TEST_OUTPUT_DIR/test-01-cli-installation.result"
else
    echo "✗ Huawei Cloud CLI is not installed"
    echo "FAIL" > "$TEST_OUTPUT_DIR/test-01-cli-installation.result"
fi

echo "Test 2: Verifying credential configuration..."
if hcloud configure list &> /dev/null; then
    echo "✓ Credentials configured correctly"
    echo "PASS" > "$TEST_OUTPUT_DIR/test-02-credentials.result"
else
    echo "✗ Credential configuration error"
    echo "FAIL" > "$TEST_OUTPUT_DIR/test-02-credentials.result"
fi

echo "Test 3: Verifying ECS instance listing..."
if hcloud ECS NovaListServers --cli-region="$HUAWEICLOUD_REGION" &> /dev/null; then
    echo "✓ ECS instance listing works"
    echo "PASS" > "$TEST_OUTPUT_DIR/test-03-ecs-list.result"
else
    echo "✗ ECS instance listing failed"
    echo "FAIL" > "$TEST_OUTPUT_DIR/test-03-ecs-list.result"
fi

echo "Test 4: Verifying CES metric query..."
if hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$TEST_INSTANCE_ID" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region="$HUAWEICLOUD_REGION" &> /dev/null; then
    echo "✓ CES metric query works"
    echo "PASS" > "$TEST_OUTPUT_DIR/test-04-ces-query.result"
else
    echo "✗ CES metric query failed"
    echo "FAIL" > "$TEST_OUTPUT_DIR/test-04-ces-query.result"
fi

# 3. Generate acceptance report
echo "3. Generating acceptance report..."
REPORT_FILE="$TEST_OUTPUT_DIR/acceptance-report.json"
cat > "$REPORT_FILE" << EOF
{
  "acceptance_test_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "skill": "huawei-cloud-ces-ecs-monitoring",
  "environment": {
    "region": "$HUAWEICLOUD_REGION",
    "platform": "$(uname -s)"
  },
  "test_results": {
    "total_tests": 2,
    "passed": 0,
    "failed": 0,
    "success_rate": "0%"
  },
  "criteria_validation": {
    "functional_criteria": "PENDING",
    "technical_criteria": "PENDING",
    "ux_criteria": "PENDING",
    "integration_criteria": "PENDING",
    "qa_criteria": "PENDING",
    "compliance_criteria": "PENDING"
  },
  "notes": "This is an example acceptance report. Actual acceptance requires execution of the complete test suite."
}
EOF

# 4. Verify all acceptance criteria
echo "4. Verifying acceptance criteria..."
echo "Verifying requirements according to acceptance criteria document:"
echo "- Functional acceptance criteria (AC-001 to AC-014)"
echo "- Technical acceptance criteria (AC-101 to AC-109)"
echo "- User experience acceptance criteria (AC-201 to AC-209)"
echo "- Integration acceptance criteria (AC-301 to AC-303)"
echo "- Quality assurance acceptance criteria (AC-401 to AC-406)"
echo "- Compliance acceptance criteria (AC-501 to AC-504)"

echo "Acceptance test execution completed"
echo "Report file: $REPORT_FILE"
echo "Output directory: $TEST_OUTPUT_DIR"
```

## References

- [Huawei Cloud official documentation](https://support.huaweicloud.com/usermanual-ecs/ecs_03_1001.html)
- [CLI reference documentation](https://support.huaweicloud.com/function-hcli/index.html)