# Troubleshooting - MaaS Tokens Usage Query

This document covers common issues and solutions during MaaS tokens usage query.

## Table of Contents

- [1. Python SDK Not Installed](#1-python-sdk-not-installed)
- [2. Credentials Not Configured](#2-credentials-not-configured)
- [3. MaaS ShowStatistics API Issues](#3-maas-showstatistics-api-issues)
- [4. AK/SK Signing Issues](#4-aksk-signing-issues)
- [5. Timestamp Issues](#5-timestamp-issues)
- [6. Permission Issues](#6-permission-issues)
- [7. Parameter Validation and Friendly Errors](#7-parameter-validation-and-friendly-errors)
- [8. Reference Documents](#8-reference-documents)

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

Configure credentials via environment variables or credentials file. See [cli-installation-guide.md](cli-installation-guide.md) and [security-guide.md](security-guide.md) for details.

> **⚠️ Never provide AK/SK directly in conversation.** Always use environment variables or `--credentials-file`.

**Temporary credentials (STS) require `HW_SECURITY_TOKEN`** — if AK/SK are temporary and the token is missing, IAM/ShowStatistics calls fail authentication (401/403). Set all three:

```bash
export HW_ACCESS_KEY=<your-temp-access-key-id>
export HW_SECRET_KEY=<your-temp-access-key-secret>
export HW_SECURITY_TOKEN=<your-security-token>
```

The credentials file (`--credentials-file`) supports the token in all three formats: `HW_SECURITY_TOKEN=<token>`
(KEY=VALUE), the third CSV column (`<ak>,<sk>,<token>`), or the third line (one value per line).

**Credentials file read failures** (all exit code 1):

| Situation | Script output (stderr) | Fix |
|-----------|------------------------|-----|
| Path does not exist | `Error: Credentials file not found: <path>` | Check the path |
| Path is a directory, permission denied, non-UTF-8 bytes, or another `OSError` | `Error: Cannot read credentials file <path>: <msg>` | Point to a **readable UTF-8 text file** — not a directory, with read permission, and no UTF-16/BOM/binary bytes (the script opens it with `encoding="utf-8"`) |

> Example (UTF-16 file): `Error: Cannot read credentials file creds.txt: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte`
> Example (directory, POSIX): `Error: Cannot read credentials file /tmp/creds: [Errno 13] Permission denied: '/tmp/creds'`
> On Windows the same directory error quotes the path and doubles its backslashes, e.g. `Error: Cannot read credentials file D:\creds: [Errno 13] Permission denied: 'D:\\creds'` — that quoting/doubling is Python's own `OSError` formatting, not a different error.

---

## 3. MaaS ShowStatistics API Issues

### Issue: DNS cannot resolve maas.{region}.myhuaweicloud.com

**Symptom:** `socket.gaierror: [Errno -2] Name or service not known`, now surfaced as a friendly error:

```
Error: Cannot reach modelarts.invalid-region.myhuaweicloud.com (ConnectionError): ...
       Check --region, network connectivity, proxy/firewall settings, and that credentials are valid.
```

**Root cause:** MaaS API has no independent `maas.*` domain. It reuses the ModelArts endpoint.

**Solution:** Use `modelarts.{region}.myhuaweicloud.com` as the endpoint (dynamically assembled by the script), and use a supported region (`cn-southwest-2`).

---

### Issue: service_type=3 returns 400

**Symptom:** `"service_type must be one of [1 2 4]"`

**Root cause:** API doc says 3=Custom Endpoint, but the actual API only supports [1, 2, 4].

**Solution:** Use `--service-type 4` for Custom Endpoint.

---

### Issue: ShowStatistics returns all zeros

**Symptom:** All metrics (tokens, requests, errors) return 0.

**What the script does (Gap-3):** the table is printed as usual, and immediately after the `Period:` line the script
adds **two lines** on **stdout** (they are **not** errors — exit code stays `0`):

```
Note: no usage data in this period (all values are zero). Verify the time range, service type, infer type, and API key filter.
Note: if --from equals --to, the query window is a single instant (00:00-00:00); use a wider range or --last-days.
```

So a zero result is always explicitly flagged instead of being silently reported as a successful query.

### Why `--from` == `--to` can return all zeros

`--from` and `--to` are both normalised to the **local 00:00 boundary** of the given date, so
`--from 2026-07-01 --to 2026-07-01` describes the interval `2026-07-01 00:00:00 ~ 2026-07-01 00:00:00` — a
**zero-length window**, which legitimately contains no data.

**Fix:** use a wider range (`--to 2026-07-02`) or use `--last-days 1`, whose `to` is the
**current instant** (today 00:00 → now), so today's usage up to now is included.

> This 00:00-boundary behaviour is a known limitation of `--from`/`--to`; `--last-days` is not affected.

**Possible causes:**

| Cause | Solution |
|-------|----------|
| Incorrect timestamp calculation (missing timezone) | Verify script auto-detects OS timezone |
| Time range spans more than 29 days | Script auto-segments; verify segmentation works |
| Wrong service_type (no calls for that type) | Try `--service-type 2` (Preset), `--service-type 1` (My Service), `--service-type 4` (Custom) |
| Wrong `--infer-type` | Check `real_time` (online) vs `batch`; batch metrics are zero unless batch inference ran |
| `--from` == `--to` (zero-length window) | See above — widen `--to` or use `--last-days N` |
| Data between `--to` 00:00 and now is missing | `--to` covers only up to its own 00:00; use `--last-days` if you need today's data up to now |
| API-key filter excludes all calls | Re-run without `--api-keys`, or verify the key list (`--api-keys key1 key2`) |
| No usage in the queried period | Verify the time range has actual MaaS calls (compare with the console) |

---

### Issue: Small discrepancy between API and console

**Symptom:** API returns 67,188, console shows 67,118.

**Possible cause:** Minor time boundary differences.

**Conclusion:** Discrepancy is within reasonable range (< 0.1%). Data is reliable.

---

### Issue: Region not supported

**Symptom:** Using a region other than `cn-southwest-2` now fails fast with a friendly parameter error (no traceback):

```
Error: Unsupported region 'invalid-region'. MaaS ShowStatistics only supports: cn-southwest-2.
```

**Root cause:** MaaS ShowStatistics API only supports Southwest-Guiyang-1 region (official doc: 区域限制 — 仅支持西南-贵阳一区域).

**Solution:** Use `--region cn-southwest-2` (default). The region whitelist is validated **before** credentials are read, so this error appears even with no credentials configured.

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

## 7. Parameter Validation and Friendly Errors

Since the #87/#112 fixes, the failure modes documented here and in [SKILL.md](../SKILL.md) `## Error Handling` are
reported as `Error: ...` on `stderr` with exit code `1` instead of a raw Python traceback; parameter validation runs
**before** credentials are read, so these errors are reproducible offline (no AK/SK needed). Invalid input beyond the
cases listed below is handled on a best-effort basis.

| Symptom / input | Script output (stderr) | Fix |
|-----------------|------------------------|-----|
| No `--from`/`--to` and no `--last-days` | `Error: --from and --to are required unless --last-days is used.` | Add `--from`+`--to` or `--last-days N` |
| `--last-days 7 --from ... --to ...` | `Error: --last-days cannot be combined with --from / --to.` | Use only one time-range form |
| `--last-days 0` / `--last-days abc` / `--last-days 7.5` | `Error: --last-days must be a positive integer, got '<v>'.` | Pass an integer in `1 <= N <= 3650` |
| `--last-days 5000` (above the bound) | `Error: --last-days must not exceed 3650 days, got '5000'.` | Use `1 <= N <= 3650` (`MAX_LAST_DAYS`) |
| `--to invalid-date` | `Error: Invalid --to date format: 'invalid-date'`<br>`       Date format should be YYYY-MM-DD, e.g. 2026-08-10` | Use `YYYY-MM-DD` |
| `--from 2026-07-20 --to 2026-07-10` | `Error: --from (2026-07-20) must not be later than --to (2026-07-10).` | Fix the date order |
| `--region invalid-region` | `Error: Unsupported region 'invalid-region'. MaaS ShowStatistics only supports: cn-southwest-2.` | Use `cn-southwest-2` |
| No credentials at all | `Error: Credentials not found. Provide AK/SK via:` + 4-line hint block | Set env vars or `--credentials-file` |
| `--credentials-file missing.txt` | `Error: Credentials file not found: missing.txt` | Check the path |
| `--credentials-file` points to a directory / unreadable / non-UTF-8 file | `Error: Cannot read credentials file <path>: <msg>` | Use a readable **UTF-8 text** file (see section 2) |
| Network/DNS/proxy failure | `Error: Cannot reach <host> (<ExcName>): <msg>`<br>`       Check --region, network connectivity, proxy/firewall settings, and that credentials are valid.` | Check region/network/proxy/credentials |
| API returns non-200 (400/401/403) or SDK error | `Error: ShowStatistics failed: <status> <body>`<br>`       Check the request parameters, region, and credential permissions (401/403 = credentials/IAM).` | Check parameters, region, IAM permissions |
| `--notify-url` is not HTTPS, is an IP literal, or is off the Huawei Cloud allowlist | `Error: --notify-url rejected: only HTTPS URLs on trusted Huawei Cloud hosts (*.myhuaweicloud.com / *.huaweicloud.com) are allowed; the request was NOT sent.` | Use `https://<host>.myhuaweicloud.com/...` (or `*.huaweicloud.com`); see [security-guide.md](security-guide.md) |

> Errors are **not retried automatically**. Fix the cause and re-run the script.
> See [SKILL.md](../SKILL.md) `## Error Handling` for the same contract in summary form.

### Issue: `--notify-url` notification was not delivered

**Symptom:** the result table prints normally, but stderr contains:

```
Warning: failed to send --notify-url notification: <message>
```

**Meaning:** the main query succeeded; only the webhook POST failed (network error, timeout, or a non-2xx
response). The **exit code is still `0`** — a notification failure never turns a successful query into an error.

**Solution:** verify the webhook endpoint is reachable and returns 2xx, and that the URL passes the HTTPS +
Huawei Cloud host allowlist. Use `--raw` or re-run without `--notify-url` to confirm the query data itself is fine.

**Success case:** when delivery succeeds the script prints `Results sent to webhook: <url>` on stdout.

---

## 8. Reference Documents

- [CLI Installation Guide](cli-installation-guide.md)
- [IAM Permission Policies](iam-policies.md)
- [Security Guide](security-guide.md)
- [Task 1: Query Tokens Usage](task-query-tokens-usage.md)
- [Verification Method](verification-method.md)
- [Acceptance Criteria](acceptance-criteria.md)
