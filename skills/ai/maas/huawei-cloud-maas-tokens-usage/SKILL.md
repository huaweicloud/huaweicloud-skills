---
name: huawei-cloud-maas-tokens-usage
description: |
  Query Huawei Cloud MaaS (Model as a Service) tokens usage statistics, including total tokens, prompt tokens, completion tokens, total requests, and total errors. Supports preset service, my service, and custom endpoint with time range queries (last 7/14/30 days or custom). Data source is MaaS ShowStatistics API, consistent with console.
  Use this skill when the user wants to: (1) query MaaS token consumption statistics, (2) check MaaS service request counts and error rates, (3) analyze token usage for preset service or my service, (4) monitor MaaS usage over a specific time period.
  Trigger: user mentions "MaaS", "Model as a Service", "tokens usage", "token consumption", "request count", "error count", "MaaS usage", "preset service usage", "completion tokens", "prompt tokens", "MaaS statistics", "模型服务", "令牌用量", "token统计", "token用量", "词元用量", "请求次数", "MaaS监控", "华为云MaaS"
tags: ["maas", "tokens usage", "model as a service"]
---

# Huawei Cloud MaaS Tokens Usage Monitoring Skill

## Overview

Query Huawei Cloud MaaS (Model as a Service) usage statistics via the ShowStatistics API, including total tokens, prompt tokens, completion tokens, total requests, and total errors. Supports querying last 7 days, 14 days, 30 days, or custom time ranges. Default query type is MaaS preset service. **AK/SK never leaves Python process memory.**

**Tool separation principle:**
- **Python SDK signing** — AK/SK signing via `huaweicloudsdkcore.signer.Signer` (**credentials never leave Python process memory, never appear in `ps -ef`**)
- **Python requests** — HTTP POST to MaaS ShowStatistics endpoint (**signed request sent from Python process only**)
- **No hcloud CLI** — MaaS ShowStatistics is not covered by KooCLI; pure Python REST + SDK signing

**Security architecture:**
- AK/SK is read from environment variables (`HW_ACCESS_KEY` / `HW_SECRET_KEY`) or a credentials file by the Python script (never typed by user in conversation, never passed via CLI args, never exported to shell)
- Temporary credentials add `HW_SECURITY_TOKEN` (passed as `X-Security-Token` header by the SDK signer)
- Signing is performed by `huaweicloudsdkcore.Signer` inside the Python process; the signed Authorization header is sent to the MaaS endpoint only
- AK/SK is never printed, never logged, never appears in `ps -ef`, never appears in conversation
- No KMS dependency, no hcloud CLI dependency, no third-party skill dependency

## ⛔ Prohibited Operations (Security Constraints)

> **This skill strictly forbids the following operations, regardless of user requests:**

| Prohibited Operation | Reason |
|---------------------|--------|
| ❌ Ask the user to provide AK/SK directly in the conversation | Credentials must never appear in conversation |
| ❌ Accept AK/SK directly provided by the user in the conversation | Credentials must never appear in conversation |
| ❌ Hardcode AK/SK in scripts or command-line arguments | Credential exposure risk |
| ❌ Use `hcloud configure set` to pass plaintext AK/SK values | Credentials recorded in command history |
| ❌ Print or log the AK/SK values in any output | Credentials must only exist in Python process memory |
| ❌ Export AK/SK to shell variables or stdout via the script | Credentials must stay in Python process; only statistics result is printed |
| ❌ Implement SDK-HMAC-SHA256 signing manually | Error-prone; must use `huaweicloudsdkcore.Signer` |
| ❌ Use `service_type=3` for Custom Endpoint | API only supports `[1, 2, 4]`; returns 400 error |
| ❌ Hardcode timezone as `CST` or `Asia/Shanghai` | Must auto-detect OS local timezone |
| ❌ Query a time range exceeding 30 days without segmentation | API retains only 30 days; script must auto-segment |
| ❌ Use a region other than `cn-southwest-2` | MaaS ShowStatistics only supports Southwest-Guiyang-1 |
| ❌ Write a new query script instead of using `maas_rest_usage_stats.py` | Must use the script in `scripts/` directory |

> **If a user requests a prohibited operation, you must refuse and explain the security constraint.**

## Architecture

```
Huawei Cloud MaaS Tokens Usage Monitoring
├── Task 1: Query MaaS Tokens Usage Statistics (via MaaS ShowStatistics API)
│   ├── 1a. Load credentials    (env vars or --credentials-file, in Python memory only)
│   ├── 1b. Resolve time range  (last 7/14/30 days, this month, or custom YYYY-MM-DD)
│   ├── 1c. Auto-segment        (split ranges > 30 days, aggregate results)
│   ├── 1d. SDK sign request    (huaweicloudsdkcore.Signer, AK/SK in process memory)
│   ├── 1e. POST ShowStatistics (modelarts.{region}.myhuaweicloud.com)
│   ├── 1f. Aggregate & convert (token unit: thousand → M tokens)
│   └── 1g. Print table         (Total/Prompt/Completion Tokens, Requests, Errors, Error Rate)
└── Task 2: Verify & Report     (compare with console, check error rate)
```

