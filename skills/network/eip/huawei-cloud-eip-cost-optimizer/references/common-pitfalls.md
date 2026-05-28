# Common Pitfalls & Solutions

This document contains detailed troubleshooting guides for common issues encountered when using the Huawei Cloud EIP Cost Optimizer skill.

## Pitfall 1: Wrong API for Bandwidth Adjustment

**Symptom**: API returns error `VPC.0301: updateBandwidth bandwidth params are invalid`

**Root Cause**: Using `UpdateBandwidthRequest` or `UpdatePublicipRequest` instead of `BatchModifyBandwidthRequest`

**Solution**:

```python
# ❌ WRONG - These APIs don't work for bandwidth adjustment
from huaweicloudsdkeip.v2 import UpdatePublicipRequest, UpdateBandwidthRequest

# ✅ CORRECT - Use BatchModifyBandwidthRequest
from huaweicloudsdkeip.v2 import BatchModifyBandwidthRequest, ModifyBandwidthOption, ModifyBandwidthRequestBody

bandwidth_option = ModifyBandwidthOption()
bandwidth_option.id = bandwidth_id  # Required!
bandwidth_option.size = new_bandwidth_size

body = ModifyBandwidthRequestBody()
body.bandwidths = [bandwidth_option]  # List format

request = BatchModifyBandwidthRequest()
request.body = body

response = client.batch_modify_bandwidth(request)
```

**Why this happens**: The EIP v2 SDK has three bandwidth-related APIs:

1. `update_publicip` - Updates EIP basic properties (alias, IP version), NOT bandwidth
2. `update_bandwidth` - Exists but has parameter validation issues (SDK limitation)
3. `batch_modify_bandwidth` - ✅ Recommended, supports batch operations, correct parameter structure

## Pitfall 2: Missing bandwidth_id in EIP List
