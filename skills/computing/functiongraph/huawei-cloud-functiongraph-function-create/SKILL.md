---
name: huawei-cloud-functiongraph-function-create
description: |
  Create FunctionGraph functions on Huawei Cloud. Use this skill when users ask to create, deploy, or upload cloud functions, serverless functions, or FunctionGraph functions. Triggered by keywords like "create function", "deploy function", "upload function", "create cloud function", "创建函数", "部署函数", "上传函数", "创建云函数", "FunctionGraph function", "serverless function".
tags: [huawei-cloud, functiongraph, function, serverless]
---

# FunctionGraph Function Creation Skill

## Overview

This skill creates FunctionGraph functions on Huawei Cloud based on
user-provided parameters including function name, runtime, and code content.

**Architecture**: Uses Huawei Cloud FunctionGraph Python SDK to interact with
FunctionGraph service.

**Applicable Scenarios**:

- Quickly create cloud functions without manual console login
- Batch creation of multiple functions
- Foundation component for workflow deployment
- CI/CD integration for function deployment

**Typical Use Cases**:

1. "Create a Python function named my_handler"
2. "Deploy this code to FunctionGraph"
3. "Batch create 10 functions from template"

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

See [IAM Policies](references/iam-policies.md) for detailed permission
configuration.

## Usage

### Command

```bash
cd scripts
python create_function.py   --name <function_name>   --runtime <runtime>   --han
dler <handler>   --code <code_content>   --memory <memory_size>   --timeout <timeout>
```

## Parameter Confirmation

|| Parameter | Required/Optional | Description | Default ||
|| ----------- | ------------------ | ------------- | --------- ||
|| `function_name` | Required | Function name, must follow naming rules | - ||
|| `runtime` | Required | Runtime environment (Python3.9, etc.) | - ||
|| `code_content` | Required | Function code content | - ||
|| `handler` | Required | Function entry point (e.g., index.handler) | - ||
|| `memory_size` | Optional | Memory size in MB | 128 ||
|| `timeout` | Optional | Timeout in seconds | 3 ||
|| `description` | Optional | Function description | - ||

### Runtime Options

|| Runtime | Handler Format | Example ||
|| --------- | ---------------- | --------- ||
|| Python3.9 | index.handler | `def handler(event, context):` ||
|| Node.js14.18 | index.handler | `exports.handler = (event, context) => {}` ||
|| Java8 | com.example.Handler::handleRequest | Java class method ||
|| Go1.x | handler | Go function name ||

## Verification Method

See [Verification Method](references/verification-method.md) for detailed
procedures.

### Quick Verification

```python
## Verify function exists using SDK

from huaweicloudsdkfunctiongraph.v2.functiongraph_client import FunctionGraphClient
from huaweicloudsdkfunctiongraph.v2.model import ListFunctionsRequest

# List functions to verify creation
client = FunctionGraphClient.new_builder().build()
request = ListFunctionsRequest()
response = client.list_functions(request)
print(f"Total functions: {len(response.functions)}")
```

## Output Format

The skill returns a structured JSON object with the following fields:

- `function_urn`: Unique resource identifier of the created function
- `function_name`: Name of the created function
- `runtime`: Runtime environment
- `memory_size`: Allocated memory in MB
- `timeout`: Function timeout in seconds
- `handler`: Function entry point
- `description`: Function description (if provided)

Example output:

```json
{
  "function_urn": "urn:fss:cn-north-4:project_id:function:default:my_function",
  "function_name": "my_function",
  "runtime": "Python3.9",
  "memory_size": 128,
  "timeout": 3,
  "handler": "index.handler",
  "description": "Test function created by skill"
}
```

## Best Practices

1. **Test before production**: Always test in a development environment first
2. **Monitor resources**: Set up monitoring for function invocations and errors
3. **Use environment variables**: Store sensitive data in environment variables
4. **Implement error handling**: Add proper error handling in function code
5. **Set appropriate timeouts**: Configure timeout based on function logic

## Error Handling

|| Error Code | Description | Resolution ||
|| ------------ | ------------- | ------------ ||
|| InvalidParameter | Invalid input parameters | Check parameter format and valu
es ||
|| InsufficientPermission | Insufficient permissions | Check IAM permissions ||
|| QuotaExceeded | Resource quota exceeded | Request quota increase or delete un
used functions ||
|| FunctionAlreadyExists | Function with same name exists | Use different functi
on name or delete existing function ||

## References

- [FunctionGraph Documentation](https://support.huaweicloud.com/functiongraph/)
- [Python SDK Documentation](https://github.com/huaweicloud/huaweicloud-sdk-python-v3)
- [IAM Policies Guide](references/iam-policies.md)
- [Verification Method](references/verification-method.md)