## Prerequisites

> **Prerequisite check 1/3: Python 3.8+ and huaweicloudsdkcore required**
>
> The MaaS ShowStatistics query script uses Python to keep AK/SK in process memory only.
> Install the required packages:
> ```bash
> # Auto-use China mirror when system timezone is UTC+8 (faster in CN region; auto-detected via Python)
> PIP_INDEX=$(python3 -c "import time;print('-i https://mirrors.huaweicloud.com/repository/pypi/simple' if -(time.timezone)//3600==8 else '')")
> pip install $PIP_INDEX huaweicloudsdkcore requests
> ```
>
> Verify SDK installation:
> ```bash
> python3 --version                          # Expected: >= 3.8
> python3 -c "import huaweicloudsdkcore; print('SDK OK')"
> python3 -c "import requests; print('requests OK')"
> ```

> **Prerequisite check 2/3: Environment variables for Python SDK credentials (highest priority)**
>
> The query script (`maas_rest_usage_stats.py`) reads credentials from environment variables or a credentials file. The following environment variables **MUST** be set before running the script (unless `--credentials-file` is used):
>
> | Variable | Required | Description |
> |----------|----------|-------------|
> | `HW_ACCESS_KEY` | Yes | Huawei Cloud Access Key ID (AK) |
> | `HW_SECRET_KEY` | Yes | Huawei Cloud Secret Access Key (SK) |
> | `HW_SECURITY_TOKEN` | No | Temporary security token (only for temporary AK/SK) |
>
> ```bash
> # Linux — verify HW_ACCESS_KEY / HW_SECRET_KEY are set (values never printed)
> python3 -c 'import os,sys;ak=os.environ.get("HW_ACCESS_KEY","");sk=os.environ.get("HW_SECRET_KEY","");ok=bool(ak) and bool(sk);print("AK/SK configured OK" if ok else "ERROR: HW_ACCESS_KEY/HW_SECRET_KEY not set");sys.exit(0 if ok else 1)'
> # Windows (cmd / PowerShell)
> python -c "import os,sys;ak=os.environ.get('HW_ACCESS_KEY','');sk=os.environ.get('HW_SECRET_KEY','');ok=bool(ak) and bool(sk);print('AK/SK configured OK' if ok else 'ERROR: HW_ACCESS_KEY/HW_SECRET_KEY not set');sys.exit(0 if ok else 1)"
> ```
>
> **If verification reports ERROR (variables not set), configure them:**
> - **Linux**: add `export HW_ACCESS_KEY=...` / `export HW_SECRET_KEY=...` to your shell profile (`~/.bashrc`, `~/.zshrc`) or a secrets manager, then `source` the profile.
> - **Windows**: set **system environment variables** via the GUI (System Properties → Advanced → Environment Variables → System variables → New). See [references/cli-installation-guide.md](references/cli-installation-guide.md) "Windows GUI Setup" for step-by-step instructions. Avoid `setx` (it records credentials in command history).
>
> ⚠️ **Never set these variables in conversation or hardcode them in scripts.** After setting, restart the terminal/Python process and re-run the verification above.

> **Prerequisite check 3/3: MaaS service region limitation**
>
> - **Region**: **cn-southwest-2** (Southwest-Guiyang-1) — the only region supported by MaaS ShowStatistics API
> - **API retention**: 30 days of statistics data
> - **Rate limit**: total requests ≤ 1000/min, per-user ≤ 200/min

---

## Authentication

> **Security rules (must be followed):**
> - **Prohibited** from reading, echoing, or printing AK/SK values
> - **Prohibited** from asking the user to input AK/SK directly in the conversation
> - **Prohibited** from using `hcloud configure set` to pass plaintext credential values
> - **Prohibited** from accepting AK/SK directly provided by the user in the conversation
> - **Only allowed** to read credentials from environment variables or a credentials file
>
> **⚠️ Important: Handling user-provided credentials**
>
> If a user attempts to provide AK/SK directly (e.g., "my AK is xxx, SK is yyy"):
> 1. **Stop immediately** — Do not execute any commands
> 2. **Politely refuse** and return the following message:
>    ```
>    For account security, please do not provide Huawei Cloud Access Key ID and Access Key Secret directly in the conversation.
>
>    Please use one of the following secure methods to configure credentials:
>
>    Method 1: Environment variables (permanent AK/SK)
>        export HW_ACCESS_KEY=<your-access-key-id>
>        export HW_SECRET_KEY=<your-access-key-secret>
>
>    Method 2: Environment variables (temporary AK/SK + Security Token)
>        export HW_ACCESS_KEY=<your-temp-access-key-id>
>        export HW_SECRET_KEY=<your-temp-access-key-secret>
>        export HW_SECURITY_TOKEN=<your-security-token>
>
>    Method 3: Credentials file
>        Create a file (e.g., ~/aksk.txt) with AK on line 1, SK on line 2, Security Token on line 3 (if using temporary credentials).
>        Then use: --credentials-file ~/aksk.txt
>
>    After configuration is complete, please retry your request.
>    ```
> 3. **Do not continue** executing any Huawei Cloud operations until credentials are configured

