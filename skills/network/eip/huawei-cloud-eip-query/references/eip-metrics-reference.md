# EIP CES Metrics Reference

EIP bandwidth monitoring data comes from Cloud Eye (CES) under namespace **SYS.VPC**.

## Namespace and Dimensions

- **Namespace**: `SYS.VPC`
- **Dimensions**:
  - `publicip_id` — for EIP-dedicated bandwidth (``bandwidth_share_type=PER``)
  - `bandwidth_id` — for EIPs that use a **shared bandwidth** (``bandwidth_share_type=WHOLE``)

Check the EIP's `bandwidth_share_type` via `hcloud EIP ShowPublicip/v2`, then dimension
the metric query accordingly. Using the wrong dimension returns no datapoints.

## Metric List

| Metric Name | Description | Unit | Typical Filter |
| ------------- | ------------- | ------ | ---------------- |
| `upstream_bandwidth` | Outbound bandwidth | bit/s | average / max |
| `downstream_bandwidth` | Inbound bandwidth | bit/s | average / max |
| `upstream_bandwidth_usage` | Outbound bandwidth usage rate | % | average / max |
| `downstream_bandwidth_usage` | Inbound bandwidth usage rate | % | average / max |
| `up_stream` | Outbound traffic | Byte | sum |
| `down_stream` | Inbound traffic | Byte | sum |

## filter Values (aggregation methods)

| Value | Meaning | Use Case |
| ------- | --------- | ---------- |
| `average` | Mean | Average bandwidth / usage rate |
| `max` | Maximum | Peak bandwidth / utilization |
| `min` | Minimum | Lowest bandwidth |
| `sum` | Sum | Total traffic volume (Byte) |
| `variance` | Variance | Dispersion analysis |

## period Values (aggregation granularity)

`1`, `60`, `300`, `1200`, `3600`, `14400`, `86400` seconds.

Rule of thumb: use `300` for the last 24 hours, `3600` for up to 7 days, `14400`/`86400`
for longer ranges to stay within the API's maximum point count.

## Time Range

- `--from` / `--to` are Unix timestamps in **milliseconds**.
- Set `--from` at least one aggregation period earlier than `now`, otherwise Cloud Eye
  may return empty results because data is aggregated to the period start.
- Example last-24h range: `--from=$(date -d '-24 hours' +%s)000 --to=$(date +%s)000`

## Verify Available Metrics

```bash
hcloud CES ListMetrics --cli-region=cn-north-4 --namespace=SYS.VPC
```

Sample response for one EIP:

```json
{
  "namespace": "SYS.VPC",
  "metric_name": "upstream_bandwidth_usage",
  "unit": "%",
  "dimensions": [{"name": "publicip_id", "value": "0521f035-..."}]
}
```
