# ELB Monitoring Skill Verification Method

## Overview

This document outlines the verification methods for the Huawei Cloud ELB Monitoring skill. Proper verification ensures the skill functions correctly and provides accurate monitoring data.

## Verification Levels

### Level 1: Environment Verification

**Objective**: Verify the Huawei Cloud CLI is properly installed and configured.

**Verification Steps:**

1. **Check CLI Installation**

   ```bash
   hcloud version
   ```

   **Expected Result**: CLI version information displayed without errors.

2. **Verify Configuration**

   ```bash
   hcloud configure list
   ```

   **Expected Result**: Configuration details shown including AK, region, and output format.

3. **Test Basic Connectivity**

   ```bash
   hcloud IAM KeystoneListUsers  --cli-region=<region-id>
   ```

   **Expected Result**: User information returned without permission errors.

**Success Criteria**:

- CLI installed and accessible
- Valid credentials configured
- Basic API calls succeed

### Level 2: Permission Verification

**Objective**: Verify IAM permissions are sufficient for ELB monitoring.

**Verification Steps:**

1. **Test ELB List Permissions**

   ```bash
   hcloud ELB ListLoadBalancers --cli-region=<region-id> --limit=1
   ```

   **Expected Result**: List of ELB instances returned or empty array if none exist.

2. **Test CES Metric Permissions**

   ```bash
   hcloud CES ListMetrics --namespace="SYS.ELB" --cli-region=<region-id> --limit=1
   ```

   **Expected Result**: List of ELB metrics returned.

3. **Test Metric Data Permissions**

   ```bash
   # First get an ELB instance ID
   ELB_ID=$(hcloud ELB ListLoadBalancers --cli-region=<region-id> --limit=1 --cli-query="loadbalancers[0].id" --cli-output=tsv)
   
   if [ -n "$ELB_ID" ] && [ "$ELB_ID" != "None" ]; then
     hcloud CES BatchListMetricData \
       --metrics.1.namespace="SYS.ELB" \
       --metrics.1.metric_name="m1_cps" \
       --metrics.1.dimensions.1.name="lbaas_instance_id" \
       --metrics.1.dimensions.1.value="$ELB_ID" \
       --from=$(date -d '-5 minutes' +%s)000 \
       --to=$(date +%s)000 \
       --period=60 \
       --filter="average" \
       --cli-region=<region-id>
   else
     echo "No ELB instances found, skipping metric data test"
   fi
   ```

   **Expected Result**: Metric data returned or empty array if no data.

**Success Criteria**:

- All required IAM permissions are granted
- No "Access denied" or "Insufficient permissions" errors
- Can list ELB instances and query metrics

### Level 3: Function Verification

**Objective**: Verify core monitoring functionality works correctly.

**Verification Steps:**

1. **Verify ELB Type Detection**

   ```bash
   # Test Dedicated ELB metrics (if available)
   hcloud CES ListMetrics \
     --namespace="SYS.ELB" \
     --metric_name="elb_http_5xx" \
     --cli-region=<region-id> \
     --limit=1
   ```

   **Expected Result**: Either metrics returned or empty array (depending on ELB type).

2. **Verify Shared ELB Metrics**

   ```bash
   # Test basic metrics that should work for all ELB types
   hcloud CES ListMetrics \
     --namespace="SYS.ELB" \
     --metric_name="m1_cps" \
     --cli-region=<region-id> \
     --limit=1
   ```

   **Expected Result**: `m1_cps` metric definition returned.

3. **Verify Time Range Queries**

   ```bash
   # Test different time ranges
   for hours in 1 6 24; do
     echo "Testing $hours hour time range:"
     hcloud CES BatchListMetricData \
       --metrics.1.namespace="SYS.ELB" \
       --metrics.1.metric_name="m1_cps" \
       --metrics.1.dimensions.1.name="lbaas_instance_id" \
       --metrics.1.dimensions.1.value="$ELB_ID" \
       --from=$(date -d "-$hours hours" +%s)000 \
       --to=$(date +%s)000 \
       --period=300 \
       --filter="average" \
       --cli-region=<region-id> \
       --cli-query="datapoints[0]" \
       --cli-output=tsv 2>/dev/null || echo "No data for $hours hours"
   done
   ```

   **Expected Result**: Data returned for valid time ranges.

**Success Criteria**:

- Can query metrics for different ELB types
- Time range queries work correctly
- Metric data retrieval functions properly

