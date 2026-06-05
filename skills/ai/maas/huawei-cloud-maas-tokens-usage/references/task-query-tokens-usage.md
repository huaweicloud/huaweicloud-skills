# Task 1: Query MaaS Tokens Usage Statistics

Query MaaS usage statistics via the ShowStatistics API. Data is consistent with the Huawei Cloud console.

## API Information

- **API**: `POST /v1/{project_id}/maas/monitoring/show-statistics`
- **Endpoint**: `modelarts.{region}.myhuaweicloud.com` (dynamically assembled)
- **Region limitation**: Only supports Southwest-Guiyang-1 (cn-southwest-2)
- **Auth**: AK/SK signing (SDK-HMAC-SHA256), via huaweicloudsdkcore `Signer`
- **API Doc**: https://support.huaweicloud.com/api-maas/ShowStatistics.html
- **Rate limit**: Total requests ≤ 1000/min, per-user ≤ 200/min

> **Important: Default region is cn-southwest-2**
> MaaS ShowStatistics API only supports Southwest-Guiyang-1 region (cn-southwest-2).

---

## Script: maas_rest_usage_stats.py

Query via MaaS ShowStatistics API. The script automatically handles:
- AK/SK signing via huaweicloudsdkcore (no manual signing needed)
- Auto-segmentation for time ranges exceeding 30 days
- Auto-detection of OS local timezone

### Required Parameters

| Parameter | Description |
|-----------|-------------|
| `--from` | Start date in YYYY-MM-DD format |
| `--to` | End date in YYYY-MM-DD format |
| Credentials | Environment variables (`HW_ACCESS_KEY`, `HW_SECRET_KEY`) or `--credentials-file` |

### Optional Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--region` | cn-southwest-2 | Huawei Cloud region |
| `--service-type` | 2 | 1=My Service, 2=Preset Service, 4=Custom Endpoint |
| `--infer-type` | real_time | real_time=Online inference, batch=Batch inference |
| `--api-keys` | All keys | Filter by API Key list |
| `--raw` | off | Show raw API response |
| `--credentials-file` | - | Credentials file path |

### Usage Examples

```bash
# Environment variables
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21

# Credentials file (supports: one-per-line, comma-separated, KEY=VALUE)
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
```

---

## Time Range Handling

> **Key: Time range must match user expression exactly**

| User expression | Time range | Description |
|----------------|-----------|-------------|
| "last 7 days" | now-7d ~ now | Rolling 7-day window |
| "last 14 days" | now-14d ~ now | Rolling 14-day window |
| "last 30 days" / "last month" | now-30d ~ now | Rolling 30-day window |
| "this month" | 1st of month 00:00:00 ~ now | Calendar month |
| Specific date range | User-specified start and end | e.g. "May 1 to May 19" |

> **Default time range:** If not specified, default to last 7 days.

> **30-day data retention:** API only retains 30 days of statistics. The script automatically segments queries exceeding 30 days and aggregates results.

---

## service_type Values

| service_type | Description |
|-------------|-------------|
| 1 | My Service (model service deployed on "My Service" page) |
| 2 | Preset Service (model service enabled on "Preset Service" tab) **[Default]** |
| 4 | Custom Endpoint (endpoint service created on "Custom Endpoint" tab) |

> **Note**: API doc says 3=Custom Endpoint, but the actual API only supports [1, 2, 4]. Using 3 returns a 400 error.

---

## Execution Steps

**Step 1: Run the script**

```bash
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21
```

**Step 2: View output**

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

## Response Fields

| Field | Type | Description | Unit | Conversion |
|-------|------|-------------|------|------------|
| `total_request_count` | Integer | Total request count | count | Use directly |
| `total_error_count` | Integer | Total error count | count | Use directly |
| `total_token` | Double | Total tokens (prompt + completion) | thousand | Actual = value × 1000 |
| `total_prompt_token` | Double | Total prompt tokens | thousand | Actual = value × 1000 |
| `total_completion_token` | Double | Total completion tokens | thousand | Actual = value × 1000 |

> **Token unit conversion**: API returns values in thousands. For example, `total_token: 2482084.98` → actual = 2,482,084,980 tokens ≈ 2,482.08 M tokens.

---

## Error Rate Calculation

```
Error rate = Total errors / Total requests × 100%
```

---

## References

| Document | Description |
|----------|-------------|
| [maas_rest_usage_stats.py](scripts/maas_rest_usage_stats.py) | ShowStatistics API usage statistics script |
| [related-apis.md](related-apis.md) | API and parameter details |
| [maas-metrics.md](maas-metrics.md) | MaaS monitoring metrics reference |
| [troubleshooting.md](troubleshooting.md) | Troubleshooting and practical experience |
