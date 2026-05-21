# OBS CES监控指标参考 - 华为云OBS对象存储管理

OBS在CES（云监控服务）中上报的监控指标，命名空间为 `SYS.OBS`。

> **参考官方文档：** https://support.huaweicloud.com/usermanual-obs/obs_03_0010.html

## 命名空间

`SYS.OBS`

## 维度

| 维度 | Key | hcloud参数格式 | 描述 |
|------|-----|---------------|------|
| 桶名 | `bucket_name` | `--dim.0=bucket_name,<BucketName>` | OBS桶名称 |

> **⚠️ hcloud CES维度参数格式**
>
> hcloud CES ShowMetricData的维度参数使用 `--dim.N=key,value` 格式：
> ```bash
> --dim.0=bucket_name,my-bucket
> ```
>
> ❌ 错误格式（SDK/REST API格式，hcloud不支持）：
> ```bash
> --dimensions.0.name=bucket_name --dimensions.0.value=my-bucket
> ```

---

## 流量指标

> **⚠️ 关键：带宽指标 vs 流量指标**
>
> - **流量指标**（累计量，单位Bytes）：直接求和即为总字节数，**查询流量时必须使用此类指标**
> - **带宽指标**（速率，单位Bytes/s）：需要乘以聚合周期才能换算为字节数，容易出错，**查询流量时禁止使用**

### 流量指标（累计量，推荐使用）

| 指标名 | 指标ID | 单位 | 描述 |
|--------|--------|------|------|
| 公网下载流量 | `download_traffic_extranet` | Bytes | 公网下载对象大小总和（含CDN回源） |
| 内网下载流量 | `download_traffic_intranet` | Bytes | 内网下载对象大小总和 |
| 总下载流量 | `download_traffic` | Bytes | 下载对象大小总和 |
| 公网上传流量 | `upload_traffic_extranet` | Bytes | 公网上传对象大小总和 |
| 内网上传流量 | `upload_traffic_intranet` | Bytes | 内网上传对象大小总和 |
| 总上传流量 | `upload_traffic` | Bytes | 上传对象大小总和 |
| CDN回源流量 | `cdn_traffic` | Bytes | CDN回源请求流量总和 |

### 带宽指标（速率，避免用于流量统计）

| 指标名 | 指标ID | 单位 | 描述 |
|--------|--------|------|------|
| 总下载带宽 | `download_bytes` | Bytes/s | 平均每秒下载对象大小 |
| 公网下载带宽 | `download_bytes_extranet` | Bytes/s | 平均每秒外网下载对象大小 |
| 内网下载带宽 | `download_bytes_intranet` | Bytes/s | 平均每秒内网下载对象大小 |
| 总上传带宽 | `upload_bytes` | Bytes/s | 平均每秒上传对象大小 |
| 公网上传带宽 | `upload_bytes_extranet` | Bytes/s | 平均每秒公网上传对象大小 |
| 内网上传带宽 | `upload_bytes_intranet` | Bytes/s | 平均每秒内网上传对象大小 |

> **⚠️ 流量计费说明**
>
> - **公网下载流量**（`download_traffic_extranet`）：计费项，公网流出流量按GB计费（含CDN回源）
> - **内网下载流量**（`download_traffic_intranet`）：免费，同区域/同VPC内网传输不收费
> - **公网上传流量**（`upload_traffic_extranet`）：免费，公网流入流量不收费
> - **内网上传流量**（`upload_traffic_intranet`）：免费

---

## 请求指标

| 指标名 | 指标ID | 单位 | 描述 |
|--------|--------|------|------|
| GET类请求次数 | `get_request_count` | Count | GET请求次数（GetObject、HeadObject、ListObjects等） |
| PUT类请求次数 | `put_request_count` | Count | PUT请求次数（PutObject、CopyObject等） |
| POST类请求次数 | `post_request_count` | Count | POST类请求次数 |
| HEAD类请求次数 | `head_request_count` | Count | HEAD类请求次数 |
| DELETE类请求次数 | `delete_request_count` | Count | DELETE类请求次数 |
| 4xx状态码个数 | `request_count_4xx` | Count | 服务端响应4xx的请求数 |
| 5xx状态码个数 | `request_count_5xx` | Count | 服务端响应5xx的请求数 |
| GET类请求首字节平均时延 | `first_byte_latency` | ms | GET请求首字节平均时延 |
| 总TPS | `request_count_per_second` | Count/s | 每秒请求数 |

> **⚠️ 注意：OBS无 `request_count` 指标**
>
> CES中**不存在**名为 `request_count` 的OBS指标。总请求数需通过各类型请求求和获得：
> `总请求数 = get_request_count + put_request_count + post_request_count + head_request_count + delete_request_count`
>
> 或使用TPS指标 `request_count_per_second`（每秒请求数，需乘以聚合周期换算为总次数）。

> **⚠️ 请求计费说明**
>
> - GET/HEAD类请求：按万次计费（价格较低）
> - PUT/POST/DELETE类请求：按万次计费（价格较高，通常为GET的10倍）

---

## 容量指标

| 指标名 | 指标ID | 单位 | 描述 |
|--------|--------|------|------|
| 存储总用量 | `capacity_total` | Bytes | 所有数据占用的存储空间 |
| 标准存储用量 | `capacity_standard` | Bytes | 标准存储数据占用的存储空间 |
| 低频存储用量 | `capacity_infrequent_access` | Bytes | 低频访问存储数据占用的存储空间 |
| 归档存储用量 | `capacity_archive` | Bytes | 归档存储数据占用的存储空间 |
| 深度归档存储用量 | `capacity_deep_archive` | Bytes | 深度归档存储数据占用的存储空间 |

> **⚠️ 容量指标采集说明**
>
> - CES容量指标采集周期为30分钟，非实时值
> - 若需精确的桶容量和对象数，优先使用 `GetBucketStorageInfo` API
> - CES容量指标适用于趋势分析和告警

> **💡 实战经验：使用CES容量指标批量查询桶容量**
>
> 查询多个桶容量排名时，逐桶调用GetBucketStorageInfo效率低，推荐通过CES批量查询：
>
> ```bash
> hcloud CES ShowMetricData \
>   --region=cn-south-1 \
>   --namespace=SYS.OBS \
>   --metric_name=capacity_total \
>   --dim.0=bucket_name,<BucketName> \
>   --period=86400 \
>   --filter=average \
>   --from=<当天0点时间戳ms> \
>   --to=<当前时间戳ms>
> ```
>
> - 使用 `filter=average`（非sum），取最新采样值
> - 返回 `datapoints[-1].average` 即为当前桶容量（Bytes）
> - CES容量指标30分钟采集一次，对排名统计足够准确

---

## 查询示例

### 查询桶的公网下载流量（本月）

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

### 查询桶的内网下载流量（本月）

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

### 查询桶的GET请求数（本月）

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

## 官方文档

- [OBS监控指标说明](https://support.huaweicloud.com/usermanual-obs/obs_03_0010.html)
- [CES ShowMetricData API](https://support.huaweicloud.com/api-ces/ces_03_0059.html)