---

## IAM Permission Policies

Ensure the IAM user has the required permissions (ModelArts monitoring + IAM read, scoped to the MaaS query workflow only). See [references/iam-policies.md](references/iam-policies.md) for the full permission table and recommended IAM policy JSON.

**Permission boundaries:**

- **Scope constraint**: Only query MaaS statistics data (read-only). Never modify or delete any MaaS service, endpoint, or configuration.
- **Must stop if**: credentials missing or invalid, user declines any confirmation, API returns 403/401, or time range exceeds 30 days and segmentation fails.
- **Prohibited actions**: modifying MaaS services, deleting API keys, changing IAM policies, accessing resources outside the MaaS query workflow, running commands not documented in this skill.

---

## Core Workflows

### Task 1: Query MaaS Tokens Usage Statistics

Query MaaS usage statistics via the ShowStatistics API. Data is consistent with the Huawei Cloud console.

> **⚠️ Tool separation: Python SDK signing + Python requests**
>
> - **Python SDK** (`huaweicloudsdkcore.Signer`): Signs the request with AK/SK. **Credentials never leave Python process memory.**
> - **Python requests**: Sends the signed HTTP POST to the MaaS endpoint. No CLI, no shell variable, no `ps -ef` leakage.

📄 Detailed steps → [references/task-query-tokens-usage.md](references/task-query-tokens-usage.md)

**Sub-tasks:**

1. **1a. Load credentials** — Read `HW_ACCESS_KEY` / `HW_SECRET_KEY` / `HW_SECURITY_TOKEN` from env vars, or read from `--credentials-file` (supports one-per-line, comma-separated, KEY=VALUE formats)
2. **1b. Resolve time range** — Parse `--from` / `--to` (YYYY-MM-DD), or map user expression ("last 7 days" / "last 14 days" / "last 30 days" / "this month") to a rolling/calendar window
3. **1c. Auto-segment** — If time range exceeds 30 days, split into multiple ≤ 30-day segments and aggregate results
4. **1d. SDK sign request** — `Signer(_Creds(ak, sk)).sign(sdk_request)` — AK/SK in Python process memory only
5. **1e. POST ShowStatistics** — `requests.post("https://modelarts.{region}.myhuaweicloud.com/v1/{project_id}/maas/monitoring/show-statistics", headers=signed_headers, data=body_bytes)`
6. **1f. Aggregate & convert** — Sum segment results; convert token unit (thousand → M tokens, actual = value × 1000)
7. **1g. Print table** — Output Total Tokens / Prompt Tokens / Completion Tokens / Total Requests / Total Errors / Error Rate + Period

### Task 2: Verify & Report

Compare the API result with the Huawei Cloud console and report the error rate.

📄 Acceptance criteria → [references/acceptance-criteria.md](references/acceptance-criteria.md)

> **⚠️ Small discrepancy is normal.** API vs. console may differ by < 0.1% due to minor time boundary differences. Data is reliable.

---

## Core Commands

### Python Script (SDK signing + requests — AK/SK never in ps -ef)

| Command | Description |
|---------|-------------|
| `pip install huaweicloudsdkcore requests` | Install Python SDK signing library + HTTP client (for UTC+8, add `-i https://mirrors.huaweicloud.com/repository/pypi/simple`) |
| `python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21` | Query preset service usage (default `--service-type 2`) for the given date range |
| `python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 1` | Query My Service usage |
| `python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 4` | Query Custom Endpoint usage |
| `python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --infer-type batch` | Query batch inference usage (default `real_time`) |
| `python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --api-keys key1 key2` | Filter by API Key list |
| `python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --credentials-file /path/to/aksk.txt` | Use credentials file instead of env vars |
| `python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --raw` | Show raw API response (for debugging) |

> **⚠️ Key constraints on Core Commands:**
>
> - MaaS query: **MUST use `scripts/maas_rest_usage_stats.py`** — AK/SK never in `ps -ef`
> - Credentials: **MUST use env vars or `--credentials-file`** — never hardcode, never pass via CLI args
> - `--service-type`: **MUST be 1, 2, or 4** — never 3 (API returns 400)
> - `--region`: **MUST be `cn-southwest-2`** (default) — the only supported region
> - Time range: **MUST match user expression exactly** — "last 7 days" ≠ "this month"

