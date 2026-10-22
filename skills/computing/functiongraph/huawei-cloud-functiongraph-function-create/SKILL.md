---
name: huawei-cloud-functiongraph-function-create
description: |
  Create and invoke FunctionGraph functions on Huawei Cloud. Supports VPC configuration, environment variables, synchronous and asynchronous function invocation. Use this skill when users ask to create, deploy, upload, or invoke cloud functions, serverless functions, or FunctionGraph functions. Triggered by keywords like "create function", "deploy function", "upload function", "invoke function", "create cloud function", "创建函数", "部署函数", "上传函数", "调用函数", "创建云函数", "FunctionGraph function", "serverless function", "function invocation".
tags: [huawei-cloud, functiongraph, function, serverless]
---

# FunctionGraph Function Creation & Invocation Skill

## Overview

This skill manages FunctionGraph functions on Huawei Cloud, supporting creation with
advanced configuration (VPC, environment variables) and function invocation (sync/async).

**Architecture**: Uses Huawei Cloud FunctionGraph Python SDK to interact with
FunctionGraph service.

**Applicable Scenarios**:

- Quickly create cloud functions without manual console login
- Batch creation of multiple functions with VPC or environment variable configuration
- Foundation component for workflow deployment
- CI/CD integration for function deployment
- Invoke and test deployed functions

**Typical Use Cases**:

1. "Create a Python function named my_handler"
2. "Deploy this code to FunctionGraph with VPC configuration"
3. "Create a function with environment variables"
4. "Invoke the function I just created"

## Prerequisites

### 1. Python Environment

- Python 3.9+
- Verify: `python --version`

### 2. SDK Installation

```bash
pip install huaweicloudsdkfunctiongraph
```

### 3. Authentication Configuration

- Valid Huawei Cloud credentials (AK/SK mode)
- Configure via environment variables:

```bash
export HUAWEI_AK="your-access-key"
export HUAWEI_SK="your-secret-key"
export HUAWEI_REGION="cn-north-4"
export HUAWEI_PROJECT_ID="your-project-id"
```

**Security Rules**:

- **NEVER** expose AK/SK values in code or logs
- **NEVER** let users input AK/SK directly in conversation
- **ALWAYS** use environment variables for credentials
- **Recommend** using IAM user instead of main account

### 4. IAM Permission Requirements

- `functiongraph:function:create` - Create function
- `functiongraph:function:get` - Query function details
- `functiongraph:function:list` - List functions
- `functiongraph:function:invoke` - Invoke function

See [IAM Policies](references/iam-policies.md) for detailed permission
configuration.

## Workflow

```
User Request → Parse Parameters → Validate Input
  → Create Function (with optional VPC/Env Vars) → Return Function URN
  → (Optional) Invoke Function → Return Invocation Result
```

## Usage

### Create a Function

```bash
cd scripts

# Basic creation
python create_function.py create \
  --name my_function \
  --runtime Python3.9 \
  --handler index.handler \
  --code main.py

# With VPC configuration
python create_function.py create \
  --name my_function \
  --runtime Python3.9 \
  --handler index.handler \
  --code main.py \
  --vpc-id vpc-xxx \
  --subnet-id subnet-xxx \
  --security-group-id sg-xxx

# With environment variables
python create_function.py create \
  --name my_function \
  --runtime Python3.9 \
  --handler index.handler \
  --code main.py \
  --env-vars '{"DB_HOST":"localhost","DB_PORT":"3306"}'

# Full configuration
python create_function.py create \
  --name my_function \
  --runtime Python3.9 \
  --handler index.handler \
  --code main.py \
  --memory 256 \
  --timeout 30 \
  --description "My production function" \
  --vpc-id vpc-xxx \
  --subnet-id subnet-xxx \
  --security-group-id sg-xxx \
  --env-vars '{"DEBUG":"true","LOG_LEVEL":"info"}'
```

### Invoke a Function

> **Note**: The function URN uses the real FunctionGraph URN prefix `urn:fss:`.
> Replace `PROJECT_ID` in the examples below with your actual project ID
> (the same value as the `HUAWEI_PROJECT_ID` environment variable). The
> function package is `default` and the version is `latest` (or a specific
> version/alias). You can copy the URN returned by the `create` command and
> append `:latest` for invocation.

