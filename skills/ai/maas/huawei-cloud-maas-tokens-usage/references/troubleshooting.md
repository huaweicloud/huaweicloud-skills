# Troubleshooting - MaaS Tokens Usage Query

This document covers common issues and solutions during MaaS tokens usage query.

## Table of Contents

- [1. Python SDK Not Installed](#1-python-sdk-not-installed)
- [2. Credentials Not Configured](#2-credentials-not-configured)
- [3. MaaS ShowStatistics API Issues](#3-maas-showstatistics-api-issues)
- [4. AK/SK Signing Issues](#4-aksk-signing-issues)
- [5. Timestamp Issues](#5-timestamp-issues)
- [6. Permission Issues](#6-permission-issues)
- [7. Reference Documents](#7-reference-documents)

---

## 1. Python SDK Not Installed

### Symptoms

```
ModuleNotFoundError: No module named 'huaweicloudsdkcore'
ModuleNotFoundError: No module named 'requests'
```

### Solution

```bash
# Auto-use China mirror when system timezone is UTC+8 (faster in CN region; auto-detected via Python)
PIP_INDEX=$(python3 -c "import time;print('-i https://mirrors.huaweicloud.com/repository/pypi/simple' if -(time.timezone)//3600==8 else '')")
pip install $PIP_INDEX huaweicloudsdkcore requests
```

See [cli-installation-guide.md](cli-installation-guide.md).

---

## 2. Credentials Not Configured

### Symptoms

```
ERROR: HW_ACCESS_KEY/HW_SECRET_KEY not set
```

### Solution

Configure credentials via environment variables or credentials file. See [cli-installation-guide.md](cli-installation-guide.md) for details.

> **⚠️ Never provide AK/SK directly in conversation.** Always use environment variables or `--credentials-file`.

---

## 3. MaaS ShowStatistics API Issues

### Issue: DNS cannot resolve maas.{region}.myhuaweicloud.com

**Symptom:** `socket.gaierror: [Errno -2] Name or service not known`

**Root cause:** MaaS API has no independent `maas.*` domain. It reuses the ModelArts endpoint.

**Solution:** Use `modelarts.{region}.myhuaweicloud.com` as the endpoint (dynamically assembled by the script).

---

### Issue: service_type=3 returns 400

**Symptom:** `"service_type must be one of [1 2 4]"`

**Root cause:** API doc says 3=Custom Endpoint, but the actual API only supports [1, 2, 4].

**Solution:** Use `--service-type 4` for Custom Endpoint.

---

### Issue: ShowStatistics returns all zeros

**Symptom:** All metrics (tokens, requests, errors) return 0.

**Possible causes:**

| Cause | Solution |
|-------|----------|
| Incorrect timestamp calculation (missing timezone) | Verify script auto-detects OS timezone |
| Time range exceeds 30 days | Script auto-segments; verify segmentation works |
| Wrong service_type (no calls for that type) | Try `--service-type 2` (Preset), `--service-type 1` (My Service), `--service-type 4` (Custom) |
| No usage in the queried period | Verify the time range has actual MaaS calls |

---

### Issue: Small discrepancy between API and console

**Symptom:** API returns 67,188, console shows 67,118.

**Possible cause:** Minor time boundary differences.

**Conclusion:** Discrepancy is within reasonable range (< 0.1%). Data is reliable.

---

### Issue: Region not supported

**Symptom:** API returns error when using a region other than `cn-southwest-2`.

**Root cause:** MaaS ShowStatistics API only supports Southwest-Guiyang-1 region.

**Solution:** Use `--region cn-southwest-2` (default).

---

## 4. AK/SK Signing Issues

### Issue: AK/SK signing returns 401

**Symptom:** `verify ak sk signature failed`

**Root cause:** Manually implementing SDK-HMAC-SHA256 signing algorithm is error-prone.

**Solution:** Use `huaweicloudsdkcore.Signer` class. Do not implement signing manually.

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

> **⚠️ Important:** The body sent must exactly match the body used during signing, otherwise 401 error.

```python
url = f"https://{host}{signed_req.uri}"
resp = requests.post(url, headers=headers, data=body_bytes, verify=True)
```

---

## 5. Timestamp Issues

### Issue: Naive datetime timestamp is incorrect

**Symptom:** Query returns wrong results or all zeros due to timezone mismatch.

**Solution:** Use timezone-aware datetime. The script auto-detects the OS local timezone via `datetime.now().astimezone()`.

> **⚠️ Never hardcode `CST` or `Asia/Shanghai`.** Always follow the OS local timezone.

---

## 6. Permission Issues

### Issue: Returns 403 error

**Symptom:** `403 Forbidden` when calling ShowStatistics API.

**Solution:** Ensure the IAM user has the required permissions. See [iam-policies.md](iam-policies.md).

| Missing Permission | Symptom | Solution |
|--------------------|---------|----------|
| `modelarts:monitoring:get` | ShowStatistics returns 403 | Add ModelArts monitoring read permission |
| `modelarts:service:get` | Service list query returns 403 | Add ModelArts service read permission |
| `iam:projects:get` | Project ID resolution fails | Add IAM projects read permission |

---

## 7. Reference Documents

- [CLI Installation Guide](cli-installation-guide.md)
- [IAM Permission Policies](iam-policies.md)
- [Task 1: Query Tokens Usage](task-query-tokens-usage.md)
- [Verification Method](verification-method.md)
- [Acceptance Criteria](acceptance-criteria.md)