### Level 4: Error Handling Verification

**Objective**: Verify error handling works correctly.

**Verification Steps:**

1. **Test Invalid ELB ID**

   ```bash
   hcloud CES BatchListMetricData \
     --metrics.1.namespace="SYS.ELB" \
     --metrics.1.metric_name="m1_cps" \
     --metrics.1.dimensions.1.name="lbaas_instance_id" \
     --metrics.1.dimensions.1.value="invalid-elb-id" \
     --from=$(date -d '-1 hour' +%s)000 \
     --to=$(date +%s)000 \
     --period=300 \
     --filter="average" \
     --cli-region=<region-id>
   ```

   **Expected Result**: Appropriate error message or empty result.

2. **Test Invalid Time Range**

   ```bash
   hcloud CES BatchListMetricData \
     --metrics.1.namespace="SYS.ELB" \
     --metrics.1.metric_name="m1_cps" \
     --metrics.1.dimensions.1.name="lbaas_instance_id" \
     --metrics.1.dimensions.1.value="$ELB_ID" \
     --from=$(date +%s)000 \
     --to=$(date -d '-1 hour' +%s)000 \
     --period=300 \
     --filter="average" \
     --cli-region=<region-id>
   ```

   **Expected Result**: Error about invalid time range.

3. **Test Missing Parameters**

   ```bash
   hcloud CES BatchListMetricData \
     --metrics.1.namespace="SYS.ELB" \
     --metrics.1.metric_name="m1_cps" \
     --cli-region=<region-id>
   ```

   **Expected Result**: Error about missing required parameters.

**Success Criteria**:

- Errors are handled gracefully
- User receives clear error messages
- Skill doesn't crash on invalid input

## Test Scenarios

### Scenario 1: Basic Monitoring Test

**Objective**: Verify basic ELB monitoring functionality.

**Test Steps:**

1. List available ELB instances
2. Select one ELB for testing
3. Query basic metrics (connections, bandwidth)
4. Verify data format and completeness

**Verification Script:**

```bash
#!/bin/bash

REGION="cn-north-4"

echo "=== Basic ELB Monitoring Test ==="

# Step 1: List ELB instances
echo "1. Listing ELB instances..."
ELB_LIST=$(hcloud ELB ListLoadBalancers --cli-region=$REGION --limit=5)
echo "ELB instances found:"
echo "$ELB_LIST" | jq -r '.loadbalancers[] | "\(.name) (\(.id))"' 2>/dev/null || echo "$ELB_LIST"

# Step 2: Get first ELB ID
ELB_ID=$(echo "$ELB_LIST" | jq -r '.loadbalancers[0].id' 2>/dev/null)

if [ -n "$ELB_ID" ] && [ "$ELB_ID" != "null" ]; then
    echo "2. Testing ELB: $ELB_ID"
    
    # Step 3: Query connection metrics
    echo "3. Querying connection metrics..."
    hcloud CES BatchListMetricData \
      --metrics.1.namespace="SYS.ELB" \
      --metrics.1.metric_name="m1_cps" \
      --metrics.1.dimensions.1.name="lbaas_instance_id" \
      --metrics.1.dimensions.1.value="$ELB_ID" \
      --from=$(date -d '-1 hour' +%s)000 \
      --to=$(date +%s)000 \
      --period=300 \
      --filter="average" \
      --cli-region=$REGION \
      --cli-query="length(datapoints)" \
      --cli-output=tsv
    
    # Step 4: Query bandwidth metrics
    echo "4. Querying bandwidth metrics..."
    hcloud CES BatchListMetricData \
      --metrics.1.namespace="SYS.ELB" \
      --metrics.1.metric_name="m7_in_Bps" \
      --metrics.1.dimensions.1.name="lbaas_instance_id" \
      --metrics.1.dimensions.1.value="$ELB_ID" \
      --from=$(date -d '-1 hour' +%s)000 \
      --to=$(date +%s)000 \
      --period=300 \
      --filter="average" \
      --cli-region=$REGION \
      --cli-query="length(datapoints)" \
      --cli-output=tsv
    
    echo "✓ Basic monitoring test passed"
else
    echo "⚠ No ELB instances found for testing"
fi
```

### Scenario 2: Dedicated ELB Advanced Test

**Objective**: Verify advanced metrics for Dedicated ELB.

**Test Steps:**

