# MaaS Monitoring Metrics Reference

Response metrics and enum values for the MaaS ShowStatistics API.

## Table of Contents

- [MaaS ShowStatistics API](#maas-showstatistics-api)
  - [API](#api)
  - [Response Metrics](#response-metrics)
  - [service_type Values](#service_type-values)
  - [infer_type Values](#infer_type-values)
  - [Limitations](#limitations)
- [References](#references)

---

## MaaS ShowStatistics API

### API

`POST /v1/{project_id}/maas/monitoring/show-statistics`

### Response Metrics

| Field | Type | Description | Unit | Conversion |
|-------|------|-------------|------|------------|
| `total_request_count` | Integer | Total request count | count | Use directly |
| `total_error_count` | Integer | Total failed request count | count | Use directly |
| `total_token` | Double | Total tokens (prompt + completion) | thousand | Actual = value × 1000 |
| `total_prompt_token` | Double | Total prompt (input) tokens | thousand | Actual = value × 1000 |
| `total_completion_token` | Double | Total completion (output) tokens | thousand | Actual = value × 1000 |
| `total_completion_tasks` | Integer | Completed batch inference tasks | count | Use directly |
| `total_infer_count` | Integer | Total inference count | count | Use directly |
| `video_generate_duration` | Double | Total video generation duration | second | Use directly |
| `image_generate_nums` | Integer | Number of generated images | count | Use directly |

> **Every numeric field present in the response is printed** in the output table (issue #112 Gap-2). The 5 core metrics (`total_token`, `total_prompt_token`, `total_completion_token`, `total_request_count`, `total_error_count`) and `Error Rate` are always shown (missing core fields count as 0); `total_completion_tasks`, `total_infer_count`, `video_generate_duration`, `image_generate_nums` and any unmapped numeric field appear only when the response contains them. Source: [ShowStatistics API doc](https://support.huaweicloud.com/api-maas/ShowStatistics.html).

### service_type Values

| service_type | Description |
|-------------|-------------|
| 1 | My Service (model service deployed on "My Service" page) |
| 2 | Preset Service (model service enabled on "Preset Service" tab) |
| 4 | Custom Endpoint (endpoint service created on "Custom Endpoint" tab) |

> **⚠️ Note**: API doc says 3=Custom Endpoint, but the actual API only supports [1, 2, 4].

### infer_type Values

| infer_type | Description |
|-----------|-------------|
| `real_time` | Online inference |
| `batch` | Batch inference (restricted use phase) |

### Limitations

- **Region**: only Southwest-Guiyang-1 (`cn-southwest-2`) is supported (official doc: 区域限制 — 仅支持西南-贵阳一区域)
- Only retains 30 days of statistics data
- API rate limit: total requests ≤ 1000/min, per-user ≤ 200/min

---

## References

| Document | Description |
|----------|-------------|
| [related-apis.md](related-apis.md) | API and parameter details |
| [task-query-tokens-usage.md](task-query-tokens-usage.md) | Task 1 detailed steps |
