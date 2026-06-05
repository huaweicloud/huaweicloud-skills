# Acceptance Criteria

This document defines the acceptance criteria, test cases, and success standards for the FunctionGraph function creation workflow.

## Overview

### Scope

| Component | Description |
|-----------|-------------|
| Feature | FunctionGraph function creation |
| Platform | Huawei Cloud FunctionGraph |
| Methods | CLI and SDK |
| Regions | All supported regions |

### Test Categories

| Category | Priority | Coverage |
|----------|----------|----------|
| Smoke Tests | Critical | Core functionality |
| Functional Tests | High | All features |
| Integration Tests | Medium | External integrations |
| Performance Tests | Medium | Performance benchmarks |
| Security Tests | High | Security compliance |

## Test Cases

### TC-001: Basic Function Creation

| Attribute | Value |
|-----------|-------|
| ID | TC-001 |
| Name | Basic function creation |
| Priority | Critical |
| Type | Smoke Test |

**Preconditions:**

- KooCLI is installed and configured
- IAM permissions are granted
- Valid runtime code is prepared

**Test Steps:**

```bash
# Step 1: Create function
hcloud FunctionGraph function create \
  --func_name=test-function-001 \
  --package_type=Zip \
  --runtime=Python3.9 \
  --handler=index.handler \
  --memory_size=128 \
  --timeout=10 \
  --code_url=https://obs-bucket.obs.cn-north-4.myhuaweicloud.com/code.zip

# Step 2: Verify creation
hcloud FunctionGraph function show \
  --func_urn=urn:fg:cn-north-4:PROJECT_ID:function:test-function-001:latest
```

**Expected Results:**

- Function is created successfully
- Status is ACTIVE
- All configuration matches input parameters

**Pass Criteria:**

- [ ] Function exists in function list
- [ ] Status equals ACTIVE
- [ ] func_name matches specification
- [ ] runtime matches specification
- [ ] memory_size matches specification
- [ ] timeout matches specification

---

### TC-002: Function with VPC Configuration

| Attribute | Value |
|-----------|-------|
| ID | TC-002 |
| Name | Function with VPC configuration |
| Priority | High |
| Type | Functional Test |

**Test Steps:**

```bash
hcloud FunctionGraph function create \
  --func_name=test-function-vpc \
  --package_type=Zip \
  --runtime=Python3.9 \
  --handler=index.handler \
  --memory_size=256 \
  --timeout=30 \
  --vpc_id=VPC_ID \
  --subnet_id=SUBNET_ID \
  --security_group_id=SECURITY_GROUP_ID
```

**Expected Results:**

- Function is created with VPC configuration
- VPC connectivity is established
- Network isolation is verified

**Pass Criteria:**

- [ ] VPC configuration is saved
- [ ] Function can access VPC resources
- [ ] Network connectivity is verified

---

### TC-003: Function with Environment Variables

| Attribute | Value |
|-----------|-------|
| ID | TC-003 |
| Name | Function with environment variables |
| Priority | High |
| Type | Functional Test |

**Test Steps:**

```bash
hcloud FunctionGraph function create \
  --func_name=test-function-env \
  --package_type=Zip \
  --runtime=Python3.9 \
  --handler=index.handler \
  --memory_size=128 \
  --timeout=10 \
  --environment_variables='{"DB_HOST": "localhost", "DB_PORT": "3306", "DEBUG": "false"}'
```

**Expected Results:**

- Environment variables are set correctly
- Variables are accessible in function execution

**Pass Criteria:**

- [ ] All environment variables are saved
- [ ] Variables are accessible at runtime
- [ ] Sensitive variables are masked in output

---

### TC-004: Function with Layers

| Attribute | Value |
|-----------|-------|
| ID | TC-004 |
| Name | Function with layers |
| Priority | Medium |
| Type | Functional Test |

**Test Steps:**

```bash
# Create layer first
hcloud FunctionGraph layer create \
  --layer_name=my-layer \
  --runtime=Python3.9 \
  --code_url=https://obs-bucket/layer.zip

# Create function with layer
hcloud FunctionGraph function create \
  --func_name=test-function-layer \
  --package_type=Zip \
  --runtime=Python3.9 \
  --handler=index.handler \
  --layers='[{"urn": "urn:fg:cn-north-4:PROJECT_ID:layer:my-layer:1"}]'
```

