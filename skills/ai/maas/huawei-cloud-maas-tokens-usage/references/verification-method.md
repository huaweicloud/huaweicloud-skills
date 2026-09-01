# Verification Method - MaaS Tokens Usage Query

This document describes how to verify a successful MaaS tokens usage query.

## Table of Contents

- [1. Prerequisite Verification](#1-prerequisite-verification)
  - [1.1 Verify Python3 and SDK](#11-verify-python3-and-sdk)
  - [1.2 Verify Credentials](#12-verify-credentials)
- [2. Functional Verification](#2-functional-verification)
- [3. End-to-End Verification Script](#3-end-to-end-verification-script)
- [4. Verification Checklist](#4-verification-checklist)
- [References](#references)

---

## 1. Prerequisite Verification

### 1.1 Verify Python3 and SDK

```bash
python3 --version  # Python3 >= 3.8
python3 -c "import huaweicloudsdkcore; print('SDK OK')"
python3 -c "import requests; print('requests OK')"
```

### 1.2 Verify Credentials

```bash
# Environment variables (values never printed)
python3 -c 'import os,sys;ak=os.environ.get("HW_ACCESS_KEY","");sk=os.environ.get("HW_SECRET_KEY","");ok=bool(ak) and bool(sk);print("AK/SK configured OK" if ok else "ERROR: HW_ACCESS_KEY/HW_SECRET_KEY not set");sys.exit(0 if ok else 1)'

# Or credentials file
ls -la /path/to/aksk.txt
```

---

## 2. Functional Verification

```bash
# Environment variables
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21

# Credentials file
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --credentials-file /path/to/aksk.txt

# Different service_type
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 1
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 4

# Batch inference
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --infer-type batch

# Raw response (for debugging)
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --raw
```

**Expected Output:**

```
MaaS Preset Service Usage Statistics - Region: cn-southwest-2
+────────────────────+──────────────────────+
| Metric               | Value                  |
+════════════════════+══════════════════════+
| Total Tokens         | 2,482.08 M tokens      |
| Prompt Tokens        | 2,456.50 M tokens      |
| Completion Tokens    | 24.87 M tokens         |
| Total Requests       | 67,188                 |
| Total Errors         | 8,002                  |
| Error Rate           | 11.91%                 |
+────────────────────+──────────────────────+
Period: 2026-05-08 00:00:00 ~ 2026-05-21 00:00:00 (CST)
```

---

## 3. End-to-End Verification Script

```bash
#!/bin/bash
set -e

echo "=== 1. Verify Python3 and SDK ==="
python3 --version
python3 -c "import huaweicloudsdkcore; print('SDK OK')"
python3 -c "import requests; print('requests OK')"

echo "=== 2. Verify Credentials ==="
python3 -c 'import os,sys;ak=os.environ.get("HW_ACCESS_KEY","");sk=os.environ.get("HW_SECRET_KEY","");ok=bool(ak) and bool(sk);print("AK/SK configured OK" if ok else "ERROR: HW_ACCESS_KEY/HW_SECRET_KEY not set");sys.exit(0 if ok else 1)'

echo "=== 3. Verify ShowStatistics API ==="
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21

echo "=== All verifications passed ==="
```

---

## 4. Verification Checklist

| Check | Expected Result |
|-------|-----------------|
| Python3 version | >= 3.8 |
| huaweicloudsdkcore | Import successful |
| requests | Import successful |
| Credentials | Environment variables or credentials file provided |
| ShowStatistics API | Returns 200, total_request_count > 0 |
| Script output format | Table + Period |
| Token unit conversion | M tokens (thousand × 1000 = actual tokens) |
| service_type | Supports 1/2/4 (not 3) |
| Region | cn-southwest-2 only |
| Timezone | Auto-detected OS local timezone |
| Console consistency | API vs. console discrepancy < 0.1% |

---

## References

| Document | Description |
|----------|-------------|
| [SKILL.md](../SKILL.md) | Skill overview and core workflows |
| [task-query-tokens-usage.md](task-query-tokens-usage.md) | Task 1 detailed steps |
| [acceptance-criteria.md](acceptance-criteria.md) | Acceptance criteria |
| [troubleshooting.md](troubleshooting.md) | Troubleshooting guide |
