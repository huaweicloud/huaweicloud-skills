# Python SDK Installation Guide

## Overview

This guide covers installation and configuration of the Huawei Cloud FunctionGraph Python SDK for creating and managing FunctionGraph triggers.

## Prerequisites

- Python 3.9 or higher
- pip package manager
- Huawei Cloud account with Access Key (AK) and Secret Key (SK)

## Installation

### 1. Install FunctionGraph SDK

```bash
# Install FunctionGraph SDK (includes core dependencies)
pip install huaweicloudsdkfunctiongraph

# Verify installation
python -c "from huaweicloudsdkfunctiongraph.v2 import FunctionGraphClient; print('SDK installed successfully')"
```

### 2. Install Additional Dependencies (Optional)

```bash
# For enhanced functionality
pip install huaweicloudsdkcore
```

## Environment Configuration

Configure authentication using environment variables:

### Linux/macOS

```bash
export HUAWEI_AK="your_access_key"
export HUAWEI_SK="your_secret_key"
export HUAWEI_REGION="cn-north-4"
export HUAWEI_PROJECT_ID="your_project_id"
```

### Windows PowerShell

```powershell
$env:HUAWEI_AK = "your_access_key"
$env:HUAWEI_SK = "your_secret_key"
$env:HUAWEI_REGION = "cn-north-4"
$env:HUAWEI_PROJECT_ID = "your_project_id"
```

### Windows Command Prompt

```cmd
set HUAWEI_AK=your_access_key
set HUAWEI_SK=your_secret_key
set HUAWEI_REGION=cn-north-4
set HUAWEI_PROJECT_ID=your_project_id
```

## Verify Configuration

Create a test script to verify your configuration:

```python
import os
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkfunctiongraph.v2 import FunctionGraphClient
from huaweicloudsdkfunctiongraph.v2.region.functiongraph_region import FunctionGraphRegion

# Load credentials from environment
ak = os.environ.get("HUAWEI_AK")
sk = os.environ.get("HUAWEI_SK")
region = os.environ.get("HUAWEI_REGION")
project_id = os.environ.get("HUAWEI_PROJECT_ID")

# Create credentials
credentials = BasicCredentials(ak, sk, project_id)

# Create client
client = FunctionGraphClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(FunctionGraphRegion.value_of(region)) \
    .build()

print("Configuration verified successfully!")
```

`with_region()` expects a `FunctionGraphRegion` object, not a bare region string. Passing the
string raises a type error at build time; always wrap the region code with
`FunctionGraphRegion.value_of(region)` as shown above.

Import `FunctionGraphRegion` from its module,
`huaweicloudsdkfunctiongraph.v2.region.functiongraph_region`. The shorter
`huaweicloudsdkfunctiongraph.v2.region` path does not export it (that package's `__init__.py` is
empty), so the short form raises `ImportError` at the first line of the script.

## Creating a Trigger with the SDK

The skill's script (`scripts/create_trigger.py`) is the supported entry point. The snippets below
show the same SDK calls when you need to embed trigger creation in your own code.

### TIMER trigger

```python
from huaweicloudsdkfunctiongraph.v2.model.create_function_trigger_request import (
    CreateFunctionTriggerRequest,
)
from huaweicloudsdkfunctiongraph.v2.model.create_function_trigger_request_body import (
    CreateFunctionTriggerRequestBody,
)
from huaweicloudsdkfunctiongraph.v2.model.trigger_event_data_request_body import (
    TriggerEventDataRequestBody,
)

event_data = TriggerEventDataRequestBody(
    name="daily-trigger",
    schedule_type="Cron",
    schedule="0 0 2 * * ?",
)

request = CreateFunctionTriggerRequest(
    function_urn="urn:fss:cn-north-4:project_id:function:default:my-function:latest",
    body=CreateFunctionTriggerRequestBody(
        trigger_type_code="TIMER",
        trigger_status="ACTIVE",
        event_data=event_data,
    ),
)

response = client.create_function_trigger(request)
print(response.trigger_id)
```

### OBS event trigger

For `OBS`, `bucket` and `events` are required on `TriggerEventDataRequestBody`; `prefix` and
`suffix` are optional key filters:

```python
event_data = TriggerEventDataRequestBody(
    name="realtime-redact",
    bucket="input-images",
    events=["ObjectCreated"],
    prefix="uploads/",
    suffix=".jpg",
)

request = CreateFunctionTriggerRequest(
    function_urn="urn:fss:cn-north-4:project_id:function:default:redact-image:latest",
    body=CreateFunctionTriggerRequestBody(
        trigger_type_code="OBS",
        trigger_status="ACTIVE",
        event_data=event_data,
    ),
)

response = client.create_function_trigger(request)
print(response.trigger_id)
```

See [OBS Event Trigger Guide](./obs-trigger-guide.md) for the full parameter list, the accepted
event values, and end-to-end examples.

### Inspecting triggers

```python
from huaweicloudsdkfunctiongraph.v2.model.list_function_triggers_request import (
    ListFunctionTriggersRequest,
)

request = ListFunctionTriggersRequest(function_urn=function_urn)
response = client.list_function_triggers(request)

# ListFunctionTriggersResponse exposes the list as `body` (list[ListFunctionTriggerResult]).
for trigger in (response.body or []):
    print(trigger.trigger_id, trigger.trigger_type_code, trigger.trigger_status)
    if trigger.event_data:
        print(trigger.event_data.name, trigger.event_data.bucket, trigger.event_data.events)
```

## Common Regions

| Region Code | Region Name |
|-------------|-------------|
| `cn-north-4` | Beijing 4 |
| `cn-south-1` | Guangzhou |
| `cn-east-3` | Shanghai |
| `ap-southeast-1` | Hong Kong |
| `ap-southeast-3` | Singapore |

## Virtual Environment Setup (Recommended)

### Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### Install SDK in Virtual Environment

```bash
pip install huaweicloudsdkfunctiongraph
```

## Troubleshooting

### Issue 1: Module Not Found

```bash
# Ensure SDK is installed
pip install huaweicloudsdkfunctiongraph

# Verify Python path
python -c "import sys; print(sys.path)"
```

### Issue 2: Authentication Failed

```bash
# Verify environment variables are set (without printing their values)
# Linux/macOS:
[ -n "$HUAWEI_AK" ] && echo 'HUAWEI_AK is set'
[ -n "$HUAWEI_SK" ] && echo 'HUAWEI_SK is set'

# Windows PowerShell:
Test-Path Env:HUAWEI_AK
Test-Path Env:HUAWEI_SK
```

Never print the AK/SK values themselves — treat them as secrets and only check whether they exist.

### Issue 3: SSL Certificate Error

Do **not** disable TLS/SSL verification — `ignore_ssl_verification = True` exposes requests to man-in-the-middle attacks. Instead, ensure the correct CA certificates are installed and trusted:

```bash
# Linux/macOS: update the system CA certificate bundle
sudo apt-get update && sudo apt-get install -y ca-certificates
sudo update-ca-certificates

# If behind a corporate proxy with a private CA, add that CA to the trusted store:
#   1. Obtain the corporate CA certificate (e.g. corporate-ca.crt)
#   2. Copy it into the system trust store and refresh
sudo cp corporate-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

After the CA chain is trusted, the SDK performs normal TLS verification automatically. If the error persists, check the `HUAWEI_REGION` endpoint and your network/proxy configuration rather than bypassing certificate validation.

### Issue 4: Region Not Found

Check that the region code is correct and matches your FunctionGraph function location.

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use environment variables** for all credential storage
3. **Rotate AK/SK regularly**
4. **Use IAM temporary credentials** when possible
5. **Restrict IAM permissions** to minimum required
6. **Use virtual environments** to isolate dependencies

## SDK Version Management

```bash
# Check installed version
pip show huaweicloudsdkfunctiongraph

# Upgrade to latest version
pip install --upgrade huaweicloudsdkfunctiongraph

# List all Huawei Cloud SDKs
pip list | grep huaweicloudsdk
```

## Uninstallation

```bash
# Uninstall SDK
pip uninstall huaweicloudsdkfunctiongraph

# Uninstall core SDK
pip uninstall huaweicloudsdkcore
```

## Next Steps

After installation, proceed to:

- [IAM Policies Configuration](./iam-policies.md)
- [OBS Event Trigger Guide](./obs-trigger-guide.md)
- [Verification Method](./verification-method.md)
- [Acceptance Criteria](./acceptance-criteria.md)