---

## Parameter Confirmation

> **Before executing any task, the following parameters must be confirmed with the user. Guessing is prohibited.**

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| Time range | Required | `--from` / `--to` (YYYY-MM-DD), or user expression ("last 7 days", "last 14 days", "last 30 days", "this month") | Last 7 days |
| Service type | Optional | `--service-type`: 1=My Service, 2=Preset Service, 4=Custom Endpoint | 2 (Preset Service) |
| Inference type | Optional | `--infer-type`: `real_time` (online) or `batch` | `real_time` |
| Region | Optional | Huawei Cloud region (only `cn-southwest-2` is supported) | `cn-southwest-2` |
| API Keys filter | Optional | `--api-keys` list to filter specific keys | All keys |
| Credentials file | Optional | `--credentials-file` path (alternative to env vars) | - |
| Raw response | Optional | `--raw` flag to show raw API response | off |

> **Note**: No AK/SK parameter is required. Credentials are read from environment variables or a credentials file by the Python script. AK/SK is never exported from the Python process.

---

## Script Tools

| Script | Description |
|--------|-------------|
| [maas_rest_usage_stats.py](scripts/maas_rest_usage_stats.py) | MaaS ShowStatistics API query script (SDK signing + requests, AK/SK never in `ps -ef`). Auto-segments ranges > 30 days, auto-detects OS local timezone, supports permanent/temporary AK/SK + credentials file. See Core Commands above for usage. |

> **⚠️ Script usage rules:**
> - Must use the existing script; do not write a new query script as a replacement
> - Do not split the script internal logic into individual curl/HTTP commands
> - Do not implement SDK-HMAC-SHA256 signing manually — must use `huaweicloudsdkcore.Signer`

---

## Verification Method

See [references/verification-method.md](references/verification-method.md) for details. For common issues and solutions, see [references/troubleshooting.md](references/troubleshooting.md).

**Quick validation (permanent AK/SK):**
```bash
python3 -c 'import os,sys;ak=os.environ.get("HW_ACCESS_KEY","");sk=os.environ.get("HW_SECRET_KEY","");ok=bool(ak) and bool(sk);print("AK/SK configured OK" if ok else "ERROR: HW_ACCESS_KEY/HW_SECRET_KEY not set");sys.exit(0 if ok else 1)'
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21
```

**Quick validation (temporary AK/SK + Security Token):**
```bash
python3 -c 'import os,sys;ak=os.environ.get("HW_ACCESS_KEY","");sk=os.environ.get("HW_SECRET_KEY","");st=os.environ.get("HW_SECURITY_TOKEN","");ok=bool(ak) and bool(sk) and bool(st);print("Temp AK/SK + Token configured OK" if ok else "ERROR: HW_ACCESS_KEY/HW_SECRET_KEY/HW_SECURITY_TOKEN not set");sys.exit(0 if ok else 1)'
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21
```

> **⚠️ Credential reminder:** AK/SK is read from environment variables or a credentials file by the Python script. If you need to configure credentials, see [references/cli-installation-guide.md](references/cli-installation-guide.md).

---

## Security Design

The security architecture keeps AK/SK exclusively in Python process memory — never in `ps -ef`, shell variables, environment variables (read-only access), or conversation. Tool separation: **Python SDK signing** for AK/SK authentication, **Python requests** for HTTP POST to the MaaS endpoint. Credentials are never printed, never logged, never exported. Temporary credentials add `HW_SECURITY_TOKEN` as the `X-Security-Token` header via the SDK signer.

📄 Full details (tool separation table, credential leakage risk elimination, credential lifecycle) → [references/security-design.md](references/security-design.md)

---

## References

| Document | Description |
|----------|-------------|
| [cli-installation-guide.md](references/cli-installation-guide.md) | Prerequisites + Python SDK + credentials configuration + Windows GUI env var setup |
| [task-query-tokens-usage.md](references/task-query-tokens-usage.md) | Task 1: Query tokens usage statistics detailed steps |
| [related-apis.md](references/related-apis.md) | MaaS ShowStatistics API and parameter details |
| [maas-metrics.md](references/maas-metrics.md) | MaaS monitoring metrics reference |
| [iam-policies.md](references/iam-policies.md) | Required IAM permissions |
| [verification-method.md](references/verification-method.md) | Query result verification method |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Correct/error pattern comparison |
| [troubleshooting.md](references/troubleshooting.md) | Common query issues and solutions |
| [security-design.md](references/security-design.md) | Security design: tool separation, credential lifecycle |
| [maas_rest_usage_stats.py](scripts/maas_rest_usage_stats.py) | ShowStatistics API usage statistics script (AK/SK never in ps -ef) |