```bash
# Synchronous invocation (default)
python create_function.py invoke \
  --function-urn urn:fss:cn-north-4:PROJECT_ID:function:default:my_function:latest \
  --body '{"key1":"value1","source":"test"}'

# Asynchronous invocation
python create_function.py invoke \
  --function-urn urn:fss:cn-north-4:PROJECT_ID:function:default:my_function:latest \
  --body '{"async":true}' \
  --invocation-type async

# Invoke with log tail (returns last 4KB of log)
python create_function.py invoke \
  --function-urn urn:fss:cn-north-4:PROJECT_ID:function:default:my_function:latest \
  --body '{"test":"data"}' \
  --log-type tail
```

## Parameter Confirmation

### Create Parameters

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `--name` | Required | Function name, must follow naming rules | - |
| `--runtime` | Required | Runtime environment (Python3.9, etc.) | - |
| `--handler` | Required | Function entry point (e.g., index.handler) | - |
| `--code` | Required | Code file path or inline code content | - |
| `--memory` | Optional | Memory size in MB | 128 |
| `--timeout` | Optional | Timeout in seconds | 3 |
| `--description` | Optional | Function description | - |
| `--vpc-id` | Optional | VPC ID for VPC configuration (must be set together with `--subnet-id` and `--security-group-id`) | - |
| `--subnet-id` | Optional | Subnet ID for VPC configuration (must be set together with `--vpc-id` and `--security-group-id`) | - |
| `--security-group-id` | Optional | Security group ID for VPC configuration (must be set together with `--vpc-id` and `--subnet-id`) | - |
| `--env-vars` | Optional | Environment variables as JSON string | - |

### Invoke Parameters

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `--function-urn` | Required | Function URN to invoke | - |
| `--body` | Optional | Event payload as JSON string | `{}` |
| `--invocation-type` | Optional | `sync` or `async` | `sync` |
| `--log-type` | Optional | `tail` to return last 4KB log | - |

### Runtime Options

| Runtime | Handler Format | Example |
|---------|----------------|---------|
| Python3.9 | index.handler | `def handler(event, context):` |
| Node.js14.18 | index.handler | `exports.handler = (event, context) => {}` |
| Java8 | com.example.Handler::handleRequest | Java class method |
| Go1.x | handler | Go function name |

## Verification Method

See [Verification Method](references/verification-method.md) for detailed
procedures.

### Quick Verification

```python
# Verify function exists using SDK

from huaweicloudsdkfunctiongraph.v2.functiongraph_client import FunctionGraphClient
from huaweicloudsdkfunctiongraph.v2.model import ListFunctionsRequest

# List functions to verify creation
client = FunctionGraphClient.new_builder().build()
request = ListFunctionsRequest()
response = client.list_functions(request)
print(f"Total functions: {len(response.functions)}")
```

## Output Format

### Create Output

The script returns a structured JSON object:

```json
{
  "status": "success",
  "function_urn": "urn:fss:cn-north-4:project_id:function:default:my_function",
  "function_name": "my_function",
  "runtime": "Python3.9",
  "memory_size": 128,
  "timeout": 3,
  "handler": "index.handler",
  "code_size": 1234,
  "message": "Function created successfully"
}
```

### Invoke Output

```json
{
  "status": "success",
  "function_urn": "urn:fss:cn-north-4:project_id:function:default:my_function",
  "invocation_type": "sync",
  "result": {
    "output": "..."
  },
  "request_id": "a1b2c3d4-...",
  "message": "Function invoked successfully"
}
```

## Best Practices

1. **Test before production**: Always test in a development environment first
2. **Monitor resources**: Set up monitoring for function invocations and errors
3. **Use environment variables**: Store sensitive data in environment variables
4. **Implement error handling**: Add proper error handling in function code
5. **Set appropriate timeouts**: Configure timeout based on function logic
6. **VPC for private resources**: Use VPC configuration when functions need access to private network resources

## Error Handling

| Error Code | Description | Resolution |
|------------|-------------|------------|
| InvalidParameter | Invalid input parameters | Check parameter format and values |
| InsufficientPermission | Insufficient permissions | Check IAM permissions |
| QuotaExceeded | Resource quota exceeded | Request quota increase or delete unused functions |
| FunctionAlreadyExists | Function with same name exists | Use different function name or delete existing function |
| FunctionNotFound | Function URN not found (invoke) | Verify the function URN is correct |

## References

- [FunctionGraph Documentation](https://support.huaweicloud.com/functiongraph/)
- [Python SDK Documentation](https://github.com/huaweicloud/huaweicloud-sdk-python-v3)
- [IAM Policies Guide](references/iam-policies.md)
- [Verification Method](references/verification-method.md)
- [Acceptance Criteria](references/acceptance-criteria.md)