1. Identify Dedicated ELB instances
2. Test HTTP metrics availability
3. Test backend server group metrics
4. Test traffic mirroring metrics (if configured)

**Verification Script:**

```bash
#!/bin/bash

REGION="cn-north-4"

echo "=== Dedicated ELB Advanced Test ==="

# Find Dedicated ELB instances
echo "Looking for Dedicated ELB instances..."
DEDICATED_ELBS=$(hcloud ELB ListLoadBalancers --cli-region=$REGION --cli-query="loadbalancers[?guaranteed=='true']" --cli-output=json)

ELB_COUNT=$(echo "$DEDICATED_ELBS" | jq -r 'length')

if [ "$ELB_COUNT" -gt 0 ]; then
    echo "Found $ELB_COUNT Dedicated ELB instance(s)"
    
    # Test HTTP metrics on first Dedicated ELB
    ELB_ID=$(echo "$DEDICATED_ELBS" | jq -r '.[0].id')
    echo "Testing HTTP metrics for ELB: $ELB_ID"
    
    # Test HTTP 5xx metric
    echo "Testing HTTP 5xx metric..."
    HTTP_RESULT=$(hcloud CES ListMetrics \
      --namespace="SYS.ELB" \
      --metric_name="elb_http_5xx" \
      --dim.0="lbaas_instance_id,$ELB_ID" \
      --cli-region=$REGION \
      --limit=1 \
      --cli-output=json 2>/dev/null)
    
    if echo "$HTTP_RESULT" | jq -e '.metrics | length > 0' >/dev/null 2>&1; then
        echo "✓ HTTP metrics available for Dedicated ELB"
        
        # Test actual metric query
        hcloud CES BatchListMetricData \
          --metrics.1.namespace="SYS.ELB" \
          --metrics.1.metric_name="elb_http_5xx" \
          --metrics.1.dimensions.1.name="lbaas_instance_id" \
          --metrics.1.dimensions.1.value="$ELB_ID" \
          --from=$(date -d '-1 hour' +%s)000 \
          --to=$(date +%s)000 \
          --period=300 \
          --filter="average" \
          --cli-region=$REGION \
          --cli-query="length(datapoints)" \
          --cli-output=tsv
        
        echo "✓ HTTP metric query successful"
    else
        echo "⚠ HTTP metrics not available (may be no HTTP listeners)"
    fi
else
    echo "No Dedicated ELB instances found"
fi
```

### Scenario 3: Shared ELB Basic Test

**Objective**: Verify basic metrics for Shared ELB.

**Test Steps:**

1. Identify Shared ELB instances
2. Test basic connection metrics
3. Test basic traffic metrics
4. Verify HTTP metrics are not available

**Verification Script:**

```bash
#!/bin/bash

REGION="cn-north-4"

echo "=== Shared ELB Basic Test ==="

# Find Shared ELB instances
echo "Looking for Shared ELB instances..."
SHARED_ELBS=$(hcloud ELB ListLoadBalancers --cli-region=$REGION --cli-query="loadbalancers[?guaranteed=='false']" --cli-output=json)

ELB_COUNT=$(echo "$SHARED_ELBS" | jq -r 'length')

if [ "$ELB_COUNT" -gt 0 ]; then
    echo "Found $ELB_COUNT Shared ELB instance(s)"
    
    # Test basic metrics on first Shared ELB
    ELB_ID=$(echo "$SHARED_ELBS" | jq -r '.[0].id')
    echo "Testing basic metrics for ELB: $ELB_ID"
    
    # Test that basic metrics work
    echo "Testing connection metrics..."
    hcloud CES BatchListMetricData \
      --metrics.1.namespace="SYS.ELB" \
      --metrics.1.metric_name="m1_cps" \
      --metrics.1.dimensions.1.name="lbaas_instance_id" \
      --metrics.1.dimensions.1.value="$ELB_ID" \
      --from=$(date -d '-1 hour' +%s)000 \
      --to=$(date +%s)000 \
      --period=300 \
      --filter="average" \
      --cli-region=$REGION \
      --cli-query="length(datapoints)" \
      --cli-output=tsv
    
    echo "✓ Basic metrics work for Shared ELB"
    
    # Test that HTTP metrics are not available
    echo "Verifying HTTP metrics are not available for Shared ELB..."
    HTTP_METRICS=$(hcloud CES ListMetrics \
      --namespace="SYS.ELB" \
      --metric_name="elb_http_5xx" \
      --dim.0="lbaas_instance_id,$ELB_ID" \
      --cli-region=$REGION \
      --limit=1 \
      --cli-output=json 2>/dev/null)
    
    if echo "$HTTP_METRICS" | jq -e '.metrics | length == 0' >/dev/null 2>&1; then
        echo "✓ HTTP metrics correctly not available for Shared ELB"
    else
        echo "⚠ Unexpected: HTTP metrics available for Shared ELB"
    fi
else
    echo "No Shared ELB instances found"
fi
```

