# Task 1: Query MaaS Tokens Usage Statistics

Query MaaS usage statistics via the ShowStatistics API. Data is consistent with the Huawei Cloud console.

## Table of Contents

- [API Information](#api-information)
- [Script: maas_rest_usage_stats.py](#script-maas_rest_usage_statspy)
  - [Time Range Parameters (one form is required)](#time-range-parameters-one-form-is-required)
  - [Optional Parameters](#optional-parameters)
  - [Usage Examples](#usage-examples)
- [Time Range Handling](#time-range-handling)
- [service_type Values](#service_type-values)
- [Execution Steps](#execution-steps)
- [Response Fields](#response-fields)
- [Notification Webhook (--notify-url)](#notification-webhook---notify-url)
- [Error Rate Calculation](#error-rate-calculation)
- [References](#references)

---

## API Information

- **API**: `POST /v1/{project_id}/maas/monitoring/show-statistics`
- **Endpoint**: `modelarts.{region}.myhuaweicloud.com` (dynamically assembled)
- **Region limitation**: Only supports Southwest-Guiyang-1 (cn-southwest-2)
- **Auth**: AK/SK signing (SDK-HMAC-SHA256), via huaweicloudsdkcore `Signer`. Supports temporary AK/SK + Security Token (`X-Security-Token` header).
- **API Doc**: https://support.huaweicloud.com/api-maas/ShowStatistics.html
- **Rate limit**: Total requests ≤ 1000/min, per-user ≤ 200/min

> **⚠️ Important: Default region is cn-southwest-2**
> MaaS ShowStatistics API only supports Southwest-Guiyang-1 region (cn-southwest-2).

---

## Script: maas_rest_usage_stats.py

Query via MaaS ShowStatistics API. The script automatically handles:
- AK/SK signing via huaweicloudsdkcore (no manual signing needed)
- Auto-segmentation for whole-day spans longer than 29 days (`(to - from).days > 29`)
- Auto-detection of OS local timezone

### Time Range Parameters (one form is required)

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--from` | Conditionally required | Start date in `YYYY-MM-DD` format (local-timezone 00:00). Required unless `--last-days` is used; **mutually exclusive with `--last-days`** |
| `--to` | Conditionally required | End date in `YYYY-MM-DD` format (local-timezone 00:00). Required unless `--last-days` is used; **mutually exclusive with `--last-days`** |
| `--last-days` | Conditionally required | Integer in **`1 <= N <= 3650`**: the **last N calendar days** — `from` = local `today - (N-1)` at 00:00, `to` = **the current instant** (today's data up to now included; `--last-days 1` = today 00:00 until now). `N > 3650` fails with `Error: --last-days must not exceed 3650 days, got '<v>'.` **Mutually exclusive with `--from`/`--to`** |
| Credentials | Required | Environment variables (`HW_ACCESS_KEY`, `HW_SECRET_KEY`, `HW_SECURITY_TOKEN`) or `--credentials-file` |

### Optional Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--region` | cn-southwest-2 | Huawei Cloud region (**only `cn-southwest-2` is supported**; any other value fails with a friendly error) |
| `--service-type` | 2 | 1=My Service, 2=Preset Service, 4=Custom Endpoint (3 is not supported; API returns 400) |
| `--infer-type` | real_time | real_time=Online inference, batch=Batch inference |
| `--api-keys` | All keys | Filter by API Key list (`--api-keys key1 key2`; `""` for online-experience calls) |
| `--raw` | off | Show raw API response (table output unchanged) |
| `--credentials-file` | - | Credentials file path; must be a **readable UTF-8 text file** in `KEY=VALUE`, CSV three-column, or one-value-per-line three-line format, **including `HW_SECURITY_TOKEN`**. Unreadable files (directory / permission denied / non-UTF-8) fail with `Error: Cannot read credentials file <path>: <msg>`; a missing path gives `Error: Credentials file not found: <path>` |
| `--notify-url` | - | Webhook URL: after the query, POST the summary JSON (`region`, `period`, `total_tokens`, `prompt_tokens`, `completion_tokens`, `total_requests`, `total_errors`). Only HTTPS on trusted Huawei Cloud hosts (`*.myhuaweicloud.com` / `*.huaweicloud.com`; IP literals rejected) |

> Invalid parameters are reported on `stderr` as `Error: ...` with exit code 1 (see [SKILL.md](../SKILL.md) `## Error Handling`).
> **Known boundary:** `--from`/`--to` are both local `00:00` boundaries (`--to` does not include that day after 00:00, and `--from` == `--to` is a zero-length window); `--last-days` ends at the current instant instead.

### Usage Examples

```bash
# Permanent AK/SK (environment variables)
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21

# Rolling window: last 7 calendar days, today included up to the current instant
python3 scripts/maas_rest_usage_stats.py --last-days 7

# Temporary AK/SK + Security Token
export HW_ACCESS_KEY=<your-temp-ak>
export HW_SECRET_KEY=<your-temp-sk>
export HW_SECURITY_TOKEN=<your-security-token>
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21

# Credentials file (supports: one-per-line with token on line 3, CSV with token in column 3, KEY=VALUE)
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --credentials-file /path/to/aksk.txt

# My Service
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 1

# Custom Endpoint
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --service-type 4

# Batch inference
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --infer-type batch

# Filter by API Key
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --api-keys key1 key2

# Show raw API response
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --raw

# Post the summary JSON to a webhook after the query (HTTPS + Huawei Cloud host allowlist only)
python3 scripts/maas_rest_usage_stats.py --last-days 7 --notify-url https://example.myhuaweicloud.com/hook
```

---

## Time Range Handling

> **Key: Time range must match user expression exactly**

| User expression | Time range | Script option |
|----------------|-----------|---------------|
| "last 7 days" | today 00:00 local time back 6 days ~ **the current instant** | `--last-days 7` |
| "last 14 days" | today 00:00 local time back 13 days ~ **the current instant** | `--last-days 14` |
| "last 30 days" / "last month" | today 00:00 local time back 29 days ~ **the current instant** | `--last-days 30` |
| "this month" | 1st of month 00:00:00 ~ today 00:00 | `--from <1st> --to <today>` |
| Specific date range | User-specified start and end (both local 00:00) | `--from ... --to ...` (e.g. "May 1 to May 19") |

> **`--last-days N`** means the **last N calendar days including today up to now**: `from` = local `today - (N-1)` at 00:00, `to` = the current instant, with **`1 <= N <= 3650`** (`MAX_LAST_DAYS`; the bound exists because the script segments at 29 days and MaaS retains only 30 days of data). `--last-days 1` = today 00:00 until now (never a zero-length window).
> **There is no default time range.** You must pass either `--last-days N` (integer `1 <= N <= 3650`) or `--from` + `--to`; the two forms are mutually exclusive.
> With neither form, the script prints `Error: --from and --to are required unless --last-days is used.` on stderr and exits with code 1.
> With both forms, it prints `Error: --last-days cannot be combined with --from / --to.`
> Above the bound it prints `Error: --last-days must not exceed 3650 days, got '<v>'.` (also exit code 1, no traceback).

> **⚠️ Segmentation threshold:** a range is split only when the **whole-day span** exceeds 29 days (`(to - from).days > 29`), so a `--to`/`--from` range of up to 29 days is one request.

> **⚠️ Known boundary of `--from`/`--to`:** both dates are normalised to the local `00:00` boundary, so data after 00:00 on the `--to` date is **not** included, and `--from` == `--to` is a **zero-length window** (which can legitimately return all zeros). `--last-days` does not have this limitation.

> **⚠️ 30-day data retention:** API only retains 30 days of statistics. The script automatically segments queries spanning more than 29 days and aggregates results.

---

## service_type Values

| service_type | Description |
|-------------|-------------|
| 1 | My Service (model service deployed on "My Service" page) |
| 2 | Preset Service (model service enabled on "Preset Service" tab) **[Default]** |
| 4 | Custom Endpoint (endpoint service created on "Custom Endpoint" tab) |

> **⚠️ Note**: API doc says 3=Custom Endpoint, but the actual API only supports [1, 2, 4]. Using 3 returns a 400 error.

---

## Execution Steps

**Step 1: Run the script (permanent AK/SK)**

```bash
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21
```

**Step 1: Run the script (temporary AK/SK + Security Token)**

```bash
export HW_ACCESS_KEY=<your-temp-ak>
export HW_SECRET_KEY=<your-temp-sk>
export HW_SECURITY_TOKEN=<your-security-token>
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21
```

**Step 1: Run the script (last N calendar days)**

```bash
python3 scripts/maas_rest_usage_stats.py --last-days 7
```

**Step 2: View output**

The table **always** shows the 5 core metrics and `Error Rate`. The other numeric fields (`Completed Batch Tasks`, `Total Inference Count`, `Video Duration (s)`, `Generated Images`, plus any unmapped numeric key) are printed **only when the response actually contains them** — the script never fabricates a `0` row for an absent field. Column widths adapt to the longest label/value printed. Example with all 9 official fields present:

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

> The `Period:` timezone label is the OS locale abbreviation (`%Z`): English locales typically print `CST`, while other locales print a localized name (e.g. `中国标准时间` on zh-CN Windows). The examples here use `(CST)`.

When every value is zero, the same table is followed by **two** lines on stdout (not an error — exit code stays `0`):

```
Note: no usage data in this period (all values are zero). Verify the time range, service type, infer type, and API key filter.
Note: if --from equals --to, the query window is a single instant (00:00-00:00); use a wider range or --last-days.
```

---

## Response Fields

The ShowStatistics 200 response contains **9 numeric fields**; every numeric field that the response actually carries is printed (Gap-2). The 5 core fields and `Error Rate` are always shown (missing core fields count as 0); the fields below are shown only when present in the response. Any additional numeric field is also printed, labeled with its raw API key.

| Field | Type | Description | Unit | Conversion | Table row |
|-------|------|-------------|------|------------|-----------|
| `total_token` | Double | Total tokens (prompt + completion) | thousand | Actual = value × 1000 | `Total Tokens` |
| `total_prompt_token` | Double | Total prompt (input) tokens | thousand | Actual = value × 1000 | `Prompt Tokens` |
| `total_completion_token` | Double | Total completion (output) tokens | thousand | Actual = value × 1000 | `Completion Tokens` |
| `total_request_count` | Integer | Total request count | count | Use directly | `Total Requests` |
| `total_error_count` | Integer | Total failed request count | count | Use directly | `Total Errors` |
| `total_completion_tasks` | Integer | Completed batch inference tasks | count | Use directly | `Completed Batch Tasks` |
| `total_infer_count` | Integer | Total inference count | count | Use directly | `Total Inference Count` |
| `video_generate_duration` | Double | Total video generation duration | second | Use directly | `Video Duration (s)` |
| `image_generate_nums` | Integer | Number of generated images | count | Use directly | `Generated Images` |

> **Token unit conversion**: API returns token values in thousands. For example, `total_token: 2482084.98` → actual = 2,482,084,980 tokens ≈ 2,482.08 M tokens.
> **Conditional rows**: `total_completion_tasks`, `total_infer_count`, `video_generate_duration`, `image_generate_nums` are shown only if at least one response segment contains that key.
> **Unmapped fields**: any further numeric field is appended after the rows above, sorted by raw field name; non-numeric keys are ignored. See [related-apis.md](related-apis.md) for the type/unit details.

---

## Notification Webhook (--notify-url)

Optional. After the table and `Period:` line are printed, the script POSTs the query summary as JSON
(`Content-Type: application/json`, timeout 10 s, `verify=True`) to the given URL and prints
`Results sent to webhook: <url>` on stdout.

```json
{
  "region": "cn-southwest-2",
  "period": "2026-05-08 00:00:00 ~ 2026-05-21 00:00:00 (CST)",
  "total_tokens": 2482084.98,
  "prompt_tokens": 2456504.362,
  "completion_tokens": 24872.928,
  "total_requests": 67188,
  "total_errors": 8002
}
```

Token values keep the API's original unit (thousand), exactly as aggregated; they are not converted to M tokens.

**Security constraints (enforced during parameter validation, before any query is sent):**

| Check | Allowed | Rejected |
|-------|---------|----------|
| Scheme | `https` | anything else (incl. `http`) |
| Host type | DNS name | IP literal (IPv4 or IPv6) |
| Domain | `myhuaweicloud.com`, `huaweicloud.com`, or a subdomain of either | any other host |
| TLS | `verify=True` (always) | TLS verification disabled |

A rejected URL fails fast with exit code 1 and nothing is sent:

```
Error: --notify-url rejected: only HTTPS URLs on trusted Huawei Cloud hosts (*.myhuaweicloud.com / *.huaweicloud.com) are allowed; the request was NOT sent.
```

If delivery itself fails (network error, timeout, non-2xx), the query result is still valid:

```
Warning: failed to send --notify-url notification: <message>
```

The exit code remains `0`. See [security-guide.md](security-guide.md) for the full SSRF rationale.

---

## Error Rate Calculation

```
Error rate = Total errors / Total requests × 100%
```

---

## References

| Document | Description |
|----------|-------------|
| [maas_rest_usage_stats.py](../scripts/maas_rest_usage_stats.py) | ShowStatistics API usage statistics script |
| [related-apis.md](related-apis.md) | API and parameter details |
| [maas-metrics.md](maas-metrics.md) | MaaS monitoring metrics reference |
| [troubleshooting.md](troubleshooting.md) | Troubleshooting and practical experience |
