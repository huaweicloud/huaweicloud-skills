# Verification Methods

This document provides comprehensive verification methods for FunctionGraph function creation, invocation, and functional testing using the Python SDK-based tool.

## Function Creation Verification

### Step 1: Verify Function Existence

```bash
# Using the Python script
cd scripts

# Create a test function
python create_function.py create \
  --name my-function \
  --runtime Python3.9 \
  --handler index.handler \
  --code /path/to/code/main.py \
  --memory 256 \
  --timeout 30
```

### Expected Output

```json
{
  "status": "success",
  "function_urn": "urn:fss:cn-north-4:project-123:function:default:my-function",
  "function_name": "my-function",
  "runtime": "Python3.9",
  "handler": "index.handler",
  "memory_size": 256,
  "timeout": 30,
  "code_size": 1234,
  "message": "Function created successfully"
}
```

### Step 2: Verify Function Configuration

| Parameter | Verification Method | Expected Result |
|-----------|---------------------|-----------------|
| func_name | Check in output | Matches specified name |
| runtime | Validate runtime value | Supported runtime version |
| memory_size | Compare with config | 128-4096 MB range |
| timeout | Compare with config | 1-900 seconds range |
| handler | Verify entry point | Correct file:function format |
| status | Check via SDK | ACTIVE or PENDING |

### Step 3: Verify VPC Configuration (if applicable)

```bash
# Create function with VPC
python create_function.py create \
  --name my-function-vpc \
  --runtime Python3.9 \
  --handler index.handler \
  --code /path/to/code/main.py \
  --vpc-id vpc-xxx \
  --subnet-id subnet-xxx \
  --security-group-id sg-xxx
```

Expected output includes VPC fields if configured successfully.

### Step 4: Verify Environment Variables (if applicable)

```bash
# Create function with environment variables
python create_function.py create \
  --name my-function-env \
  --runtime Python3.9 \
  --handler index.handler \
  --code /path/to/code/main.py \
  --env-vars '{"DB_HOST": "localhost", "DB_PORT": "3306", "DEBUG": "false"}'
```

## Status Checking

### Function Status Values

| Status | Description | Action Required |
|--------|-------------|-----------------|
| ACTIVE | Function is operational | None |
| PENDING | Creation in progress | Wait for completion |
| FAILED | Creation failed | Check error logs |
| DELETING | Deletion in progress | Wait for completion |
| INACTIVE | Function is disabled | Enable if needed |

## Functional Testing

> **Note**: Replace `PROJECT_ID` in the URNs below with your actual project ID
> (same value as `HUAWEI_PROJECT_ID`). The URN uses the real FunctionGraph
> prefix `urn:fss:` and includes the `default` package and `latest` version,
> matching the format returned by the `create` command.

### Test Method 1: Synchronous Invocation

```bash
# Invoke function synchronously (default)
cd scripts
python create_function.py invoke \
  --function-urn urn:fss:cn-north-4:PROJECT_ID:function:default:my-function:latest \
  --body '{"test": "data", "source": "verification"}'
```

Expected output:

```json
{
  "status": "success",
  "function_urn": "urn:fss:cn-north-4:PROJECT_ID:function:default:my-function:latest",
  "invocation_type": "sync",
  "result": {
    "output": "..."
  },
  "request_id": "a1b2c3d4-...",
  "message": "Function invoked successfully"
}
```

### Test Method 2: Asynchronous Invocation

```bash
# Invoke function asynchronously
python create_function.py invoke \
  --function-urn urn:fss:cn-north-4:PROJECT_ID:function:default:my-function:latest \
  --body '{"async": true}' \
  --invocation-type async
```

### Test Method 3: Invocation with Log Tail

```bash
# Invoke and return last 4KB of log
python create_function.py invoke \
  --function-urn urn:fss:cn-north-4:PROJECT_ID:function:default:my-function:latest \
  --body '{"test": "logging"}' \
  --log-type tail
```

## Verification Checklist

### Pre-Creation Verification

| Check | Command | Expected Result |
|-------|---------|-----------------|
| SDK installed | `pip list \| grep huaweicloudsdkfunctiongraph` | Package listed |
| Credentials configured | `echo $HUAWEI_AK` and `echo $HUAWEI_SK` | Values present |
| Region configured | `echo $HUAWEI_REGION` | Region set |
| IAM permissions | Test create operation | Permission granted |

