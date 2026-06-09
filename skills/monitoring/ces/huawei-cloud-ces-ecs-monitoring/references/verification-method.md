# Huawei Cloud ECS Monitoring Skill Verification Method

## Overview

This document describes the verification methods for ensuring the Huawei Cloud ECS Monitoring
skill functions correctly and meets quality standards. Verification includes functional testing,
integration testing, and user acceptance testing.

## Verification Environment

### 1. Test Environment Setup

```bash
# Prerequisites
- Huawei Cloud account with active subscription
- At least one running ECS instance
- Huawei Cloud CLI (hcloud) installed and configured
- Proper IAM permissions (see iam-policies.md)

# Environment variables for testing
export HUAWEICLOUD_REGION="cn-north-4"  # Test region
export TEST_INSTANCE_ID="<instance-uuid>"  # Test ECS instance UUID
export TEST_METRIC_NAME="cpu_util"  # Test metric (SYS.ECS)
```

### 2. Test Data Requirements

- ECS instance must be in "ACTIVE" state
- Instance should have been running for at least 30 minutes to generate metrics
- CES agent must be installed and running on the instance (for AGT.ECS metrics)
- Sufficient monitoring data should be available (at least 1 hour of data)

## Functional Verification

### 1. Prerequisite Verification

```bash
# Test 1: Verify Huawei Cloud CLI installation
hcloud --version
# Expected: CLI version information displayed without errors

# Test 2: Verify CLI configuration
hcloud configure list
# Expected: Valid credentials and region configuration displayed

# Test 3: Verify authentication
hcloud IAM ShowUser
# Expected: User information displayed without authentication errors
```

### 2. ECS Instance Listing Verification

```bash
# Test 4: List ECS instances
hcloud ECS NovaListServers --cli-region=$HUAWEICLOUD_REGION --limit=50
# Expected: JSON array of ECS instances, including test instance

# Test 5: Get specific instance details
hcloud ECS NovaShowServer --server_id=$TEST_INSTANCE_ID --cli-region=$HUAWEICLOUD_REGION
# Expected: Detailed information about the test instance
```

### 3. CES Metrics Verification

```bash
# Test 6: List available metrics
hcloud CES ListMetrics --namespace=SYS.ECS --dim.0="instance_id,$TEST_INSTANCE_ID" --cli-region=$HUAWEICLOUD_REGION
# Expected: List of available metrics for the instance

# Test 7: Query metric data (SYS.ECS - cpu_util)
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

### 4. Common Metrics Verification

```bash
# Test 8: Verify CPU metrics (SYS.ECS)
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$TEST_INSTANCE_ID" \
  --from=$(date -d '30 minutes ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=$HUAWEICLOUD_REGION

# Test 9: Verify memory metrics (SYS.ECS)
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="mem_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$TEST_INSTANCE_ID" \
  --from=$(date -d '30 minutes ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=$HUAWEICLOUD_REGION

# Test 10: Verify disk metrics (SYS.ECS)
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="disk_util_inband" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$TEST_INSTANCE_ID" \
  --from=$(date -d '30 minutes ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=$HUAWEICLOUD_REGION
```

## Integration Verification

### 1. Skill Workflow Verification

```bash
# Test 11: Complete workflow test
# Step 1: List instances
INSTANCES=$(hcloud ECS NovaListServers --cli-region=$HUAWEICLOUD_REGION --limit=50)

# Step 2: Extract instance ID
INSTANCE_ID=$(echo $INSTANCES | jq -r '.servers[0].id')

# Step 3: Query metrics (SYS.ECS)
METRIC_DATA=$(hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$INSTANCE_ID" \
  --metrics.2.namespace="SYS.ECS" \
  --metrics.2.metric_name="mem_util" \
  --metrics.2.dimensions.1.name="instance_id" \
  --metrics.2.dimensions.1.value="$INSTANCE_ID" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=$HUAWEICLOUD_REGION)

# Step 4: Verify data format
echo $METRIC_DATA | jq '.metrics[0].datapoints | length'
# Expected: Positive integer indicating data points retrieved
```

### 2. Error Handling Verification

```bash
# Test 12: Invalid instance ID
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="invalid-uuid" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=$HUAWEICLOUD_REGION
# Expected: Appropriate error message

# Test 13: Invalid time range
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$TEST_INSTANCE_ID" \
  --from=0 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=$HUAWEICLOUD_REGION
# Expected: Appropriate error message

# Test 14: Invalid metric name
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="invalid_metric" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$TEST_INSTANCE_ID" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=$HUAWEICLOUD_REGION
# Expected: Appropriate error message
```

### 3. Performance Verification

```bash
# Test 15: Response time test
time hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$TEST_INSTANCE_ID" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=$HUAWEICLOUD_REGION
# Expected: Response within 5 seconds

# Test 16: Multiple metrics query
time hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$TEST_INSTANCE_ID" \
  --metrics.2.namespace="SYS.ECS" \
  --metrics.2.metric_name="mem_util" \
  --metrics.2.dimensions.1.name="instance_id" \
  --metrics.2.dimensions.1.value="$TEST_INSTANCE_ID" \
  --metrics.3.namespace="SYS.ECS" \
  --metrics.3.metric_name="disk_read_bytes_rate" \
  --metrics.3.dimensions.1.name="instance_id" \
  --metrics.3.dimensions.1.value="$TEST_INSTANCE_ID" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=$HUAWEICLOUD_REGION
# Expected: Response within 10 seconds
```

## Verification Criteria

### 1. Success Criteria

- All functional tests pass (100% success rate)
- Response times meet performance requirements
- Error handling works correctly
- Documentation is complete and accurate
- Cross-platform compatibility verified

### 2. Performance Criteria

- Single metric query: < 5 seconds response time
- Multiple metrics query (6 metrics): < 10 seconds response time
- Instance listing: < 3 seconds response time
- Memory usage: < 100MB for skill execution

### 3. Quality Criteria

- Code coverage: > 80% for core functionality
- Documentation coverage: 100% of features documented
- Error handling: All expected errors handled gracefully
- User experience: Clear, actionable output format

### 4. Security Criteria

- No hardcoded credentials in code
- Proper IAM permission validation
- Secure credential handling
- No sensitive data exposure in logs

## References

- [Huawei Cloud CLI Documentation](https://support.huaweicloud.com/usermanual-hcli/)
- [ECS Monitoring Metrics](https://support.huaweicloud.com/usermanual-ecs/ecs_03_1001.html)
- [CES API Reference](https://support.huaweicloud.com/api-ces/ces_03_0041.html)
- [IAM Policy Documentation](https://support.huaweicloud.com/usermanual-iam/)
