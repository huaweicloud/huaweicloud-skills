# Related APIs

## MaaS ShowStatistics API

### API Information

- **API**: `POST /v1/{project_id}/maas/monitoring/show-statistics`
- **Endpoint**: `modelarts.{region}.myhuaweicloud.com` (dynamically assembled)
- **Auth**: AK/SK signing (SDK-HMAC-SHA256)
- **API Doc**: https://support.huaweicloud.com/api-maas/ShowStatistics.html
- **Rate limit**: Total requests ≤ 1000/min, per-user ≤ 200/min

### Request Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `service_type` | Yes | Integer | 1=My Service, 2=Preset Service, 4=Custom Endpoint |
| `start_time` | Yes | Long | Start time, millisecond timestamp |
| `end_time` | Yes | Long | End time, millisecond timestamp (≤ 30 days from start_time) |
| `infer_type` | Yes | String | "real_time"=online inference, "batch"=batch inference |
| `timezone` | No | String | IANA format, defaults to OS local timezone |
| `api_keys` | No | Array of strings | Filter by API Key list, pass empty string "" for online experience calls |
| `ips` | No | Array of strings | Filter by IP address |

### Response Parameters

| Parameter | Type | Description | Unit |
|-----------|------|-------------|------|
| `total_request_count` | Integer | Total request count | count |
| `total_error_count` | Integer | Total error count | count |
| `total_token` | Double | Total tokens | thousand |
| `total_prompt_token` | Double | Total prompt tokens | thousand |
| `total_completion_token` | Double | Total completion tokens | thousand |
| `total_completion_tasks` | Integer | Completed batch inference tasks | count |
| `total_infer_count` | Integer | Total inference count | count |

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
  "total_infer_count": 0
}
```

### Python Script Invocation

```bash
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21
```

## References

| Document | Description |
|----------|-------------|
| [MaaS ShowStatistics API](https://support.huaweicloud.com/api-maas/ShowStatistics.html) | Official API documentation |