## Validation Checklist

### Pre-requisites Validation

- [ ] Huawei Cloud CLI installed and accessible
- [ ] Valid credentials configured
- [ ] Sufficient IAM permissions granted
- [ ] ELB instances exist in the region
- [ ] Network connectivity to Huawei Cloud APIs

### Basic Functionality Validation

- [ ] Can list ELB instances
- [ ] Can query basic metrics (connections, bandwidth)
- [ ] Time range queries work correctly
- [ ] Different aggregation methods work (average, max, min, sum)
- [ ] Error handling works for invalid inputs

### Advanced Functionality Validation (Dedicated ELB)

- [ ] HTTP metrics available and queryable
- [ ] Backend server group metrics available
- [ ] Traffic mirroring metrics available (if configured)
- [ ] Listener-level metrics work correctly

### Performance Validation

- [ ] Query response time < 5 seconds for basic metrics
- [ ] Query response time < 10 seconds for complex queries
- [ ] Can handle multiple concurrent metric queries
- [ ] Memory usage stays within reasonable limits

### Security Validation

- [ ] No sensitive data exposure in error messages
- [ ] Credentials not logged or exposed
- [ ] API calls use secure connections
- [ ] Rate limiting respected

## Test Data Preparation

### Creating Test ELB Instances

For comprehensive testing, create test ELB instances:

1. **Dedicated ELB Test Instance**
   - Create a Dedicated ELB with HTTP/HTTPS listeners
   - Configure backend servers
   - Generate test traffic

2. **Shared ELB Test Instance**
   - Create a Shared ELB with basic listeners
   - Configure backend servers
   - Generate test traffic

3. **Test Traffic Generation**

   ```bash
   # Generate test traffic using curl or similar tools
   # This helps create monitoring data for testing
   for i in {1..100}; do
     curl -s http://<elb-ip> > /dev/null
     sleep 0.1
   done
   ```

### Test Data Verification

```bash
# Verify test data is being collected
echo "Verifying test data collection..."

# Wait for metrics to be available
sleep 60

# Check if metrics are being collected
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m1_cps" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="$TEST_ELB_ID" \
  --from=$(date -d '-5 minutes' +%s)000 \
  --to=$(date +%s)000 \
  --period=60 \
  --filter="average" \
  --cli-region=$REGION \
  --cli-query="datapoints[].average" \
  --cli-output=tsv
```

## Troubleshooting Verification Issues

### Issue: No Metrics Data

**Symptoms**: Queries return empty results
**Solutions**:

1. Verify ELB instance is in "ACTIVE" state
2. Check if traffic is flowing through ELB
3. Wait 1-2 minutes for initial data collection
4. Verify correct metric names and dimensions

### Issue: Permission Errors

**Symptoms**: "Access denied" or "Insufficient permissions"
**Solutions**:

1. Verify IAM policies are attached
2. Check if policies have correct permissions
3. Verify region matches ELB instance region
4. Check if project ID is correct

### Issue: Invalid Parameters

**Symptoms**: "Invalid parameter" errors
**Solutions**:

1. Verify parameter names and formats
2. Check timestamp format (Unix milliseconds)
3. Verify dimension names and values
4. Check metric namespace and name

### Issue: Timeout Errors

**Symptoms**: Requests timeout
**Solutions**:

1. Increase timeout settings
2. Reduce query time range
3. Query fewer metrics at once
4. Check network connectivity

## Automation Testing

### Automated Test Script

Create an automated test script for continuous validation:

