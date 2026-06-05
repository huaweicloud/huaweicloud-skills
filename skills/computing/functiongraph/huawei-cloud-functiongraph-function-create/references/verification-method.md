# Verification Methods

This document provides comprehensive verification methods for FunctionGraph function creation, status checking, and functional testing.

## Function Creation Verification

### Step 1: Verify Function Existence

```bash
# List all functions
hcloud FunctionGraph function list \
  --cli-region=cn-north-4 \
  --cli-query="functions[?func_name=='YOUR_FUNCTION_NAME']"

# Get specific function details
hcloud FunctionGraph function show \
  --func_urn=urn:fg:cn-north-4:PROJECT_ID:function:FUNCTION_NAME:latest
```

### Expected Output

```json
{
  "func_urn": "urn:fg:cn-north-4:project-123:function:my-function:latest",
  "func_name": "my-function",
  "runtime": "Python3.9",
  "handler": "index.handler",
  "memory_size": 256,
  "timeout": 30,
  "code_type": "Zip",
  "code_url": "https://obs.bucket/code.zip",
  "status": "ACTIVE"
}
```

### Step 2: Verify Function Configuration

| Parameter | Verification Method | Expected Result |
|-----------|---------------------|-----------------|
| func_name | Check in list output | Matches specified name |
| runtime | Validate runtime value | Supported runtime version |
| memory_size | Compare with config | 128-4096 MB range |
| timeout | Compare with config | 1-900 seconds range |
| handler | Verify entry point | Correct file:function format |
| status | Check state | ACTIVE or PENDING |

## Status Checking

### Function Status Values

| Status | Description | Action Required |
|--------|-------------|-----------------|
| ACTIVE | Function is operational | None |
| PENDING | Creation in progress | Wait for completion |
| FAILED | Creation failed | Check error logs |
| DELETING | Deletion in progress | Wait for completion |
| INACTIVE | Function is disabled | Enable if needed |

### Status Check Commands

```bash
# Get function status
hcloud FunctionGraph function show \
  --func_urn=FUNCTION_URN \
  --cli-query="status"

# Monitor status with retry
for i in {1..10}; do
  status=$(hcloud FunctionGraph function show --func_urn=FUNCTION_URN --cli-query="status")
  if [ "$status" == '"ACTIVE"' ]; then
    echo "Function is ACTIVE"
    break
  fi
  echo "Status: $status, retrying... ($i/10)"
  sleep 5
done
```

### Version and Alias Status

```bash
# List function versions
hcloud FunctionGraph version list \
  --func_urn=FUNCTION_URN

# List function aliases
hcloud FunctionGraph alias list \
  --func_urn=FUNCTION_URN

# Verify alias points to correct version
hcloud FunctionGraph alias show \
  --func_urn=FUNCTION_URN \
  --alias_name=prod
```

## Functional Testing

### Test Method 1: Synchronous Invocation

```bash
# Invoke function with test event
hcloud FunctionGraph function invoke \
  --func_urn=FUNCTION_URN \
  --body='{
    "test": "data",
    "source": "verification"
  }'

# Invoke with file input
hcloud FunctionGraph function invoke \
  --func_urn=FUNCTION_URN \
  --body=@test-event.json
```

### Test Method 2: Asynchronous Invocation

```bash
# Invoke asynchronously
hcloud FunctionGraph function invoke \
  --func_urn=FUNCTION_URN \
  --invocation_type=Async \
  --body='{"async": true}'

# Check invocation result
# Note: Requires OBS or DIS for async result storage
```

### Test Method 3: API Gateway Trigger

```bash
# Create test API trigger
hcloud FunctionGraph trigger create \
  --func_urn=FUNCTION_URN \
  --trigger_type=apig \
  --trigger_data='{
    "group_id": "API_GROUP_ID",
    "env_id": "ENV_ID",
    "auth": "NONE"
  }'

# Test via HTTP request
curl -X POST https://API_ENDPOINT/path \
  -H "Content-Type: application/json" \
  -d '{"test": "http"}'
```

## Verification Checklist

### Pre-Creation Verification

| Check | Command | Expected Result |
|-------|---------|-----------------|
| CLI installed | `hcloud version` | Version displayed |
| Credentials configured | `hcloud configure list` | AK/SK present |
| Region accessible | `hcloud FunctionGraph function list --cli-region=REGION` | No error |
| IAM permissions | Test create operation | Permission granted |

### Post-Creation Verification

| Check | Command | Expected Result |
|-------|---------|-----------------|
| Function exists | List functions | Function in list |
| Status active | Show function | Status: ACTIVE |
| Configuration correct | Show function | All params match |
| Code uploaded | Check code_size | Size > 0 |
| Handler valid | Test invocation | No handler error |