**Expected Results:**

- Layer is attached to function
- Layer dependencies are available

**Pass Criteria:**

- [ ] Layer is associated with function
- [ ] Layer packages are accessible
- [ ] Function executes with layer dependencies

---

### TC-005: Function Invocation

| Attribute | Value |
|-----------|-------|
| ID | TC-005 |
| Name | Function invocation |
| Priority | Critical |
| Type | Smoke Test |

**Test Steps:**

```bash
# Create test event
cat > test-event.json << EOF
{
  "key1": "value1",
  "key2": 100,
  "source": "acceptance-test"
}
EOF

# Invoke function
hcloud FunctionGraph function invoke \
  --func_urn=FUNCTION_URN \
  --body=@test-event.json
```

**Expected Results:**

- Function executes successfully
- Returns expected response
- Execution logs are captured

**Pass Criteria:**

- [ ] Invocation returns success status
- [ ] Response matches expected format
- [ ] Execution time is within limits
- [ ] No errors in execution logs

---

### TC-006: Trigger Creation

| Attribute | Value |
|-----------|-------|
| ID | TC-006 |
| Name | API Gateway trigger |
| Priority | High |
| Type | Integration Test |

**Test Steps:**

```bash
# Create API trigger
hcloud FunctionGraph trigger create \
  --func_urn=FUNCTION_URN \
  --trigger_type=apig \
  --trigger_data='{
    "group_id": "API_GROUP_ID",
    "env_id": "DEFAULT_ENV",
    "auth": "IAM"
  }'

# Verify trigger
hcloud FunctionGraph trigger list --func_urn=FUNCTION_URN

# Test via HTTP
curl -X POST https://API_ENDPOINT/invoke \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: TOKEN" \
  -d '{"test": "http"}'
```

**Expected Results:**

- Trigger is created successfully
- HTTP endpoint is accessible
- Function is invoked via trigger

**Pass Criteria:**

- [ ] Trigger appears in trigger list
- [ ] HTTP endpoint is valid
- [ ] Function invocation succeeds via trigger

---

### TC-007: Error Handling

| Attribute | Value |
|-----------|-------|
| ID | TC-007 |
| Name | Error handling validation |
| Priority | High |
| Type | Functional Test |

**Test Cases:**

| Scenario | Input | Expected Error |
|----------|-------|----------------|
| Invalid runtime | runtime=InvalidRuntime | Validation error |
| Invalid memory | memory_size=999999 | Validation error |
| Invalid timeout | timeout=9999 | Validation error |
| Invalid handler | handler=invalid | Handler not found |
| Missing code | code_url=invalid | Code not found |

**Pass Criteria:**

- [ ] Appropriate error messages returned
- [ ] No resource created on validation failure
- [ ] Error codes match API documentation

---

### TC-008: Update Function

| Attribute | Value |
|-----------|-------|
| ID | TC-008 |
| Name | Update function configuration |
| Priority | High |
| Type | Functional Test |

**Test Steps:**

```bash
# Update memory size
hcloud FunctionGraph function update \
  --func_urn=FUNCTION_URN \
  --memory_size=512

# Verify update
hcloud FunctionGraph function show \
  --func_urn=FUNCTION_URN \
  --cli-query="memory_size"
```

**Expected Results:**

- Configuration is updated
- New configuration is active

**Pass Criteria:**

- [ ] Memory size updated to 512
- [ ] Other configurations unchanged
- [ ] Status remains ACTIVE

## Success Standards

### Functional Requirements

| Requirement | Metric | Threshold |
|-------------|--------|-----------|
| Function creation success rate | Percentage | ≥ 99% |
| Function invocation success rate | Percentage | ≥ 99.5% |
| Configuration accuracy | Percentage | 100% |
| Error handling completeness | Percentage | 100% |

### Performance Requirements

| Metric | Unit | Acceptable | Good | Excellent |
|--------|------|------------|------|-----------|
| Cold start latency | ms | < 1000 | < 500 | < 200 |
| Warm invocation latency | ms | < 200 | < 100 | < 50 |
| API response time | ms | < 5000 | < 2000 | < 1000 |
| Throughput | req/sec | ≥ 10 | ≥ 50 | ≥ 100 |

