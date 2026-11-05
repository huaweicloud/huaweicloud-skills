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

# Rolling window: last 7 calendar days, today included up to the current instant
python3 scripts/maas_rest_usage_stats.py --last-days 7

# Credentials file
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --credentials-file /path/to/aksk.txt

# Different service_type
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 1
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 4

# Batch inference
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --infer-type batch

# Raw response (for debugging)
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --raw

# Optional webhook notification (HTTPS + Huawei Cloud host allowlist only)
python3 scripts/maas_rest_usage_stats.py --last-days 7 --notify-url https://example.myhuaweicloud.com/hook
```

**Expected Output** (5 core metrics + `Error Rate` always; other numeric fields only when present in the response; column widths adapt to the longest label — here `Completed Batch Tasks`, 21 chars):

```
MaaS Preset Service Usage Statistics - Region: cn-southwest-2
+─────────────────────+──────────────────────+
| Metric                | Value                  |
+═════════════════════+══════════════════════+
| Total Tokens          | 2,482.08 M tokens      |
| Prompt Tokens         | 2,456.50 M tokens      |
| Completion Tokens     | 24.87 M tokens         |
| Total Requests        | 67,188                 |
| Total Errors          | 8,002                  |
| Error Rate            | 11.91%                 |
| Completed Batch Tasks | 0                      |
| Total Inference Count | 0                      |
| Video Duration (s)    | 0                      |
| Generated Images      | 0                      |
+─────────────────────+──────────────────────+
Period: 2026-05-08 00:00:00 ~ 2026-05-21 00:00:00 (CST)
```

If all values are zero, the same table is followed on stdout by **two** lines:
`Note: no usage data in this period (all values are zero). Verify the time range, service type, infer type, and API key filter.`
`Note: if --from equals --to, the query window is a single instant (00:00-00:00); use a wider range or --last-days.`

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
| Output fields | 5 core metrics + Error Rate always printed; other numeric fields only when present in the response (never a fabricated 0 row) |
| Column widths | Adapt to the longest label/value printed |
| Time range arguments | Exactly one of `--last-days N` or `--from`+`--to`; neither → `Error: ...` on stderr, exit code 1 |
| `--last-days` window | `1 <= N <= 3650`; `from` = today-(N-1) 00:00 local, `to` = current instant (`--last-days 1` is not a zero-length window); `N > 3650` → `Error: --last-days must not exceed 3650 days, got '<v>'.` |
| Segmentation threshold | Split only when `(to - from).days > 29` |
| `--credentials-file` read failure | Missing → `Error: Credentials file not found: <path>`; directory/permission/non-UTF-8 → `Error: Cannot read credentials file <path>: <msg>` (both exit code 1) |
| `--from`/`--to` boundary | Both ends local 00:00; `--from` == `--to` is a zero-length window (documented limitation) |
| All-zero result | Table printed, then the two `Note: ...` lines on stdout, exit code 0 |
| `--notify-url` rejection | Non-HTTPS / IP literal / off-allowlist → `Error: --notify-url rejected: ...`, exit code 1, nothing sent |
| `--notify-url` delivery failure | Result printed, `Warning: failed to send --notify-url notification: ...` on stderr, exit code still 0 |
| Documented invalid parameters | Friendly `Error: ...` on stderr with exit code 1 (no raw traceback for the documented cases) |
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
