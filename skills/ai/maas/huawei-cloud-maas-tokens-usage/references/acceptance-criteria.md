# Acceptance Criteria: huawei-cloud-maas-tokens-usage

**Scenario**: Huawei Cloud MaaS Tokens Usage Query (Python SDK signing + requests + MaaS ShowStatistics API)

## Table of Contents

- [1. Python SDK and Credentials Acceptance](#1-python-sdk-and-credentials-acceptance)
- [2. service_type Acceptance](#2-service_type-acceptance)
- [3. Credential Provision Acceptance](#3-credential-provision-acceptance)
- [4. Time Range Acceptance](#4-time-range-acceptance)
- [5. Timezone Acceptance](#5-timezone-acceptance)
- [6. Query Result Acceptance](#6-query-result-acceptance)
- [7. Security Criteria](#7-security-criteria)

---

## 1. Python SDK and Credentials Acceptance

### ✅ Correct

```bash
python3 -c "import huaweicloudsdkcore; print('SDK OK')"  # SDK signing library installed
python3 -c 'import os,sys;ak=os.environ.get("HW_ACCESS_KEY","");sk=os.environ.get("HW_SECRET_KEY","");ok=bool(ak) and bool(sk);print("AK/SK configured OK" if ok else "ERROR");sys.exit(0 if ok else 1)'
```

### ❌ Incorrect

```bash
ModuleNotFoundError: No module named 'huaweicloudsdkcore'
ERROR: HW_ACCESS_KEY/HW_SECRET_KEY not set
```

---

## 2. service_type Acceptance

### ✅ Correct

Use 1, 2, or 4:
```bash
--service-type 2   # Preset Service (default)
--service-type 1   # My Service
--service-type 4   # Custom Endpoint
```

### ❌ Incorrect

Use 3 (API does not support):
```bash
--service-type 3   # Returns 400 error: "service_type must be one of [1 2 4]"
```

---

## 3. Credential Provision Acceptance

### ✅ Correct

Environment variables or credentials file:
```bash
export HW_ACCESS_KEY=xxx && export HW_SECRET_KEY=xxx
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21

python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --credentials-file /path/to/aksk.txt
```

### ❌ Incorrect

Hardcode AK/SK in code:
```python
ak = "WTEBXXXXXX"
sk = "xxxxxxxxxx"
```

Ask user for AK/SK in conversation:
```
Please tell me your AK and SK
```

---

## 4. Time Range Acceptance

### ✅ Correct

Strictly distinguish "last 7 days" and "this month":
- "last 7 days": `--last-days 7` (today 00:00 local time back 6 days → **the current instant**, today included up to now)
- "this month": 1st of month 00:00:00 ~ today 00:00 (explicit `--from`/`--to`)
- Specific range: `--from 2026-05-08 --to 2026-05-21`
- Exactly one form is used: `--last-days N` **or** `--from` + `--to` (mutually exclusive)
- `--last-days 1` = today 00:00 until now (never a zero-length window)
- `--last-days N` stays inside the documented bound `1 <= N <= 3650` (`MAX_LAST_DAYS`)

### ❌ Incorrect

Confuse time ranges or misuse the options:
- User says "last 7 days" but calculate as "this month"
- User says "this month" but calculate as "last 30 days"
- Describe `--last-days N` as ending at today 00:00 (it ends at the current instant)
- Expect `--from 2026-07-01 --to 2026-07-01` to cover that whole day (both ends are local 00:00 → zero-length window)
- Pass `--last-days 7 --from ... --to ...` → `Error: --last-days cannot be combined with --from / --to.`
- Pass no time range at all → `Error: --from and --to are required unless --last-days is used.`
- Pass `--last-days 5000` → `Error: --last-days must not exceed 3650 days, got '5000'.`

---

## 5. Timezone Acceptance

### ✅ Correct

Follow OS local timezone, auto-detect via Python `datetime.now().astimezone()`.

### ❌ Incorrect

Hardcode `CST` or `Asia/Shanghai`:
```python
timezone = "Asia/Shanghai"  # Hardcoded, ignores OS timezone
```

---

## 6. Query Result Acceptance

### Output Format

| Metric | Expected |
|--------|----------|
| Total Tokens / Prompt Tokens / Completion Tokens | M tokens (always shown; thousand × 1000 = actual tokens) |
| Total Requests / Total Errors | Integer count (always shown) |
| Error Rate | Percentage (errors / requests × 100%; 0 requests → `0.00%`; always shown) |
| Completed Batch Tasks | Integer count (`total_completion_tasks`), **only if present in the response** |
| Total Inference Count | Integer count (`total_infer_count`), **only if present in the response** |
| Video Duration (s) | Numeric seconds (`video_generate_duration`), **only if present in the response** |
| Generated Images | Integer count (`image_generate_nums`), **only if present in the response** |
| Unmapped numeric fields | Appended by raw field name, only if present (no fabricated 0 rows) |
| Column widths | Adapt to the longest label/value printed |
| All-zero result | Table + **two** `Note: ...` lines on stdout (exit code 0, not an error) |
| Period | Start ~ End (auto-detected timezone) |

### Console Consistency

- API result should match Huawei Cloud console within < 0.1% discrepancy
- Minor boundary differences are normal and acceptable

---

## 7. Security Criteria

### ✅ Correct Security Practices

1. Credentials read from environment variables or credentials file; never provided in conversation
2. **Python SDK Signer** for AK/SK signing — credentials in process memory only
3. **Python requests** for HTTP POST — signed headers in process memory only
4. Temporary credentials add `X-Security-Token` via SDK signer (not CLI arg)
5. AK/SK never printed, never logged, never exported to shell
6. Credentials destroyed when Python process exits
7. Read-only IAM scope (`modelarts:monitoring:get`, `modelarts:service:get`, `iam:projects:get`)
8. `--notify-url` (if used) is HTTPS on a trusted Huawei Cloud host (`*.myhuaweicloud.com` / `*.huaweicloud.com`), with TLS verification on; a delivery failure is only a `Warning` and exit code stays 0

### ❌ Incorrect Security Practices

1. Provide AK/SK directly in conversation
2. Hardcode AK/SK in scripts
3. Use `curl` with `--header "Authorization: ..."` (visible in `ps -ef`)
4. Implement SDK-HMAC-SHA256 signing manually
5. Pass `X-Security-Token` via CLI argument
6. Print or log AK/SK values
7. Grant write/modify permissions beyond read-only scope
8. Point `--notify-url` at `http://`, an IP literal, or an arbitrary domain → rejected before the query is sent
9. Treat a failed `--notify-url` delivery as a query failure (the query succeeded; exit code stays 0)

### Webhook (`--notify-url`) Security Standards

| URL | Verdict | Description |
|-----|---------|-------------|
| `https://example.myhuaweicloud.com/hook` | ✅ Allowed | HTTPS + trusted Huawei Cloud subdomain |
| `https://myhuaweicloud.com/hook` | ✅ Allowed | Exact allowlisted domain |
| `http://example.myhuaweicloud.com/hook` | ❌ Prohibited | Plain HTTP rejected during validation |
| `https://1.2.3.4/hook` | ❌ Prohibited | IP literal rejected (SSRF) |
| `https://evil.example/hook` | ❌ Prohibited | Host outside the allowlist; nothing is sent |

### Credential Lifecycle Security Standards

| Method | Security | Description |
|--------|----------|-------------|
| Env vars + Python SDK Signer + Python requests | ✅ Secure | AK/SK in Python process memory only; signed in-process; destroyed on exit |
| Hardcoded AK/SK in script | ❌ Prohibited | Credentials leaked in source code |
| `curl` with `--header "Authorization: ..."` | ❌ Prohibited | Signed header visible in `ps -ef` |
| User-provided AK/SK in conversation | ❌ Prohibited | Credentials leaked in chat history |

### Tool Separation Standards

| Operation | Required Tool | Reason |
|-----------|--------------|--------|
| Credential loading | Python `os.environ` / file read | AK/SK in process memory only |
| Request signing | Python `huaweicloudsdkcore.Signer` | SDK-HMAC-SHA256 in-process; AK/SK never on CLI |
| HTTP POST | Python `requests` | Signed request from process memory; no `ps -ef` leakage |
| Timezone resolution | Python `datetime` | Auto-detect OS timezone; no hardcode |
| Time range segmentation | Python `datetime` | Auto-segment > 29 days; aggregate in memory |

---

## References

| Document | Description |
|----------|-------------|
| [SKILL.md](../SKILL.md) | Skill overview and core workflows |
| [security-design.md](security-design.md) | Security design: tool separation, credential lifecycle |
| [verification-method.md](verification-method.md) | Verification method |
