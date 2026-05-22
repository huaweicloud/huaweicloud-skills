# OBS CES Monitoring Metrics Reference - Huawei Cloud OBS Object Storage Management

Monitoring metrics reported by OBS to CES (Cloud Eye Service), with namespace `SYS.OBS`.

> **Reference official documentation:** https://support.huaweicloud.com/usermanual-obs/obs_03_0010.html

## Namespace

`SYS.OBS`

## Dimensions

| Dimension | Key | hcloud parameter format | Description |
|-----------|-----|------------------------|-------------|
| Bucket name | `bucket_name` | `--dim.0=bucket_name,<BucketName>` | OBS bucket name |

> **⚠️ hcloud CES dimension parameter format**
>
> hcloud CES ShowMetricData dimension parameters use the `--dim.N=key,value` format:
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

> **⚠️ Key: Bandwidth metrics vs Traffic metrics**
>
> - **Traffic metrics** (cumulative, unit Bytes): Direct summation gives total bytes; **must use these metrics when querying traffic**
> - **Bandwidth metrics** (rate, unit Bytes/s): Need to multiply by aggregation period to convert to bytes; error-prone; **do not use for traffic queries**

### Traffic Metrics (Cumulative, Recommended)

| Metric Name | Metric ID | Unit | Description |
|-------------|-----------|------|-------------|
| External download traffic | `download_traffic_extranet` | Bytes | Sum of externally downloaded object sizes (includes CDN origin pull) |
| Internal download traffic | `download_traffic_intranet` | Bytes | Sum of internally downloaded object sizes |
| Total download traffic | `download_traffic` | Bytes | Sum of downloaded object sizes |
| External upload traffic | `upload_traffic_extranet` | Bytes | Sum of externally uploaded object sizes |
| Internal upload traffic | `upload_traffic_intranet` | Bytes | Sum of internally uploaded object sizes |
| Total upload traffic | `upload_traffic` | Bytes | Sum of uploaded object sizes |
| CDN origin pull traffic | `cdn_traffic` | Bytes | Sum of CDN origin pull request traffic |

### Bandwidth Metrics (Rate, Avoid for Traffic Statistics)

| Metric Name | Metric ID | Unit | Description |
|-------------|-----------|------|-------------|
| Total download bandwidth | `download_bytes` | Bytes/s | Average downloaded object size per second |
| External download bandwidth | `download_bytes_extranet` | Bytes/s | Average externally downloaded object size per second |
| Internal download bandwidth | `download_bytes_intranet` | Bytes/s | Average internally downloaded object size per second |
| Total upload bandwidth | `upload_bytes` | Bytes/s | Average uploaded object size per second |
| External upload bandwidth | `upload_bytes_extranet` | Bytes/s | Average externally uploaded object size per second |
| Internal upload bandwidth | `upload_bytes_intranet` | Bytes/s | Average internally uploaded object size per second |

> **⚠️ Traffic billing notes**
>
> - **External download traffic** (`download_traffic_extranet`): Billable item; external outgoing traffic billed per GB (includes CDN origin pull)
> - **Internal download traffic** (`download_traffic_intranet`): Free; intra-region/intra-VPC internal transfer is not charged
> - **External upload traffic** (`upload_traffic_extranet`): Free; external incoming traffic is not charged
> - **Internal upload traffic** (`upload_traffic_intranet`): Free

---

## Request Metrics

| Metric Name | Metric ID | Unit | Description |
|-------------|-----------|------|-------------|
| GET-type request count | `get_request_count` | Count | GET request count (GetObject, HeadObject, ListObjects, etc.) |
| PUT-type request count | `put_request_count` | Count | PUT request count (PutObject, CopyObject, etc.) |
| POST-type request count | `post_request_count` | Count | POST-type request count |
| HEAD-type request count | `head_request_count` | Count | HEAD-type request count |
| DELETE-type request count | `delete_request_count` | Count | DELETE-type request count |
| 4xx status code count | `request_count_4xx` | Count | Server responded 4xx request count |
| 5xx status code count | `request_count_5xx` | Count | Server responded 5xx request count |
| GET-type first byte average latency | `first_byte_latency` | ms | GET request first byte average latency |
| Total TPS | `request_count_per_second` | Count/s | Requests per second |

> **⚠️ Note: OBS has no `request_count` metric**
>
> CES **does not have** an OBS metric named `request_count`. Total request count must be obtained by summing all request types:
> `Total requests = get_request_count + put_request_count + post_request_count + head_request_count + delete_request_count`
>
> Or use the TPS metric `request_count_per_second` (requests per second; multiply by aggregation period to convert to total count).

> **⚠️ Request billing notes**
>
> - GET/HEAD-type requests: Billed per 10,000 requests (lower price)
> - PUT/POST/DELETE-type requests: Billed per 10,000 requests (higher price, typically 10x GET)

---

## Capacity Metrics

| Metric Name | Metric ID | Unit | Description |
|-------------|-----------|------|-------------|
| Total storage usage | `capacity_total` | Bytes | Storage space occupied by all data |
| Standard storage usage | `capacity_standard` | Bytes | Storage space occupied by standard storage data |
| Infrequent access storage usage | `capacity_infrequent_access` | Bytes | Storage space occupied by infrequent access storage data |
| Archive storage usage | `capacity_archive` | Bytes | Storage space occupied by archive storage data |
| Deep archive storage usage | `capacity_deep_archive` | Bytes | Storage space occupied by deep archive storage data |

> **⚠️ Capacity metric collection notes**
>
> - CES capacity metrics have a 30-minute collection cycle; values are not real-time
> - For exact bucket capacity and object count, prefer the `GetBucketStorageInfo` API
> - CES capacity metrics are suitable for trend analysis and alerting

> **💡 Practical tip: Use CES capacity metrics for batch bucket capacity queries**
>
> When querying capacity rankings for multiple buckets, calling GetBucketStorageInfo per bucket is inefficient; recommended to batch query via CES:
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
> - Use `filter=average` (not sum), taking the latest sample value
> - The returned `datapoints[-1].average` is the current bucket capacity (Bytes)
> - CES capacity metrics are collected every 30 minutes, which is accurate enough for ranking statistics

---

## Query Examples

### Query bucket's external download traffic (this month)

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

### Query bucket's internal download traffic (this month)

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

### Query bucket's GET request count (this month)

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

## Official Documentation

- [OBS Monitoring Metrics Description](https://support.huaweicloud.com/usermanual-obs/obs_03_0010.html)
- [CES ShowMetricData API](https://support.huaweicloud.com/api-ces/ces_03_0059.html)
