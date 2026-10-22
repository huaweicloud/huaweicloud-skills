# Acceptance Criteria

This document defines the acceptance criteria, test cases, and success standards for the FunctionGraph function management workflow.

## Overview

### Scope

| Component | Description |
|-----------|-------------|
| Feature | FunctionGraph function creation and invocation |
| Platform | Huawei Cloud FunctionGraph |
| Methods | Python SDK |
| Regions | All supported regions |

### Test Categories

| Category | Priority | Coverage |
|----------|----------|----------|
| Smoke Tests | Critical | Core functionality |
| Functional Tests | High | All features |
| Integration Tests | Medium | External integrations |
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

- Python SDK installed (`pip install huaweicloudsdkfunctiongraph`)
- HUAWEI_AK and HUAWEI_SK environment variables set
- Valid runtime code is prepared

**Test Steps:**

```bash
# Step 1: Create function using Python script
cd scripts
python create_function.py create \
  --name test-function-001 \
  --runtime Python3.9 \
  --handler index.handler \
  --code /path/to/main.py \
  --memory 128 \
  --timeout 10

# Step 2: Verify creation via SDK query
python -c "
from huaweicloudsdkfunctiongraph.v2.functiongraph_client import FunctionGraphClient
from huaweicloudsdkfunctiongraph.v2.model import ListFunctionsRequest
# (Client initialization requires credentials)
# Expected: function appears in list
print('Verifying function exists...')
"
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
cd scripts
python create_function.py create \
  --name test-function-vpc \
  --runtime Python3.9 \
  --handler index.handler \
  --code /path/to/main.py \
  --memory 256 \
  --timeout 30 \
  --vpc-id vpc-xxx \
  --subnet-id subnet-xxx \
  --security-group-id sg-xxx
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
cd scripts
python create_function.py create \
  --name test-function-env \
  --runtime Python3.9 \
  --handler index.handler \
  --code /path/to/main.py \
  --memory 128 \
  --timeout 10 \
  --env-vars '{"DB_HOST": "localhost", "DB_PORT": "3306", "DEBUG": "false"}'
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
| Status | ⚠️ Requires separate layer creation skill |

**Note:** Layer configuration during function creation requires the layer to be pre-created. This functionality is handled by the `huawei-cloud-functiongraph-trigger-create` skill for layer-related operations.

---

### TC-005: Function Invocation

| Attribute | Value |
|-----------|-------|
| ID | TC-005 |
| Name | Function invocation |
| Priority | Critical |
| Type | Smoke Test |

**Preconditions:**

- Function exists (created via TC-001 or equivalent)

> **Note**: Replace `PROJECT_ID` in the URN below with your actual project ID
> (same value as `HUAWEI_PROJECT_ID`). The URN uses the real FunctionGraph
> prefix `urn:fss:` and includes the `default` package and `latest` version,
> matching the format returned by the `create` command.

**Test Steps:**

```bash
# Synchronous invocation
cd scripts
python create_function.py invoke \
  --function-urn urn:fss:cn-north-4:PROJECT_ID:function:default:test-function-001:latest \
  --body '{"key1": "value1", "key2": 100, "source": "acceptance-test"}'

# Asynchronous invocation
python create_function.py invoke \
  --function-urn urn:fss:cn-north-4:PROJECT_ID:function:default:test-function-001:latest \
  --body '{"async": true}' \
  --invocation-type async
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

### TC-006: Error Handling

| Attribute | Value |
|-----------|-------|
| ID | TC-006 |
| Name | Error handling validation |
| Priority | High |
| Type | Functional Test |

**Test Cases:**

| Scenario | Input | Expected Error |
|----------|-------|----------------|
| Invalid runtime | --runtime=InvalidRuntime | Validation error |
| Invalid memory | --memory=999999 | Validation error |
| Invalid timeout | --timeout=9999 | Validation error |
| Invalid handler | --handler=invalid | Handler not found |
| Missing code | No --code | Error: argument --code is required |
| Invalid env vars | --env-vars='not-json' | JSON decode error |
| Partial VPC params | Only --vpc-id (no subnet/security group) | Error: VPC configuration requires all three parameters |
| Invoke non-existent URN | Wrong --function-urn | Function not found |

**Pass Criteria:**

- [ ] Appropriate error messages returned
- [ ] No resource created on validation failure
- [ ] Error codes match API documentation

---

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
| Input validation | Invalid input rejected | TC-006 tests |
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
run_test "TC-005" "Function Invocation"
run_test "TC-006" "Error Handling"

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