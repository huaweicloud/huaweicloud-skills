---
name: huawei-cloud-maas-tokens-usage
description: |
  Query Huawei Cloud MaaS (Model as a Service) tokens usage statistics, including total tokens, prompt tokens, completion tokens, total requests, and total errors. Read-only queries, supports preset service, my service, and custom endpoint with time range queries (rolling last N days via --last-days, last 7/14/30 days, or a custom --from/--to range). Data source is MaaS ShowStatistics API, consistent with console.
  Use this skill when the user wants to: (1) query MaaS token consumption statistics, (2) check MaaS service request counts and error rates, (3) analyze token usage for preset service or my service, (4) monitor MaaS usage over a specific time period.
  Trigger: user mentions "MaaS", "Model as a Service", "tokens usage", "token consumption", "request count", "error count", "MaaS usage", "preset service usage", "completion tokens", "prompt tokens", "MaaS statistics", "模型服务", "令牌用量", "token统计", "token用量", "词元用量", "请求次数", "MaaS监控", "华为云MaaS"
  Trigger (verb-style phrasings): user says "查询MaaS用量", "MaaS用量查询", "查询token用量", "统计MaaS令牌用量", "查询MaaS请求次数", "MaaS监控数据查询", "检查MaaS错误率", "query MaaS usage statistics", "check MaaS tokens usage", "search MaaS usage", "find MaaS token consumption", "browse MaaS statistics", "discover MaaS resource usage"
tags: ["maas", "tokens usage", "model as a service", "huawei-cloud", "statistics", "readonly", "monitoring", "token usage"]
---

# Huawei Cloud MaaS Tokens Usage Monitoring Skill

## Overview

Query Huawei Cloud MaaS (Model as a Service) usage statistics via the ShowStatistics API, including total tokens, prompt tokens, completion tokens, total requests, and total errors. Supports querying a rolling last N days via `--last-days N` (7/14/30 days, …) or a custom `--from`/`--to` time range. Default query type is MaaS preset service. **AK/SK never leaves Python process memory.**

**Capability type: `readonly` — read-only queries only.** This skill **only reads** data: the IAM `GET /v3/projects` project lookup plus the MaaS ShowStatistics query API. It performs **no create / update / delete / write operation** on any Huawei Cloud resource, no configuration change, no state mutation, and no resource provisioning; every command it runs is an idempotent query. The optional `--notify-url` webhook is an outbound POST of the query summary to a **trusted Huawei Cloud host only** (HTTPS enforced, TLS verification on) — it does not modify any resource.

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
| ❌ Query a time range longer than 29 days without segmentation | The API retains only 30 days of data, and a single request must span ≤ 29 days; the script auto-segments ranges > 29 days |
| ❌ Use a region other than `cn-southwest-2` | MaaS ShowStatistics only supports Southwest-Guiyang-1 |
| ❌ Point `--notify-url` at an HTTP URL, an IP literal, or any host outside `*.myhuaweicloud.com` / `*.huaweicloud.com` | SSRF/exfiltration risk; the script rejects such URLs before sending the query |
| ❌ Disable TLS verification for the notification (`verify=False`) | Notification must keep `verify=True` |
| ❌ Write a new query script instead of using `maas_rest_usage_stats.py` | Must use the script in `scripts/` directory |

> **If a user requests a prohibited operation, you must refuse and explain the security constraint.**

## 🚫 Unsupported Operations (Capability Boundary)

> **This skill only supports the ShowStatistics aggregate statistics query. The MaaS monitoring API family contains 10 APIs; the other 9 are outside this skill's capability boundary and are not implemented.**

| Unsupported API | Purpose | Why Not Covered |
|-----------------|---------|-----------------|
| `ListServiceStatistics` | List per-service statistics | Skill focuses on aggregate tokens usage, not per-service breakdown |
| `ShowDetailChart` | Show detail chart data | Skill returns a summary table, not chart series |
| `ListErrors` | List error details | Skill reports error count/rate only, not error detail records |
| `ListServices` | List services | Skill queries statistics, not service inventory |
| `ListSourceIps` | List source IPs | Skill does not track caller IP distribution |
| `GetServiceDetailMetricData` | Get service detail metrics | Skill provides aggregate metrics, not per-service detail |
| `ListVersionStatistics` | List version statistics | Skill does not segment by model version |
| `GetGenerationSupportedMetrics` | Get supported metrics | Skill uses the fixed metric set from ShowStatistics response |
| `ShowErrorCodeChart` | Show error code chart | Skill reports error rate, not error code distribution |

