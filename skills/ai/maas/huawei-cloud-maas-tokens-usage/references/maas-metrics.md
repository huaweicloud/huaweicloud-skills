# MaaS Monitoring Metrics Reference

## MaaS ShowStatistics API

### API

`POST /v1/{project_id}/maas/monitoring/show-statistics`

### Response Metrics

| Field | Type | Description | Unit | Conversion |
|-------|------|-------------|------|------------|
| `total_request_count` | Integer | Total request count | count | Use directly |
| `total_error_count` | Integer | Total error count | count | Use directly |
| `total_token` | Double | Total tokens (prompt + completion) | thousand | Actual = value × 1000 |
| `total_prompt_token` | Double | Total prompt tokens | thousand | Actual = value × 1000 |
| `total_completion_token` | Double | Total completion tokens | thousand | Actual = value × 1000 |
| `total_completion_tasks` | Integer | Completed batch inference tasks | count | Batch inference only |
| `total_infer_count` | Integer | Total inference count | count | Batch inference only |

### service_type Values

| service_type | Description |
|-------------|-------------|
| 1 | My Service (model service deployed on "My Service" page) |
| 2 | Preset Service (model service enabled on "Preset Service" tab) |
| 4 | Custom Endpoint (endpoint service created on "Custom Endpoint" tab) |

> **Note**: API doc says 3=Custom Endpoint, but the actual API only supports [1, 2, 4].

### infer_type Values

| infer_type | Description |
|-----------|-------------|
| `real_time` | Online inference |
| `batch` | Batch inference (restricted use phase) |

### Limitations

- Only retains 30 days of statistics data
- API rate limit: total requests ≤ 1000/min, per-user ≤ 200/min

## References

| Document | Description |
|----------|-------------|
| [related-apis.md](related-apis.md) | API and parameter details |