### Integration Verification

| Check | Description | Method |
|-------|-------------|--------|
| VPC connectivity | Verify VPC config | Show function VPC settings |
| Network access | Test outbound calls | Invoke with network test |
| OBS access | Read from OBS | Invoke with OBS operation |
| Database access | Query database | Invoke with DB query |

## Automated Verification Script

```bash
#!/bin/bash
# verify_function.sh - Automated function verification

FUNC_URN=$1
REGION=${2:-"cn-north-4"}

echo "=== Function Verification Script ==="
echo "Function URN: $FUNC_URN"
echo "Region: $REGION"
echo ""

# Check 1: Function exists
echo "[1/6] Checking function existence..."
result=$(hcloud FunctionGraph function show --func_urn=$FUNC_URN --cli-region=$REGION 2>&1)
if echo "$result" | grep -q "func_name"; then
  echo "✓ Function exists"
else
  echo "✗ Function not found"
  exit 1
fi

# Check 2: Status is ACTIVE
echo "[2/6] Checking function status..."
status=$(hcloud FunctionGraph function show --func_urn=$FUNC_URN --cli-region=$REGION --cli-query="status")
if [ "$status" == '"ACTIVE"' ]; then
  echo "✓ Function is ACTIVE"
else
  echo "✗ Function status: $status"
  exit 1
fi

# Check 3: Runtime verification
echo "[3/6] Verifying runtime..."
runtime=$(hcloud FunctionGraph function show --func_urn=$FUNC_URN --cli-region=$REGION --cli-query="runtime")
echo "✓ Runtime: $runtime"

# Check 4: Memory and timeout
echo "[4/6] Verifying configuration..."
memory=$(hcloud FunctionGraph function show --func_urn=$FUNC_URN --cli-region=$REGION --cli-query="memory_size")
timeout=$(hcloud FunctionGraph function show --func_urn=$FUNC_URN --cli-region=$REGION --cli-query="timeout")
echo "✓ Memory: $memory MB, Timeout: $timeout seconds"

# Check 5: Test invocation
echo "[5/6] Testing function invocation..."
invocation=$(hcloud FunctionGraph function invoke --func_urn=$FUNC_URN --body='{"verification": true}' 2>&1)
if echo "$invocation" | grep -q "error"; then
  echo "✗ Invocation failed: $invocation"
else
  echo "✓ Invocation successful"
fi

# Check 6: Version info
echo "[6/6] Checking version information..."
version=$(hcloud FunctionGraph function show --func_urn=$FUNC_URN --cli-region=$REGION --cli-query="version")
echo "✓ Version: $version"

echo ""
echo "=== Verification Complete ==="
```

## Performance Verification

### Cold Start Performance

```bash
# Measure cold start time
start_time=$(date +%s%N)
hcloud FunctionGraph function invoke --func_urn=FUNCTION_URN --body='{"test": "cold"}'
end_time=$(date +%s%N)
cold_start_ms=$(( (end_time - start_time) / 1000000 ))
echo "Cold start time: ${cold_start_ms}ms"
```

### Warm Invocation Performance

```bash
# Measure warm invocation time (after initial invocation)
for i in {1..10}; do
  start=$(date +%s%N)
  hcloud FunctionGraph function invoke --func_urn=FUNCTION_URN --body='{"test": "warm"}' > /dev/null
  end=$(date +%s%N)
  echo "Invocation $i: $(( (end - start) / 1000000 ))ms"
done
```

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Cold start | < 500ms | Time to first response |
| Warm invocation | < 100ms | Average of 10 invocations |
| Memory usage | Within limit | Function metrics in console |
| Init duration | < 200ms | Check execution logs |

## Logging and Debugging

### View Function Logs

```bash
# Query recent function logs via LTS
hcloud LTS logs query \
  --log_group_id=LOG_GROUP_ID \
  --log_stream_id=LOG_STREAM_ID \
  --start_time="2024-01-01 00:00:00" \
  --end_time="2024-01-01 23:59:59"
```

### Enable Debug Logging

```bash
# Invoke with environment variable for debug
hcloud FunctionGraph function update \
  --func_urn=FUNCTION_URN \
  --environment_variables='{"DEBUG": "true", "LOG_LEVEL": "debug"}'
```

## Related Documentation

- [FunctionGraph API Reference](https://support.huaweicloud.com/intl/en-us/api-functiongraph/functiongraph_06_0101.html)
- [Function Testing Guide](https://support.huaweicloud.com/intl/en-us/usermanual-functiongraph/functiongraph_01_0101.html)
- [Performance Optimization](https://support.huaweicloud.com/intl/en-us/functiongraph_01_0201.html)