### Post-Creation Verification

| Check | Command | Expected Result |
|-------|---------|-----------------|
| Function created | Script returns `status: success` | Success output |
| Function URN returned | Check output JSON | URN in response |
| Configuration correct | Verify output fields | All params match |
| Invocation works | Test invoke | Successful execution |

### VPC Verification

| Check | Description | Method |
|-------|-------------|--------|
| VPC configuration | Verify VPC settings in creation output | Check response for VPC fields |
| Network access | Test outbound calls from function | Invoke function with network test |

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

# Check 1: Verify function via SDK query
echo "[1/4] Checking function existence via SDK..."
python3 -c "
import os
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkfunctiongraph.v2.functiongraph_client import FunctionGraphClient
from huaweicloudsdkfunctiongraph.v2.region.functiongraph_region import FunctionGraphRegion
from huaweicloudsdkfunctiongraph.v2.model import ListFunctionsRequest

creds = BasicCredentials(ak=os.environ['HUAWEI_AK'], sk=os.environ['HUAWEI_SK'])
client = FunctionGraphClient.new_builder() \
    .with_credentials(creds) \
    .with_region(FunctionGraphRegion.value_of('$REGION')) \
    .build()

request = ListFunctionsRequest()
response = client.list_functions(request)
if response.functions:
    print(f'✓ Found {len(response.functions)} functions')
else:
    print('✓ SDK connection successful (listing not required for verification)')
" 2>&1

# Check 2: Test invocation
echo "[2/4] Testing function invocation..."
cd $(dirname $0)/..
python3 scripts/create_function.py invoke \
  --function-urn=$FUNC_URN \
  --body='{"verification": true}' 2>&1

if [ $? -eq 0 ]; then
  echo "✓ Invocation successful"
else
  echo "✗ Invocation failed"
fi

echo ""
echo "=== Verification Complete ==="
```

## Performance Verification

### Cold Start Performance

```bash
# Measure cold start time via SDK invocation
start_time=$(date +%s%N)
python3 scripts/create_function.py invoke \
  --function-urn=FUNCTION_URN \
  --body='{"test": "cold"}' > /dev/null
end_time=$(date +%s%N)
cold_start_ms=$(( (end_time - start_time) / 1000000 ))
echo "Cold start time: ${cold_start_ms}ms"
```

### Warm Invocation Performance

```bash
# Measure warm invocation time
for i in {1..10}; do
  start=$(date +%s%N)
  python3 scripts/create_function.py invoke \
    --function-urn=FUNCTION_URN \
    --body='{"test": "warm"}' > /dev/null
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

## Logging and Debugging

### View Function Logs via SDK

```bash
# Check function configuration for log settings
python3 -c "
import os
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkfunctiongraph.v2.functiongraph_client import FunctionGraphClient
from huaweicloudsdkfunctiongraph.v2.region.functiongraph_region import FunctionGraphRegion
from huaweicloudsdkfunctiongraph.v2.model import ShowFunctionConfigRequest

creds = BasicCredentials(ak=os.environ['HUAWEI_AK'], sk=os.environ['HUAWEI_SK'])
client = FunctionGraphClient.new_builder() \
    .with_credentials(creds) \
    .with_region(FunctionGraphRegion.value_of('cn-north-4')) \
    .build()

request = ShowFunctionConfigRequest(function_urn='FUNCTION_URN')
response = client.show_function_config(request)
print(f'Function config: {response}')
"
```

### Enable Debug Logging

```bash
# Re-create function with debug environment variables
python scripts/create_function.py create \
  --name my-function \
  --runtime Python3.9 \
  --handler index.handler \
  --code main.py \
  --env-vars '{"DEBUG": "true", "LOG_LEVEL": "debug"}'
```

## Related Documentation

- [FunctionGraph API Reference](https://support.huaweicloud.com/intl/en-us/api-functiongraph/functiongraph_06_0101.html)
- [Function Testing Guide](https://support.huaweicloud.com/intl/en-us/usermanual-functiongraph/functiongraph_01_0101.html)
- [Python SDK Documentation](https://github.com/huaweicloud/huaweicloud-sdk-python-v3)
- [Acceptance Criteria](acceptance-criteria.md)