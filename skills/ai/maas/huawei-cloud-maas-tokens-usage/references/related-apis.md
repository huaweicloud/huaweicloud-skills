# Related APIs

MaaS ShowStatistics API reference for the tokens usage query workflow.

## Table of Contents

- [MaaS ShowStatistics API](#maas-showstatistics-api)
  - [API Information](#api-information)
  - [Request Parameters](#request-parameters)
  - [Response Parameters](#response-parameters)
  - [Request Example](#request-example)
  - [Response Example](#response-example)
  - [Python Script Invocation](#python-script-invocation)
- [References](#references)

---

## MaaS ShowStatistics API

### API Information

- **API**: `POST /v1/{project_id}/maas/monitoring/show-statistics`
- **Endpoint**: `modelarts.{region}.myhuaweicloud.com` (dynamically assembled)
- **Auth**: AK/SK signing (SDK-HMAC-SHA256). Supports temporary AK/SK + Security Token via `X-Security-Token` header.
- **API doc**: https://support.huaweicloud.com/api-maas/ShowStatistics.html
- **Region limitation**: only Southwest-Guiyang-1 (`cn-southwest-2`) is supported (official doc: 区域限制 — 仅支持西南-贵阳一区域); the script enforces this as a region whitelist.
- **Rate limit**: Total requests ≤ 1000/min, per-user ≤ 200/min

### Request Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `service_type` | Yes | Integer | 1=My Service, 2=Preset Service, 4=Custom Endpoint |
| `start_time` | Yes | Long | Start time, millisecond timestamp |
| `end_time` | Yes | Long | End time, millisecond timestamp (≤ 30 days from start_time; the script segments requests spanning > 29 days to stay inside this limit) |
| `infer_type` | Yes | String | "real_time"=online inference, "batch"=batch inference |
| `timezone` | No | String | Timezone: the OS local timezone, mapped to an IANA name when known (`CST` → `Asia/Shanghai`); otherwise the OS abbreviation/localized name is sent (e.g. `中国标准时间` on zh-CN Windows) |
| `api_keys` | No | Array of strings | Filter by API Key list, pass empty string "" for online experience calls |
| `ips` | No | Array of strings | Filter by IP address |

### Response Parameters

The ShowStatistics 200 response carries **9 fields** (source: [official API doc](https://support.huaweicloud.com/api-maas/ShowStatistics.html), 2026-11-02 revision). The script prints **every numeric field** — no field is dropped (Gap-2):

| Parameter | Type | Description | Unit | Table row label |
|-----------|------|-------------|------|-----------------|
| `total_request_count` | Integer | Total request count (总调用次数) | count | `Total Requests` |
| `total_error_count` | Integer | Total failed request count (总调用失败次数) | count | `Total Errors` |
| `total_token` | Double | Total tokens, prompt + completion (总调用 Tokens 数) | thousand | `Total Tokens` |
| `total_prompt_token` | Double | Total input (prompt) tokens (输入总 Tokens 数) | thousand | `Prompt Tokens` |
| `total_completion_token` | Double | Total output (completion) tokens (输出总 Tokens 数) | thousand | `Completion Tokens` |
| `total_completion_tasks` | Integer | Completed batch inference tasks (已完成批量推理任务数量) | count | `Completed Batch Tasks` |
| `total_infer_count` | Integer | Total inference count (推理总量) | count | `Total Inference Count` |
| `video_generate_duration` | Double | Total video generation duration (生成视频总时长) | second | `Video Duration (s)` |
| `image_generate_nums` | Integer | Number of generated images (生成图片总张数) | count | `Generated Images` |

> **Core fields are always shown**: `total_token`, `total_prompt_token`, `total_completion_token`,
> `total_request_count`, `total_error_count` (missing ones count as 0) plus the computed `Error Rate`.
> The remaining fields above are printed **only when the response actually contains them** — the script never
> fabricates a `0` row. Any further numeric field in the response is still printed, as an extra row labeled with
> its raw API key, after the rows above (ascending field-name order); non-numeric keys (strings/objects) are ignored.
> Token fields are rendered with `fmt_tokens()` (thousand → M/K tokens); count fields use a thousands separator.

### Request Example

```json
{
  "service_type": 2,
  "start_time": 1778169600000,
  "end_time": 1779292800000,
  "timezone": "Asia/Shanghai",
  "infer_type": "real_time"
}
```

### Response Example

```json
{
  "total_request_count": 67188,
  "total_error_count": 8002,
  "total_token": 2482084.98,
  "total_prompt_token": 2456504.362,
  "total_completion_token": 24872.928,
  "total_completion_tasks": 0,
  "total_infer_count": 0,
  "video_generate_duration": 0.0,
  "image_generate_nums": 0
}
```

### Python Script Invocation

```bash
# Explicit date range, permanent AK/SK
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

# Temporary AK/SK + Security Token from a credentials file (third line/column)
python3 scripts/maas_rest_usage_stats.py --last-days 7 --credentials-file ./creds.txt

# Post the summary JSON to a webhook after the query (HTTPS + Huawei Cloud host allowlist only)
python3 scripts/maas_rest_usage_stats.py --last-days 7 --notify-url https://example.myhuaweicloud.com/hook
```

---

## References

| Document | Description |
|----------|-------------|
| [MaaS ShowStatistics API](https://support.huaweicloud.com/api-maas/ShowStatistics.html) | Official API documentation |
| [task-query-tokens-usage.md](task-query-tokens-usage.md) | Task 1 detailed steps |
| [maas-metrics.md](maas-metrics.md) | MaaS monitoring metrics reference |
