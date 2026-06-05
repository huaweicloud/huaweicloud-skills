# Huawei Cloud EIP Python SDK Usage Guide

## Overview

This document covers Python SDK usage patterns for Huawei Cloud EIP operations, based on real-world testing and troubleshooting sessions.

## SDK Installation

```bash
pip install huaweicloudsdkeip huaweicloudsdkvpc
```

**Note**: SDK version 3.1.196+ tested and working.

## Authentication

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials

ak = os.environ.get('HUAWEI_CLOUD_AK')
sk = os.environ.get('HUAWEI_CLOUD_SK')
region = os.environ.get('HUAWEI_CLOUD_REGION', 'cn-north-4')

credentials = BasicCredentials(ak=ak, sk=sk)
```

**Security Rules**:
- ✅ Use environment variables for AK/SK
- ✅ Use IAM users instead of root account
- ❌ Never hardcode credentials in scripts
- ❌ Never print full AK/SK values (use slicing: `ak[:8]...ak[-4:]`)

## Client Initialization

```python
from huaweicloudsdkeip.v2.region.eip_region import EipRegion
from huaweicloudsdkeip.v2.eip_client import EipClient

client = EipClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(EipRegion.value_of(region)) \
    .build()
```

## Common Operations

### 1. List All EIPs

```python
from huaweicloudsdkeip.v2.model.list_publicips_request import ListPublicipsRequest

request = ListPublicipsRequest()
response = client.list_publicips(request)
eips = response.publicips

for eip in eips:
    print(f"{eip.id}: {eip.public_ip_address} (status: {eip.status}, bound: {eip.port_id is not None})")
```

### 2. List All Bandwidths

```python
from huaweicloudsdkeip.v2.model.list_bandwidths_request import ListBandwidthsRequest

request = ListBandwidthsRequest()
response = client.list_bandwidths(request)
bandwidths = response.bandwidths

bw_map = {bw.id: bw for bw in bandwidths}
```

### 3. Batch Adjust Bandwidth

**Important**: The API structure is:
- `BatchModifyBandwidthRequest` takes `ModifyBandwidthRequestBody`
- `ModifyBandwidthRequestBody` contains `bandwidths` list
- Each item is `ModifyBandwidthOption(id=eip_id, size=bandwidth_mbps)`

```python
from huaweicloudsdkeip.v2.model.batch_modify_bandwidth_request import BatchModifyBandwidthRequest
from huaweicloudsdkeip.v2.model.modify_bandwidth_request_body import ModifyBandwidthRequestBody
from huaweicloudsdkeip.v2.model.modify_bandwidth_option import ModifyBandwidthOption

eip_ids = ['eip-id-1', 'eip-id-2']
bandwidth_size = 5  # Mbps

# Create option for each EIP
bandwidth_options = [
    ModifyBandwidthOption(id=eip_id, size=bandwidth_size)
    for eip_id in eip_ids
]

body = ModifyBandwidthRequestBody(bandwidths=bandwidth_options)
request = BatchModifyBandwidthRequest(body=body)
response = client.batch_modify_bandwidth(request)
```

### 4. Release EIP

```python
from huaweicloudsdkeip.v2.model.delete_publicip_request import DeletePublicipRequest

eip_id = 'eip-id-to-delete'
request = DeletePublicipRequest(publicip_id=eip_id)
response = client.delete_publicip(request)
```

## Error Handling

```python
from huaweicloudsdkcore.exceptions.exceptions import ServiceResponseException

try:
    request = ListPublicipsRequest()
    response = client.list_publicips(request)
except ServiceResponseException as e:
    print(f"Error: {e}")
    print(f"Status code: {e.status_code}")
    print(f"Error message: {e.error_msg}")
```

## Common Import Errors & Solutions

### Issue 1: ModuleNotFoundError for list_publicip_bandwidths_request

**Wrong**:
```python
from huaweicloudsdkeip.v2.model.list_publicip_bandwidths_request import ListPublicipBandwidthsRequest
```

**Correct**:
```python
from huaweicloudsdkeip.v2.model.list_bandwidths_request import ListBandwidthsRequest
```

### Issue 2: ModuleNotFoundError for batch_modify_bandwidth_request_body

**Wrong**:
```python
from huaweicloudsdkeip.v2.model.batch_modify_bandwidth_request_body import BatchModifyBandwidthRequestBody
```

**Correct**:
```python
from huaweicloudsdkeip.v2.model.modify_bandwidth_request_body import ModifyBandwidthRequestBody
```

### Issue 3: ServiceException import error

**Wrong**:
```python
from huaweicloudsdkcore.exceptions.service_exception import ServiceException
```

**Correct**:
```python
from huaweicloudsdkcore.exceptions.exceptions import ServiceResponseException
```

### Issue 4: Using wrong API for bandwidth adjustment (CRITICAL)

**Common Mistake**: Trying to use `UpdatePublicip` or `UpdateBandwidth` APIs

**Wrong Approach 1** - UpdatePublicip:
```python
from huaweicloudsdkeip.v2 import UpdatePublicipRequest, UpdatePublicipOption

publicip_option = UpdatePublicipOption()
publicip_option.bandwidth_size = 5  # ❌ This parameter doesn't exist!
```

**Wrong Approach 2** - UpdateBandwidth:
```python
from huaweicloudsdkeip.v2 import UpdateBandwidthRequest, UpdateBandwidthOption