> **If a user requests any of the above APIs or their underlying capabilities (per-service breakdown, error detail, chart data, source IP list, version statistics, error code distribution, etc.), you must refuse and clarify: this skill only supports the ShowStatistics aggregate statistics query (total/prompt/completion tokens, request count, error count, error rate).**

## Architecture

```
Huawei Cloud MaaS Tokens Usage Monitoring  (read-only; no write operations on any resource)
├── Task 1: Query MaaS Tokens Usage Statistics (via MaaS ShowStatistics API)
│   ├── 1a. Load credentials    (env vars or --credentials-file, in Python memory only)
│   ├── 1b. Resolve time range  (last 7/14/30 days, this month, or custom YYYY-MM-DD)
│   ├── 1c. Auto-segment        (split ranges > 29 days, aggregate results)
│   ├── 1d. SDK sign request    (huaweicloudsdkcore.Signer, AK/SK in process memory)
│   ├── 1e. POST ShowStatistics (modelarts.{region}.myhuaweicloud.com)
│   ├── 1f. Aggregate & convert (token unit: thousand → M tokens)
│   ├── 1g. Print table         (all fields present in the response + Period)
│   └── 1h. Optional webhook    (--notify-url: POST summary JSON, HTTPS trusted host)
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
> | `HW_ACCESS_KEY` | Yes | Huawei Cloud Access Key ID (AK) — permanent or temporary |
> | `HW_SECRET_KEY` | Yes | Huawei Cloud Secret Access Key (SK) — permanent or temporary |
> | `HW_SECURITY_TOKEN` | Only for temporary AK/SK | Temporary security token. **Required whenever `HW_ACCESS_KEY`/`HW_SECRET_KEY` are temporary**; the SDK signer sends it as the `X-Security-Token` request header. Never passed as a CLI argument. |
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
>
> **Temporary AK/SK (STS) example** — `HW_SECURITY_TOKEN` is read by the script and forwarded to the SDK signer as `X-Security-Token`:
> ```bash
> export HW_ACCESS_KEY=<your-temp-access-key-id>
> export HW_SECRET_KEY=<your-temp-access-key-secret>
> export HW_SECURITY_TOKEN=<your-security-token>
> python3 scripts/maas_rest_usage_stats.py --last-days 7
> ```
>
> **Credentials file (`--credentials-file`) — three supported formats, all of them support the Security Token:**
>
> | Format | Layout | Example |
> |--------|--------|---------|
> | `KEY=VALUE` | one assignment per line | `HW_ACCESS_KEY=<your-ak>` / `HW_SECRET_KEY=<your-sk>` / `HW_SECURITY_TOKEN=<your-token>` |
> | CSV | **third column** carries the token | `<your-ak>,<your-sk>,<your-token>` |
> | one value per line | **third line** carries the token | line 1 = AK, line 2 = SK, line 3 = `HW_SECURITY_TOKEN` |
>
> ```bash
> # creds.txt (one value per line, temporary credentials)
> #   line 1: <your-temp-access-key-id>
> #   line 2: <your-temp-access-key-secret>
> #   line 3: <your-security-token>
> python3 scripts/maas_rest_usage_stats.py --credentials-file ./creds.txt --last-days 7
> ```
>
> For permanent AK/SK the third column/line may be omitted. Full details: [references/security-guide.md](references/security-guide.md) and [references/cli-installation-guide.md](references/cli-installation-guide.md).

> **Prerequisite check 3/3: MaaS service region limitation**
>
> - **Region**: **cn-southwest-2** (Southwest-Guiyang-1) — the only region supported by MaaS ShowStatistics API
> - **API retention**: 30 days of statistics data
> - **Rate limit**: total requests ≤ 1000/min, per-user ≤ 200/min

---

## Authentication

> **Security rules (summary — must be followed):**
> - **Prohibited**: reading, echoing, or printing AK/SK values; asking the user to input AK/SK directly in the conversation; accepting AK/SK the user provides directly in the conversation; passing plaintext credential values via `hcloud configure set` or any CLI argument.
> - **Only allowed**: read credentials from environment variables (`HW_ACCESS_KEY` / `HW_SECRET_KEY` / `HW_SECURITY_TOKEN`) or from a credentials file via `--credentials-file`; credentials stay in Python process memory only.
> - **If the user offers AK/SK directly** (e.g. "my AK is xxx, SK is yyy"): stop immediately, execute no command, politely refuse, and reply with the secure-configuration template — then **do not continue** any Huawei Cloud operation until credentials are configured.

📄 Full refusal template, credential configuration methods, and credentials-file formats → [references/security-guide.md](references/security-guide.md)

---

## Error Handling

> **All documented failure modes and invalid CLI input are reported on `stderr` as `Error: ...` with exit code `1`; nothing is silently swallowed, and AK/SK values never appear in error output.** Parameter validation runs **before** credentials are read, so invalid arguments produce a parameter error even with no credentials configured (offline-reproducible). Errors are not retried automatically — fix the cause and re-run.

| Failure scenario | Script message (stderr; first line starts with `Error: `) | Resolution |
|------------------|-----------------------------------------------------------|------------|
| Neither `--last-days` nor `--from`/`--to` given | `Error: --from and --to are required unless --last-days is used.` | Pass `--from` + `--to`, or `--last-days N` |
| `--last-days` combined with `--from`/`--to` (mutually exclusive) | `Error: --last-days cannot be combined with --from / --to.` | Use exactly one of the two forms |
| `--last-days` is not a positive integer | `Error: --last-days must be a positive integer, got '<v>'.` | Pass an integer in `1 <= N <= 3650` |
| `--last-days` above the upper bound (`N > 3650`) | `Error: --last-days must not exceed 3650 days, got '<v>'.` | Use `1 <= N <= 3650` (`MAX_LAST_DAYS`, 10 years) |
| Invalid date format | `Error: Invalid <--from\|--to> date format: '<v>'`<br>`       Date format should be YYYY-MM-DD, e.g. 2026-08-10` | Use `YYYY-MM-DD` |
| `--from` later than `--to` | `Error: --from (<f>) must not be later than --to (<t>).` | Fix the date order |
| `--region` outside the whitelist (invalid region) | `Error: Unsupported region '<r>'. MaaS ShowStatistics only supports: cn-southwest-2.` | Use `--region cn-southwest-2` (the only supported region) |
| Credentials missing | `Error: Credentials not found. Provide AK/SK via:` (4-line hint block) | Set env vars or pass `--credentials-file` |
| `--credentials-file` path does not exist | `Error: Credentials file not found: <path>` | Check the path |
| `--credentials-file` exists but cannot be read (directory, permission denied, non-UTF-8 bytes, other `OSError`) | `Error: Cannot read credentials file <path>: <msg>` | Path must be a **readable UTF-8 text file** (not a directory; correct permissions/encoding) |
| Network unreachable / DNS / proxy failure | `Error: Cannot reach <host> (<ExcName>): <msg>`<br>`       Check --region, network connectivity, proxy/firewall settings, and that credentials are valid.` | Check region, network, proxy/firewall, credentials |
| API or SDK failure, including non-200 (400/401/403) | `Error: <original error message>`<br>`       Check the request parameters, region, and credential permissions (401/403 = credentials/IAM).` | Check parameters, region, IAM permissions |
| Query succeeded but all values are zero | Two lines on **stdout** after the `Period:` line — **not an error**, exit code `0`:<br>`Note: no usage data in this period (all values are zero). Verify the time range, service type, infer type, and API key filter.`<br>`Note: if --from equals --to, the query window is a single instant (00:00-00:00); use a wider range or --last-days.` | Widen/verify the time range (or use `--last-days`), `--service-type`, `--infer-type`, and `--api-keys` |
| `--notify-url` not HTTPS, or host not on the Huawei Cloud allowlist (incl. IP literals) | `Error: --notify-url rejected: only HTTPS URLs on trusted Huawei Cloud hosts (*.myhuaweicloud.com / *.huaweicloud.com) are allowed; the request was NOT sent.` (rejected during parameter validation — the query is **not** sent) | Use an HTTPS URL whose host is `myhuaweicloud.com` / `huaweicloud.com` or a subdomain of either (never an IP literal) |
| `--notify-url` delivery failed (network / non-2xx) | Query result prints normally; stderr: `Warning: failed to send --notify-url notification: <msg>` — **exit code stays `0`** | Check the webhook endpoint; the main query already succeeded |

> See [references/troubleshooting.md](references/troubleshooting.md) for symptoms, root causes, and fixes of each scenario.

---

## IAM Permission Policies

Ensure the IAM user has the required permissions (ModelArts monitoring + IAM read, scoped to the MaaS query workflow only). See [references/iam-policies.md](references/iam-policies.md) for the full permission table and recommended IAM policy JSON.

**Permission boundaries:**

- **Scope constraint**: Only query MaaS statistics data (read-only). Never modify or delete any MaaS service, endpoint, or configuration.
- **Must stop if**: credentials missing or invalid, user declines any confirmation, API returns 403/401, or the requested range spans more than 29 days and segmentation fails.
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

1. **1a. Load credentials** — Read `HW_ACCESS_KEY` / `HW_SECRET_KEY` / `HW_SECURITY_TOKEN` from env vars, or read them from `--credentials-file` (all three formats support the token: `KEY=VALUE`, CSV third column, or one-value-per-line third line; see [references/security-guide.md](references/security-guide.md))
2. **1b. Resolve time range** — Use `--last-days N` with **`1 <= N <= 3650`**: the **last N calendar days**, with `from` = local `today - (N-1)` at 00:00 and `to` = **the current instant** (so today's data up to now is included; `--last-days 1` = today 00:00 until now). Alternatively parse `--from` / `--to` (`YYYY-MM-DD`, both at local 00:00); map user expressions ("last 7 days" / "last 14 days" / "last 30 days" / "this month") to a calendar window. `--last-days` and `--from`/`--to` are mutually exclusive
3. **1c. Auto-segment** — If the **whole-day span** `(to - from).days` is more than 29 days, split into multiple ≤ 29-day segments and aggregate results
4. **1d. SDK sign request** — `Signer(_Creds(ak, sk)).sign(sdk_request)` — AK/SK in Python process memory only
5. **1e. POST ShowStatistics** — `requests.post("https://modelarts.{region}.myhuaweicloud.com/v1/{project_id}/maas/monitoring/show-statistics", headers=signed_headers, data=body_bytes)`
6. **1f. Aggregate & convert** — Sum segment results; convert token unit (thousand → M tokens, actual = value × 1000)
7. **1g. Print table** — Print the 5 core metrics plus `Error Rate` (always), then one row for every other numeric field **actually present in the response** (see "Output fields" below), then `Period: <start> ~ <end> (<tz>)`; if every value is zero, append the two-line no-usage note after `Period:`
8. **1h. Optional webhook** — If `--notify-url URL` is given (validated: HTTPS + trusted Huawei Cloud host), POST the summary JSON (`region`, `period`, `total_tokens`, `prompt_tokens`, `completion_tokens`, `total_requests`, `total_errors`) and print `Results sent to webhook: <url>`; delivery failures only print a `Warning: ...` and never change exit code 0

**Output fields (Gap-2 — no returned field is dropped):** the table always shows the 5 core metrics and `Error Rate` (missing core fields count as 0, master behavior). Every other numeric field is shown **only if the response actually contains it** — the script never invents a `0` row for an absent field. Extra rows follow the fixed order below; any numeric response key that is not mapped is appended last, labeled with its raw key.

| Table row label | API field | Format | Shown when |
|-----------------|-----------|--------|------------|
| `Total Tokens` | `total_token` | token unit (`fmt_tokens`, thousand → M/K tokens) | always (missing → 0) |
| `Prompt Tokens` | `total_prompt_token` | token unit | always (missing → 0) |
| `Completion Tokens` | `total_completion_token` | token unit | always (missing → 0) |
| `Total Requests` | `total_request_count` | thousands separator | always (missing → 0) |
| `Total Errors` | `total_error_count` | thousands separator | always (missing → 0) |
| `Error Rate` | `total_error_count` / `total_request_count` × 100 | `0.00%` (denominator 0 → `0.00%`) | always (computed) |
| `Completed Batch Tasks` | `total_completion_tasks` | thousands separator | only if present in the response |
| `Total Inference Count` | `total_infer_count` | thousands separator | only if present in the response |
| `Video Duration (s)` | `video_generate_duration` | numeric (seconds) | only if present in the response |
| `Generated Images` | `image_generate_nums` | thousands separator | only if present in the response |
| *(any other numeric key)* | raw API key used as label | numeric | only if present, appended in ascending field-name order |

> Multi-segment queries (whole-day span `(to - from).days > 29` is auto-segmented) sum each field across the segments that returned it. Column widths adapt to the longest label/value actually printed. `--raw` still prints the untouched per-segment JSON.

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
| `python3 scripts/maas_rest_usage_stats.py --last-days 7` | Query the last 7 calendar days (`from` = today-6 at 00:00 local time, `to` = now); **cannot be combined with `--from`/`--to`** |
| `python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 1` | Query My Service usage |
| `python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 4` | Query Custom Endpoint usage |
| `python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --infer-type batch` | Query batch inference usage (default `real_time`) |
| `python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --api-keys key1 key2` | Filter by API Key list |
| `python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --credentials-file /path/to/aksk.txt` | Use credentials file instead of env vars |
| `python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --raw` | Show raw API response (for debugging) |
| `python3 scripts/maas_rest_usage_stats.py --last-days 7 --notify-url https://example.myhuaweicloud.com/hook` | After the query, POST the summary JSON to the webhook (only HTTPS + trusted Huawei Cloud hosts) and print `Results sent to webhook: <url>` |

