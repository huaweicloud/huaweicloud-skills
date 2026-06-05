# Troubleshooting and Practical Experience

## 1. MaaS ShowStatistics API Issues

### Issue: DNS cannot resolve maas.{region}.myhuaweicloud.com

**Symptom:** `socket.gaierror: [Errno -2] Name or service not known`

**Root cause:** MaaS API has no independent `maas.*` domain. It reuses the ModelArts endpoint.

**Solution:** Use `modelarts.{region}.myhuaweicloud.com` as the endpoint (dynamically assembled).

### Issue: AK/SK signing returns 401

**Symptom:** `verify ak sk signature failed`

**Root cause:** Manually implementing HWS-HMAC-SHA256 signing algorithm is error-prone.

**Solution:** Use huaweicloudsdkcore Signer class. Do not implement signing manually.

### Issue: service_type=3 returns 400

**Symptom:** `"service_type must be one of [1 2 4]"`

**Root cause:** API doc says 3=Custom Endpoint, but the actual API only supports [1, 2, 4].

**Solution:** Use service_type=4 for Custom Endpoint.

### Issue: ShowStatistics returns all zeros

**Possible causes:**
1. Incorrect timestamp calculation (missing timezone)
2. Time range exceeds 30 days
3. Wrong service_type (no calls for that type)

**Troubleshooting:**
1. Verify timestamp is correct
2. Ensure time range ≤ 30 days (script auto-segments longer ranges)
3. Try different service_type

### Issue: Small discrepancy between API and console

**Symptom:** API returns 67,188, console shows 67,118.

**Possible cause:** Minor time boundary differences.

**Conclusion:** Discrepancy is within reasonable range (< 0.1%). Data is reliable.

## 2. AK/SK Signing Implementation

### Recommended: Use huaweicloudsdkcore Signer

```python
from huaweicloudsdkcore.signer.signer import Signer
from huaweicloudsdkcore.sdk_request import SdkRequest

class _Creds:
    def __init__(self, ak, sk):
        self.ak = ak
        self.sk = sk

signer = Signer(_Creds(ak, sk))
req = SdkRequest(
    method="POST", schema="https", host=host,
    resource_path=path, uri=path, query_params=[],
    header_params={"Content-Type": "application/json"}, body=body_bytes
)
signed_req = signer.sign(req)
headers = {k: v for k, v in signed_req.header_params.items()}
```

### Sending the signed request

**Important:** The body sent must exactly match the body used during signing, otherwise 401 error.

```python
url = f"https://{host}{signed_req.uri}"
resp = requests.post(url, headers=headers, data=body_bytes, verify=False)
```

## 3. Timestamp Issues

### Issue: Naive datetime timestamp is incorrect

**Solution:** Use timezone-aware datetime. The script auto-detects the OS local timezone.

## 4. Permission Issues

### Issue: Returns 403 error

**Solution:** Ensure the IAM user has `modelarts:service:get` and `modelarts:monitoring:get` permissions. See [iam-policies.md](iam-policies.md).