```bash
#!/bin/bash
# automated-elb-monitoring-test.sh

REGION=${1:-"cn-north-4"}
TEST_RESULTS="/tmp/elb-monitoring-test-$(date +%Y%m%d-%H%M%S).log"

echo "ELB Monitoring Automated Test - $(date)" > "$TEST_RESULTS"
echo "========================================" >> "$TEST_RESULTS"

# Test 1: CLI and Configuration
echo "Test 1: CLI and Configuration" >> "$TEST_RESULTS"
if hcloud version >> "$TEST_RESULTS" 2>&1; then
    echo "✓ CLI installed" >> "$TEST_RESULTS"
else
    echo "✗ CLI not installed" >> "$TEST_RESULTS"
    exit 1
fi

# Test 2: List ELB Instances
echo -e "\nTest 2: List ELB Instances" >> "$TEST_RESULTS"
ELB_LIST=$(hcloud ELB ListLoadBalancers --cli-region=$REGION --limit=2 --cli-output=json 2>&1)
if echo "$ELB_LIST" | jq -e '.loadbalancers' >/dev/null 2>&1; then
    ELB_COUNT=$(echo "$ELB_LIST" | jq -r '.loadbalancers | length')
    echo "✓ Found $ELB_COUNT ELB instance(s)" >> "$TEST_RESULTS"
    
    # Test 3: Query Metrics
    if [ "$ELB_COUNT" -gt 0 ]; then
        ELB_ID=$(echo "$ELB_LIST" | jq -r '.loadbalancers[0].id')
        echo -e "\nTest 3: Query Metrics for $ELB_ID" >> "$TEST_RESULTS"
        
        METRIC_RESULT=$(hcloud CES BatchListMetricData \
          --metrics.1.namespace="SYS.ELB" \
          --metrics.1.metric_name="m1_cps" \
          --metrics.1.dimensions.1.name="lbaas_instance_id" \
          --metrics.1.dimensions.1.value="$ELB_ID" \
          --from=$(date -d '-5 minutes' +%s)000 \
          --to=$(date +%s)000 \
          --period=60 \
          --filter="average" \
          --cli-region=$REGION \
          --cli-output=json 2>&1)
        
        if echo "$METRIC_RESULT" | jq -e '.datapoints' >/dev/null 2>&1; then
            echo "✓ Metric query successful" >> "$TEST_RESULTS"
        else
            echo "✗ Metric query failed: $METRIC_RESULT" >> "$TEST_RESULTS"
        fi
    fi
else
    echo "✗ Failed to list ELB instances: $ELB_LIST" >> "$TEST_RESULTS"
fi

echo -e "\nTest completed. Results saved to: $TEST_RESULTS"
cat "$TEST_RESULTS"
```

## Performance Benchmarks

### Expected Performance

- **CLI Response Time**: < 2 seconds for simple queries
- **Metric Query Time**: < 5 seconds for 1-hour range
- **Data Processing Time**: < 1 second for basic aggregation
- **Memory Usage**: < 100MB for typical operations

### Load Testing

```bash
# Simulate multiple concurrent queries
for i in {1..10}; do
  (hcloud CES BatchListMetricData \
    --metrics.1.namespace="SYS.ELB" \
    --metrics.1.metric_name="m1_cps" \
    --metrics.1.dimensions.1.name="lbaas_instance_id" \
    --metrics.1.dimensions.1.value="$ELB_ID" \
    --from=$(date -d '-1 hour' +%s)000 \
    --to=$(date +%s)000 \
    --period=300 \
    --filter="average" \
    --cli-region=$REGION \
    --cli-output=json > /dev/null 2>&1 &
  ) &
done

wait
echo "Concurrent query test completed"
```

## Documentation

### Test Results Documentation

Document test results including:

- Test environment details
- Test cases executed
- Results and observations
- Issues encountered and resolutions
- Performance metrics

### Known Issues and Workarounds

Maintain a list of known issues:

1. **Issue**: HTTP metrics not available for Shared ELB
   **Workaround**: Only query basic metrics for Shared ELB

2. **Issue**: No data for newly created ELB
   **Workaround**: Wait 2-3 minutes for initial data collection

3. **Issue**: Timezone differences in timestamps
   **Workaround**: Use UTC timestamps consistently

### Regression Testing

Establish regression test suite:

- Run after CLI updates
- Run after IAM policy changes
- Run before production deployment
- Run periodically (weekly/monthly)

## Conclusion

Proper verification ensures the ELB monitoring skill:

1. Functions correctly in all scenarios
2. Handles errors gracefully
3. Provides accurate monitoring data
4. Meets performance requirements
5. Maintains security standards

Regular verification should be part of the development and deployment process to ensure ongoing reliability and accuracy.