bandwidth_option = UpdateBandwidthOption()
bandwidth_option.size = 5
request = UpdateBandwidthRequest(bandwidth_id=bw_id, body=bandwidth_option)
response = client.update_bandwidth(request)  # ❌ Returns 400 VPC.0301 error
```

**Correct Approach** - BatchModifyBandwidth:
```python
from huaweicloudsdkeip.v2 import (
    BatchModifyBandwidthRequest,
    ModifyBandwidthRequestBody,
    ModifyBandwidthOption
)

# Step 1: Create option with id and size
bandwidth_option = ModifyBandwidthOption()
bandwidth_option.id = '5466e72a-9f4e-4b7a-aea8-8d9cd1739458'  # bandwidth_id
bandwidth_option.size = 5  # new bandwidth in Mbps

# Step 2: Wrap in request body (bandwidths is a list)
body = ModifyBandwidthRequestBody()
body.bandwidths = [bandwidth_option]

# Step 3: Create and execute request
request = BatchModifyBandwidthRequest()
request.body = body
response = client.batch_modify_bandwidth(request)  # ✅ Success
```

**Error Message** when using wrong API:
```
ClientRequestException: {status_code:400, error_code:VPC.0301, 
error_msg:updateBandwidth bandwidth params are invalid.}
```

**Why this happens**: The SDK has multiple bandwidth-related APIs:
- `UpdateBandwidth` - for updating bandwidth billing mode (not size)
- `UpdatePublicip` - for updating EIP attributes (not bandwidth)
- `BatchModifyBandwidth` - ✅ The ONLY API that adjusts bandwidth size

**Pitfall**: This is not obvious from the SDK documentation. Always use `batch_modify_bandwidth` for bandwidth size adjustments.

## API Discovery Pattern

When unsure about API structure, use this pattern:

```python
import sys
sys.path.insert(0, '/path/to/site-packages')
from huaweicloudsdkeip.v2 import model

# Find APIs by keyword
items = [x for x in dir(model) if 'bandwidth' in x.lower() and 'modify' in x.lower()]
for item in items:
    print(f'  - {item}')

# Inspect request structure
from huaweicloudsdkeip.v2.model.batch_modify_bandwidth_request import BatchModifyBandwidthRequest
req = BatchModifyBandwidthRequest()
print(req.openapi_types)  # Shows expected body type
print(req.attribute_map)
```

## Idle EIP Detection

**Reliable Method**: Check if `port_id` is `None`

```python
idle_eips = [eip for eip in eips if not eip.port_id]
```

**Unreliable Methods** (avoid):
- `binding_status` field may not exist in all API versions
- `bind_type` field may be empty string instead of `None`
- `associate_instance_type` may be present even for idle EIPs

## Complete Working Example

See `scripts/adjust_eip_bandwidth.py` for a complete, production-ready example that:
- Lists all EIPs with bandwidth information
- Supports `--list`, `--all`, `--idle-only`, `--eip-ids` modes
- Interactive confirmation before destructive operations
- Proper error handling and user feedback
- Statistics and summary output

## Region Codes

| Region | Code |
|--------|------|
| 华北 - 北京四 | cn-north-4 |
| 华北 - 北京一 | cn-north-1 |
| 华东 - 上海一 | cn-east-3 |
| 华东 - 上海二 | cn-east-2 |
| 华南 - 广州 | cn-south-1 |
| 华南 - 深圳 | cn-south-4 |
| 西南 - 贵阳一 | cn-southwest-2 |
| 亚太 - 曼谷 | ap-southeast-2 |
| 亚太 - 新加坡 | ap-southeast-1 |
| 亚太 - 香港 | ap-southeast-3 |

## Troubleshooting

### Issue: "No module named 'huaweicloudsdkeip'"

**Solution**: Install SDK with `--break-system-packages` flag (WSL/Ubuntu):
```bash
pip install huaweicloudsdkeip huaweicloudsdkvpc --break-system-packages
```

Or use virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install huaweicloudsdkeip huaweicloudsdkvpc
```

### Issue: "externally-managed-environment" error

This is a PEP 668 restriction in modern Python distributions.

**Solutions**:
1. Use `--break-system-packages` flag (quick fix)
2. Use virtual environment (recommended for development)
3. Use `pipx` for application installation

### Issue: Empty EIP list returned

Possible causes:
1. Wrong region - verify with `HUAWEI_CLOUD_REGION`
2. No EIPs in that region (confirmed empty)
3. Permission issue - check IAM policies
4. Credential issue - verify AK/SK

**Debug**:
```python
print(f"Region: {region}")
print(f"AK: {ak[:8]}...{ak[-4:]}")
```

## Session Notes

**Date**: 2026-05-25
**Region**: cn-north-4
**Result**: Successfully identified and released 1 idle EIP (120.46.5.112)
**Follow-up**: No EIPs remaining in cn-north-4 region

**Key Learnings**:
1. Shell scripts in this skill depend heavily on Python SDK (Python SDK command)
2. Python SDK scripts provide better portability
3. API naming in SDK v3.1.196 differs from documentation (e.g., `ListBandwidthsRequest` vs `ListPublicipBandwidthsRequest`)
4. Always test imports before writing full scripts
