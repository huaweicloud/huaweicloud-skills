# OBS CES Monitoring Metrics Reference - Huawei Cloud OBS Object Storage Statistics

OBS monitoring metrics reported in CES (Cloud Eye Service), with namespace `SYS.OBS`.

> **Official documentation reference:** https://support.huaweicloud.com/usermanual-obs/obs_03_0010.html

## Namespace

`SYS.OBS`

## Dimensions

| Dimension | Key | hcloud Parameter Format | Description |
|-----------|-----|------------------------|-------------|
| Bucket name | `bucket_name` | `--dim.0=bucket_name,<BucketName>` | OBS bucket name |

> **⚠️ hcloud CES dimension parameter format**
>
> hcloud CES ShowMetricData uses `--dim.N=key,value` format for dimension parameters:
> ```bash
> --dim.0=bucket_name,my-bucket
> ```
>
> ❌ Incorrect format (SDK/REST API format, not supported by hcloud):
> ```bash
> --dimensions.0.name=bucket_name --dimensions.0.value=my-bucket
> ```

---

## Traffic Metrics

> **⚠️ Key: Bandwidth metrics vs. Traffic metrics**
>
> - **Traffic metrics** (cumulative, unit: Bytes): can be summed directly for total bytes, **must use these for traffic queries**
> - **Bandwidth metrics** (rate, unit: Bytes/s): must be multiplied by the aggregation period to convert to bytes, error-prone, **prohibited for traffic queries**

### Traffic Metrics (Cumulative, Recommended)

| Metric Name | Metric ID | Unit | Description |
|-------------|-----------|------|-------------|
| Extranet download traffic | `download_traffic_extranet` | Bytes | Total extranet download object size (including CDN origin pull) |
| Intranet download traffic | `download_traffic_intranet` | Bytes | Total intranet download object size |
| Total download traffic | `download_traffic` | Bytes | Total download object size |
| Extranet upload traffic | `upload_traffic_extranet` | Bytes | Total extranet upload object size |
| Intranet upload traffic | `upload_traffic_intranet` | Bytes | Total intranet upload object size |
| Total upload traffic | `upload_traffic` | Bytes | Total upload object size |
| CDN origin pull traffic | `cdn_traffic` | Bytes | Total CDN origin pull request traffic |

### Bandwidth Metrics (Rate, Avoid for Traffic Statistics)

| Metric Name | Metric ID | Unit | Description |
|-------------|-----------|------|-------------|
| Total download bandwidth | `download_bytes` | Bytes/s | Average download object bytes per second |
| Extranet download bandwidth | `download_bytes_extranet` | Bytes/s | Average extranet download bytes per second |
| Intranet download bandwidth | `download_bytes_intranet` | Bytes/s | Average intranet download bytes per second |
| Total upload bandwidth | `upload_bytes` | Bytes/s | Average upload object bytes per second |
| Extranet upload bandwidth | `upload_bytes_extranet` | Bytes/s | Average extranet upload bytes per second |
| Intranet upload bandwidth | `upload_bytes_intranet` | Bytes/s | Average intranet upload bytes per second |

> **⚠️ Traffic billing notes**
>
> - **Extranet download traffic** (`download_traffic_extranet`): billed item, extranet outbound traffic is charged per GB (including CDN origin pull)
> - **Intranet download traffic** (`download_traffic_intranet`): free, same-region/same-VPC intranet transfer is not charged
> - **Extranet upload traffic** (`upload_traffic_extranet`): free, extranet inbound traffic is not charged
> - **Intranet upload traffic** (`upload_traffic_intranet`): free

---

## Request Metrics

| Metric Name | Metric ID | Unit | Description |
|-------------|-----------|------|-------------|
| GET requests | `get_request_count` | Count | GET-type requests (GetObject, HeadObject, ListObjects, etc.) |
| PUT requests | `put_request_count` | Count | PUT-type requests (PutObject, CopyObject, etc.) |
| POST requests | `post_request_count` | Count | POST-type requests |
| HEAD requests | `head_request_count` | Count | HEAD-type requests |
| DELETE requests | `delete_request_count` | Count | DELETE-type requests |
| 4xx status codes | `request_count_4xx` | Count | Requests with 4xx server responses |
| 5xx status codes | `request_count_5xx` | Count | Requests with 5xx server responses |
| GET first byte latency | `first_byte_latency` | ms | GET request average first byte latency |
| Total TPS | `request_count_per_second` | Count/s | Requests per second |

> **⚠️ Note: OBS has no `request_count` metric**
>
> There is **no** OBS metric named `request_count` in CES. Total request count must be calculated by summing all request types:
> `Total requests = get_request_count + put_request_count + post_request_count + head_request_count + delete_request_count`
>
> Alternatively, use the TPS metric `request_count_per_second` (requests per second; requires multiplication by aggregation period for total count).

> **⚠️ Request billing notes**
>
> - GET/HEAD requests: billed per 10,000 requests (lower price)
> - PUT/POST/DELETE requests: billed per 10,000 requests (higher price, typically 10x GET price)

---

## Capacity Metrics

| Metric Name | Metric ID | Unit | Description |
|-------------|-----------|------|-------------|
| Total storage usage | `capacity_total` | Bytes | Total storage occupied by all data |
| Standard storage usage | `capacity_standard` | Bytes | Storage occupied by standard storage data |
| Infrequent access storage | `capacity_infrequent_access` | Bytes | Storage occupied by infrequent access data |
| Archive storage | `capacity_archive` | Bytes | Storage occupied by archive data |
| Deep archive storage | `capacity_deep_archive` | Bytes | Storage occupied by deep archive data |

> **⚠️ Capacity metric collection notes**
>
> - CES capacity metrics are collected every 30 minutes, not real-time
> - For exact bucket capacity and object count, prefer using `GetBucketStorageInfo` API
> - CES capacity metrics are suitable for trend analysis and alerting

> **💡 Best Practice: Batch query bucket capacity via CES capacity metrics**
>
> When ranking multiple buckets by capacity, calling GetBucketStorageInfo per bucket is slow. Use CES batch query instead:
>
> ```bash
> hcloud CES ShowMetricData \
>   --region=cn-south-1 \
>   --namespace=SYS.OBS \
>   --metric_name=capacity_total \
>   --dim.0=bucket_name,<BucketName> \
>   --period=86400 \
>   --filter=average \
>   --from=<TodayMidnightTimestampMs> \
>   --to=<CurrentTimestampMs>
> ```
>
> - Use `filter=average` (not sum), to get the latest sampled value
> - `datapoints[-1].average` is the current bucket capacity (Bytes)
> - CES capacity metrics are collected every 30 minutes, sufficiently accurate for ranking

---

## Query Examples

### Query bucket extranet download traffic (this month)

```bash
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=download_traffic_extranet \
  --dim.0=bucket_name,my-bucket \
  --period=86400 \
  --filter=sum \
  --from=1777564800000 \
  --to=1779181505463
```

### Query bucket intranet download traffic (this month)

```bash
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=download_traffic_intranet \
  --dim.0=bucket_name,my-bucket \
  --period=86400 \
  --filter=sum \
  --from=1777564800000 \
  --to=1779181505463
```

### Query bucket GET request count (this month)

```bash
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=get_request_count \
  --dim.0=bucket_name,my-bucket \
  --period=86400 \
  --filter=sum \
  --from=1777564800000 \
  --to=1779181505463
```

---

## References

- [OBS Monitoring Metrics](https://support.huaweicloud.com/usermanual-obs/obs_03_0010.html)
- [CES ShowMetricData API](https://support.huaweicloud.com/api-ces/ces_03_0059.html)