### Security Requirements

| Requirement | Description | Verification |
|-------------|-------------|--------------|
| Authentication | Valid AK/SK required | Verify with invalid credentials |
| Authorization | IAM permissions enforced | Verify with limited permissions |
| Data encryption | HTTPS enforced | Verify HTTP is rejected |
| Input validation | Invalid input rejected | TC-007 tests |
| Secrets management | Sensitive data masked | Verify in logs |

### Reliability Requirements

| Requirement | Metric | Target |
|-------------|--------|--------|
| Availability | Uptime | ≥ 99.9% |
| Retry success | Percentage | ≥ 95% |
| Graceful degradation | Error handling | All paths covered |

## Test Execution Matrix

### Environment Coverage

| Region | Runtime | VPC | Priority |
|--------|---------|-----|----------|
| cn-north-4 | Python3.9 | No | Critical |
| cn-north-4 | Python3.9 | Yes | High |
| cn-north-4 | Node.js14.18 | No | High |
| cn-north-4 | Java11 | No | Medium |
| cn-south-1 | Python3.9 | No | Medium |

### Test Suite Execution

```bash
#!/bin/bash
# run_acceptance_tests.sh

echo "=== FunctionGraph Acceptance Test Suite ==="

# Test execution tracking
TOTAL=0
PASSED=0
FAILED=0

run_test() {
  local test_id=$1
  local test_name=$2
  TOTAL=$((TOTAL + 1))
  
  echo ""
  echo "Running $test_id: $test_name"
  
  if execute_test $test_id; then
    PASSED=$((PASSED + 1))
    echo "✓ PASSED"
  else
    FAILED=$((FAILED + 1))
    echo "✗ FAILED"
  fi
}

# Execute test cases
run_test "TC-001" "Basic Function Creation"
run_test "TC-002" "Function with VPC Configuration"
run_test "TC-003" "Function with Environment Variables"
run_test "TC-004" "Function with Layers"
run_test "TC-005" "Function Invocation"
run_test "TC-006" "Trigger Creation"
run_test "TC-007" "Error Handling"
run_test "TC-008" "Update Function"

# Summary
echo ""
echo "=== Test Summary ==="
echo "Total:  $TOTAL"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Pass Rate: $(awk "BEGIN {printf \"%.1f\", ($PASSED/$TOTAL)*100}")%"

# Exit code
if [ $FAILED -gt 0 ]; then
  exit 1
fi
```

## Acceptance Sign-off

### Approval Criteria

| Role | Responsibility | Required |
|------|----------------|----------|
| Test Lead | Test execution completeness | Yes |
| Developer | Code quality approval | Yes |
| Product Owner | Feature acceptance | Yes |
| Security | Security requirements | Yes |

### Sign-off Checklist

- [ ] All critical test cases passed
- [ ] All high-priority test cases passed
- [ ] Performance requirements met
- [ ] Security requirements verified
- [ ] Documentation complete
- [ ] No critical defects remaining
- [ ] Test coverage ≥ 80%
- [ ] Success rate ≥ 95%

## Defect Classification

| Severity | Description | Resolution |
|----------|-------------|------------|
| Critical | Function creation fails | Block release |
| High | Major feature broken | Fix before release |
| Medium | Feature partially working | Fix in next iteration |
| Low | Minor issue, workaround exists | Schedule for fix |

## Reporting

### Test Report Template

```
Test Execution Report
=====================
Date: YYYY-MM-DD
Environment: Production/Staging
Region: cn-north-4

Summary:
- Total Tests: XX
- Passed: XX
- Failed: XX
- Skipped: XX

Details:
[Detailed results for each test case]

Defects:
[List of identified defects]

Recommendations:
[Go/No-Go recommendation]
```

## Related Documentation

- [Test Automation Guide](https://support.huaweicloud.com/intl/en-us/productdesc-functiongraph/functiongraph_01_0001.html)
- [Performance Tuning](https://support.huaweicloud.com/intl/en-us/functiongraph_01_0201.html)
- [Security Best Practices](https://support.huaweicloud.com/intl/en-us/functiongraph_01_0301.html)
