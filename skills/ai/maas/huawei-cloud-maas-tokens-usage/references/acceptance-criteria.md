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
- "last 7 days": now-7d ~ now (rolling window)
- "this month": 1st of month 00:00:00 ~ now (calendar month)
- Specific range: `--from 2026-05-08 --to 2026-05-21`

### ❌ Incorrect

Confuse time ranges:
- User says "last 7 days" but calculate as "this month"
- User says "this month" but calculate as "last 30 days"

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
| Total Tokens | M tokens (thousand × 1000 = actual tokens) |
| Prompt Tokens | M tokens |
| Completion Tokens | M tokens |
| Total Requests | Integer count |
| Total Errors | Integer count |
| Error Rate | Percentage (errors / requests × 100%) |
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

### ❌ Incorrect Security Practices

1. Provide AK/SK directly in conversation
2. Hardcode AK/SK in scripts
3. Use `curl` with `--header "Authorization: ..."` (visible in `ps -ef`)
4. Implement SDK-HMAC-SHA256 signing manually
5. Pass `X-Security-Token` via CLI argument
6. Print or log AK/SK values
7. Grant write/modify permissions beyond read-only scope

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
| Time range segmentation | Python `datetime` | Auto-segment > 30 days; aggregate in memory |

---

## References

| Document | Description |
|----------|-------------|
| [SKILL.md](../SKILL.md) | Skill overview and core workflows |
| [security-design.md](security-design.md) | Security design: tool separation, credential lifecycle |
| [verification-method.md](verification-method.md) | Verification method |