> **⚠️ Key constraints on Core Commands:**
>
> - MaaS query: **MUST use `scripts/maas_rest_usage_stats.py`** — AK/SK never in `ps -ef`
> - Credentials: **MUST use env vars or `--credentials-file`** — never hardcode, never pass via CLI args
> - `--service-type`: **MUST be 1, 2, or 4** — never 3 (API returns 400)
> - `--region`: **MUST be `cn-southwest-2`** (default) — the only supported region
> - Time range: **MUST match user expression exactly** — "last 7 days" ≠ "this month"
> - Time range arguments: **`--last-days` and `--from`/`--to` are mutually exclusive**; at least one form must be provided; `--last-days` accepts only `1 <= N <= 3650`
> - `--notify-url`: **MUST be HTTPS on `*.myhuaweicloud.com` / `*.huaweicloud.com`** (IP literals and other hosts are rejected during validation, before any query is sent)

---

## Parameter Confirmation

> **Before executing any task, the following parameters must be confirmed with the user. Guessing is prohibited.**

| CLI Parameter | Required / Optional | Description | Default |
|---------------|---------------------|-------------|---------|
| `--from` | Conditionally required | Start date `YYYY-MM-DD` (local-timezone 00:00). Required unless `--last-days` is used. **Mutually exclusive with `--last-days`** | — |
| `--to` | Conditionally required | End date `YYYY-MM-DD` (local-timezone 00:00). Required unless `--last-days` is used. **Mutually exclusive with `--last-days`** | — |
| `--last-days` | Optional | Integer in **`1 <= N <= 3650`** (`MAX_LAST_DAYS`): the **last N calendar days** — `from` = local `today - (N-1)` at 00:00, `to` = **the current instant** (today's data up to now is included; `--last-days 1` = today 00:00 until now). The upper bound exists because the script segments at 29 days (longer windows would fire hundreds of serial requests) and MaaS retains only 30 days of data; `N > 3650` fails with `Error: --last-days must not exceed 3650 days, got '<v>'.` **Mutually exclusive with `--from`/`--to`** | — |
| `--region` | Optional | Huawei Cloud region. **Only `cn-southwest-2` (Southwest-Guiyang-1) is supported** by MaaS ShowStatistics; any other value fails with `Error: Unsupported region '<r>'. ...` | `cn-southwest-2` |
| `--service-type` | Optional | 1 = My Service, 2 = Preset Service, 4 = Custom Endpoint. **3 is not supported** (API returns 400) | `2` (Preset Service) |
| `--infer-type` | Optional | `real_time` = online inference, `batch` = batch inference | `real_time` |
| `--api-keys` | Optional | Space-separated API Key list to filter results (`--api-keys key1 key2`); pass `""` for online-experience calls | all keys |
| `--raw` | Optional | Also print the raw segmented API JSON response (debugging); does not change the table | off |
| `--credentials-file` | Optional | Path to a credentials file (alternative to env vars); must be a **readable UTF-8 text file**. Supports `KEY=VALUE`, CSV three-column, and one-value-per-line three-line formats, **including `HW_SECURITY_TOKEN`**; unreadable files (directory/permission/non-UTF-8) fail with `Error: Cannot read credentials file <path>: <msg>` | — |
| `--notify-url` | Optional | Webhook URL: after the query, POST the summary JSON (`region`, `period`, `total_tokens`, `prompt_tokens`, `completion_tokens`, `total_requests`, `total_errors`). **Only HTTPS on trusted Huawei Cloud hosts** (`*.myhuaweicloud.com` / `*.huaweicloud.com`, equal-or-subdomain; IP literals rejected) | — |

> **Natural-language time expressions** ("last 7 days" / "last 14 days" / "last 30 days" / "this month") map to `--last-days 7/14/30` or explicit `--from`/`--to`; the range must match the user's expression exactly ("last 7 days" ≠ "this month").
> **Known boundary**: `--from`/`--to` keep the existing semantics — both ends are local `00:00`, so data after `00:00` on the `--to` date is **not** included, and `--from` == `--to` is a zero-length window. `--last-days` is **not** affected (its `to` is the current instant).
> **Time-range arguments**: `--last-days` and `--from`/`--to` are mutually exclusive — `Error: --last-days cannot be combined with --from / --to.`; providing neither gives `Error: --from and --to are required unless --last-days is used.` (see [Error Handling](#error-handling)).
> **Security note for `--notify-url`**: HTTPS-only with TLS verification (`verify=True`); URLs that fail the host allowlist or are IP literals are rejected during validation with `Error: --notify-url rejected: ...` and no query is sent. See [references/security-guide.md](references/security-guide.md).
> **Note**: No AK/SK parameter is required. Credentials are read from environment variables or a credentials file by the Python script. AK/SK is never exported from the Python process.

---

## Script Tools

| Script | Description |
|--------|-------------|
| [maas_rest_usage_stats.py](scripts/maas_rest_usage_stats.py) | MaaS ShowStatistics API query script (SDK signing + requests, AK/SK never in `ps -ef`). Auto-segments ranges > 29 days, auto-detects OS local timezone, supports `--last-days`, permanent/temporary AK/SK + credentials file, and the optional SSRF-guarded `--notify-url` webhook. See Core Commands above for usage. |

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

The security architecture keeps AK/SK exclusively in Python process memory — never in `ps -ef`, shell variables, environment variables (read-only access), or conversation. Tool separation: **Python SDK signing** for AK/SK authentication, **Python requests** for HTTP POST to the MaaS endpoint. Credentials are never printed, never logged, never exported. Temporary credentials add `HW_SECURITY_TOKEN` as the `X-Security-Token` header via the SDK signer. The optional `--notify-url` webhook is SSRF-guarded: HTTPS only, host must be `myhuaweicloud.com` / `huaweicloud.com` or a subdomain (IP literals rejected), TLS verification stays on, and rejected URLs never reach the network.

📄 Full details (tool separation table, credential leakage risk elimination, credential lifecycle) → [references/security-design.md](references/security-design.md)
📄 Operational security rules, refusal template, credential configuration methods, and `--notify-url` allowlist → [references/security-guide.md](references/security-guide.md)

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
| [security-guide.md](references/security-guide.md) | Operational security rules, refusal template for user-provided AK/SK, credential configuration and credentials-file formats (`HW_SECURITY_TOKEN`) |
| [maas_rest_usage_stats.py](scripts/maas_rest_usage_stats.py) | ShowStatistics API usage statistics script (AK/SK never in ps -ef) |
