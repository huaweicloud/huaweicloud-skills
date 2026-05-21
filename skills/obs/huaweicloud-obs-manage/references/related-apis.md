# 相关API - 华为云OBS对象存储管理

本文档列出OBS对象存储管理技能中使用的所有CLI命令和API。

## 目录

- [API概览](#api概览)
- [API详情](#api详情)
  - [1. ListBucketsWithStats - 列出桶名及其容量和对象数](#1-listbucketswithstats---列出桶名及其容量和对象数)
  - [2. UploadFile - 上传本地文件或目录到目标桶](#2-uploadfile---上传本地文件或目录到目标桶)
  - [3. ScheduledUpload - 定时上传本地目录到目标桶](#3-scheduledupload---定时上传本地目录到目标桶)
  - [4. GetMonthlyTraffic - 查询本月外网内网下载流量](#4-getmonthlytraffic---查询本月外网内网下载流量)
  - [5. GetMonthlyRequests - 查询本月请求总数](#5-getmonthlyrequests---查询本月请求总数)
- [月环比计算](#月环比计算)
- [官方文档](#官方文档)

---

## API概览

| 产品 | CLI命令 | API操作 | 描述 |
|------|---------|---------|------|
| OBS | `hcloud obs ls` | ListAllMyBucketsType | 列出所有桶（obsutil方式，hcloud OBS模块无此命令） |
| OBS | `hcloud OBS GetBucketStorageInfo` | GetBucketStorageInfo | 获取桶存储信息（容量、对象数，可能不被hcloud支持） |
| CES | `hcloud CES ShowMetricData` | ShowMetricData | 查询监控指标数据（流量、请求数、容量） |
| OBS | `obsutil cp` | PutObject / UploadPart | 上传文件/目录 |

---

## API详情

### 1. ListBucketsWithStats - 列出桶名及其容量和对象数

> **⚠️ 关键：region参数必须由用户提供**
>
> `--region` 参数**必须由用户显式提供**。Agent **禁止猜测或使用默认值**。
>
> **前置检查步骤：**
> 1. 检查用户是否提供了 `--region` 参数
> 2. 若区域缺失，**立即要求用户提供**：
>    ```
>    请提供OBS所在区域，例如：cn-north-1, cn-north-4, cn-east-2, cn-east-3, cn-south-1 等
>    ```
> 3. 若区域明显无效（如空字符串、纯数字、包含特殊字符），**提示用户**

**步骤 1：列出所有桶**

> **⚠️ 关键：hcloud OBS模块无ListAllMyBucketsType命令**
>
> hcloud CLI（v7.2.2实测）**不存在** `ListAllMyBucketsType` 命令，必须使用obsutil方式：

```bash
# 列出所有桶
hcloud obs ls

# 筛选指定地域
hcloud obs ls 2>&1 | grep "cn-south-1"

# 提取桶名
hcloud obs ls 2>&1 | awk '/obs:\/\// && /cn-south-1/ {print $1}' | sed 's|obs://||'
```

**响应关键字段：**

| 字段 | 描述 |
|------|------|
| `Buckets.Bucket[].Name` | 桶名称 |
| `Buckets.Bucket[].Location` | 桶所在区域 |
| `Buckets.Bucket[].CreationDate` | 桶创建时间 |

**步骤 2：获取每个桶的容量和对象数**

> **⚠️ 关键：推荐使用CES容量指标批量查询，效率更高**
>
> 逐桶调用GetBucketStorageInfo效率低，推荐通过CES `capacity_total` 指标批量查询：
> ```bash
> hcloud CES ShowMetricData \
>   --region=<RegionId> \
>   --namespace=SYS.OBS \
>   --metric_name=capacity_total \
>   --dim.0=bucket_name,<BucketName> \
>   --period=86400 \
>   --filter=average \
>   --from=<当天0点时间戳ms> \
>   --to=<当前时间戳ms>
> ```
> 返回 `datapoints[-1].average` 即为桶容量（Bytes）。

```bash
hcloud OBS GetBucketStorageInfo \
  --region=<RegionId> \
  --bucket=<BucketName>
```

**GetBucketStorageInfo 响应关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `size` | long | 桶中对象总大小（字节） |
| `objectNumber` | int | 桶中对象总数 |

> **⚠️ 注意：hcloud OBS模块可能无GetBucketStorageInfo命令**
>
> 若hcloud不支持 `GetBucketStorageInfo`，替代方案：
> - 通过obsutil查询桶信息：`obsutil ls -bucket=<BucketName> -limit=0 -s`
> - 通过OBS API直接调用：`GET /?storageInfo` 获取桶存储信息
>
> 若obsutil也不支持该查询，可通过列出桶内所有对象并累加大小来获取（性能较差，仅作兜底方案）。

**错误处理：**
1. 若提示"Access Denied"，提示用户检查IAM权限或桶策略
2. 若桶数量为0，提示用户当前区域无桶，可能需要切换区域
3. 若GetBucketStorageInfo报错，跳过该桶并在输出中标注"获取失败"

---

### 2. UploadFile - 上传本地文件或目录到目标桶

> **⚠️ 关键：上传使用obsutil，非hcloud**
>
> hcloud CLI不支持OBS对象上传操作，必须使用obsutil。

> **前置检查：**
> 1. 检查obsutil是否安装：`obsutil version`
> 2. 检查obsutil是否已配置凭证：`obsutil ls -limit=1`
> 3. 检查本地路径是否存在

**必需参数：**

| 参数 | 描述 | 示例 |
|------|------|------|
| 本地路径 | 上传的文件或目录路径 | `/home/user/data/report.csv` |
| 目标桶名 | OBS桶名称 | `my-bucket` |
| 目标对象键（可选） | 桶内对象路径 | `reports/report.csv` |

**CLI命令：**

```bash
# 上传单个文件
obsutil cp <LocalFilePath> obs://<BucketName>/<ObjectKey> -flat

# 上传整个目录（递归）
obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -flat

# 上传并指定并发数（大文件/大量文件）
obsutil cp <LocalPath> obs://<BucketName>/<Prefix> -r -flat -p=10
```

**可选参数：**

| 参数 | 默认值 | 描述 |
|------|--------|------|
| `-flat` | - | 不保留本地目录结构 |
| `-r` | - | 递归上传目录 |
| `-p` | 5 | 并发数 |
| `-threshold` | 50MB | 分片上传阈值 |
| `-fr` | 续传 | 断点续传模式 |
| `-v` | 关闭 | 详细日志模式 |
| `-config` | 默认配置 | 指定obsutil配置文件 |

> **⚠️ 上传大文件注意事项**
>
> - 单个对象最大支持48.8TB
> - 大文件自动使用分片上传，默认分片大小9MB
> - 网络不稳定时建议降低并发数（`-p=3`）
> - 上传中断后支持断点续传（默认启用）

**错误处理：**
1. `bucket not exist`：确认桶名正确，桶名全局唯一需精确匹配
2. `access denied`：检查obsutil凭证配置和桶ACL/策略
3. `no such file or directory`：确认本地路径正确
4. `network timeout`：降低并发数或增加超时时间

---

### 3. ScheduledUpload - 定时上传本地目录到目标桶

> **基于操作系统定时任务（crontab）实现，无需额外守护进程**

**必需参数：**

| 参数 | 描述 | 示例 |
|------|------|------|
| 本地目录路径 | 需定时上传的目录 | `/home/user/data/` |
| 目标桶名 | OBS桶名称 | `my-bucket` |
| 目标路径前缀（可选） | 桶内路径前缀 | `backup/` |
| 定时周期 | 执行周期 | `每小时`、`每天8:00`、`*/30 * * * *` |

**实现步骤：**

**步骤 1：创建上传脚本**

```bash
#!/bin/bash
# OBS定时上传脚本
LOG_FILE="$HOME/obs-scheduled-upload-<BucketName>.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始定时上传" >> "$LOG_FILE"
obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -flat >> "$LOG_FILE" 2>&1
RESULT=$?
if [ $RESULT -eq 0 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 上传成功" >> "$LOG_FILE"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 上传失败，退出码: $RESULT" >> "$LOG_FILE"
fi
```

**步骤 2：设置crontab**

| 周期描述 | crontab表达式 |
|---------|--------------|
| 每30分钟 | `*/30 * * * *` |
| 每小时 | `0 * * * *` |
| 每天8:00 | `0 8 * * *` |
| 每周一0:00 | `0 0 * * 1` |
| 每月1日0:00 | `0 0 1 * *` |

```bash
# 添加crontab任务
(crontab -l 2>/dev/null; echo "<CronExpr> /bin/bash $HOME/obs-scheduled-upload-<BucketName>.sh") | crontab -
```

**步骤 3：验证**

```bash
crontab -l
```

> **⚠️ crontab环境注意事项**
>
> - crontab的PATH环境变量最小，需在脚本中使用obsutil完整路径
> - 建议在脚本开头添加：`export PATH=/usr/local/bin:$PATH`
> - obsutil的AK/SK配置文件路径需确认在crontab环境中可访问

**管理定时任务：**

```bash
# 列出所有定时任务
crontab -l

# 删除特定定时任务
crontab -l | grep -v "obs-scheduled-upload-<BucketName>" | crontab -

# 查看上传日志
tail -f $HOME/obs-scheduled-upload-<BucketName>.log
```

---

### 4. GetMonthlyTraffic - 查询本月外网内网下载流量

> **⚠️ 关键：流量数据通过CES获取，非OBS直接API**
>
> OBS服务本身不提供流量统计API，流量数据由CES（云监控服务）采集。

**必需参数：**

| 参数 | hcloud参数名 | 描述 | 示例 |
|------|-------------|------|------|
| 区域 | `--region` | 桶所在区域 | `cn-south-1` |
| 桶名 | `--dim.0` | 维度 `bucket_name,<BucketName>` | `bucket_name,my-bucket` |

**时间范围计算：**

> **⚠️ 关键：时间范围必须精确匹配用户表述**
>
> | 用户表述 | 时间范围 | 说明 |
> |---------|---------|------|
> | "本月" | 当月1日 00:00:00 ~ 当前时间 | 自然月 |
> | "最近一个月" / "最近30天" | 当前时间-30天 ~ 当前时间 | 滚动30天窗口 |
> | "上月" | 上月1日 00:00:00 ~ 上月最后一天 23:59:59 | 上个自然月 |
> | 具体日期范围 | 用户指定的起止时间 | 如"5月1日到5月19日" |
>
> **"本月" ≠ "最近一个月"**：本月从当月1日算起，最近一个月从当前时间往前推30天。
> 华为云OBS控制台默认统计"最近30天"。

**月环比对照期计算：**

| 查询周期 | 对照期 |
|---------|--------|
| 本月（自然月） | 上月（上个自然月） |
| 最近30天 | 再往前推30天（前30~60天） |
| 具体日期范围 | 前一个等长周期 |

```
# 本月
起始：当月1日 00:00:00 → Unix时间戳(ms)
截止：当前时间 → Unix时间戳(ms)

# 最近30天
起始：当前时间 - 30天 → Unix时间戳(ms)
截止：当前时间 → Unix时间戳(ms)

# 上月（对照期）
起始：上月1日 00:00:00 → Unix时间戳(ms)
截止：上月最后一天 23:59:59 → Unix时间戳(ms)
```

**CLI命令：**

> **⚠️ CES ShowMetricData不支持--User-Agent参数，禁止附加**

```bash
# 查询本月外网下载流量
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=download_traffic_extranet \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<FromTimestamp> \
  --to=<ToTimestamp>

# 查询本月内网下载流量
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=download_traffic_intranet \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<FromTimestamp> \
  --to=<ToTimestamp> \
  --User-Agent HuaweiCloud-Agent-Skills/huaweicloud-obs-manage
```

**CES ShowMetricData参数说明：**

| 参数 | 必需 | 描述 |
|------|------|------|
| `--namespace` | 是 | 固定值 `SYS.OBS` |
| `--metric_name` | 是 | 指标名称 |
| `--dim.0` | 是 | 维度，格式 `bucket_name,<BucketName>` |
| `--period` | 是 | 聚合周期，`86400`（1天） |
| `--filter` | 是 | 聚合方式，`sum`（求和） |
| `--from` | 是 | 起始时间（毫秒时间戳） |
| `--to` | 是 | 截止时间（毫秒时间戳） |

**响应关键字段：**

| 字段 | 描述 |
|------|------|
| `datapoints[].average` | 聚合周期内的平均值 |
| `datapoints[].sum` | 聚合周期内的求和值 |
| `datapoints[].timestamp` | 数据点时间戳 |

> **⚠️ 关键：必须使用流量指标，不能使用带宽指标**
>
> - ✅ `download_traffic_extranet`：公网下载流量（单位Bytes，累计量）
> - ✅ `download_traffic_intranet`：内网下载流量（单位Bytes，累计量）
> - ❌ `download_bytes`：总下载带宽（单位Bytes/s，速率值，不是累计量）
> - ❌ `download_bytes_extranet`/`download_bytes_intranet`：带宽指标（速率值）
>
> 查询时使用 `filter=sum` 获取时间范围内的总流量，流量指标直接求和即为总字节数。
> 结果需将字节转换为合适单位：`GB = bytes / (1024^3)`, `MB = bytes / (1024^2)`, `KB = bytes / 1024`

---

### 5. GetMonthlyRequests - 查询本月请求总数

> **⚠️ 关键：请求数据通过CES获取，非OBS直接API**

**必需参数：** 同GetMonthlyTraffic

**CLI命令：**

```bash
# 查询本月总请求数
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<FromTimestamp> \
  --to=<ToTimestamp>

# 查询本月GET请求数
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=get_request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<FromTimestamp> \
  --to=<ToTimestamp>

# 查询本月PUT请求数
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=put_request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<FromTimestamp> \
  --to=<ToTimestamp>
```

> **⚠️ 注意：OBS请求计费相关**
>
> - GET类请求（GetObject、HeadObject、ListObjects等）
> - PUT类请求（PutObject、CopyObject、CreateMultipartUpload等）
> - 不同类型请求的计费单价不同，详细参见OBS定价页面

---

## 月环比计算

**公式：**

```
月环比(%) = (本月值 - 上月值) / 上月值 × 100%
```

**特殊情况：**

| 情况 | 处理 |
|------|------|
| 上月值 = 0，本月值 > 0 | 显示 "新增（上月为0）" |
| 上月值 = 0，本月值 = 0 | 显示 "N/A" |
| 上月值 > 0 | 计算月环比百分比，保留2位小数 |

**示例：**

```
本月外网下载流量 = 125.3 GB
上月外网下载流量 = 98.7 GB
月环比 = (125.3 - 98.7) / 98.7 × 100% = +26.95%
```

---

## 官方文档

- [OBS API参考](https://support.huaweicloud.com/api-obs/obs_04_0001.html)
- [OBS SDK参考](https://support.huaweicloud.com/sdk-python-devg-obs/obs_22_0100.html)
- [obsutil命令行工具](https://support.huaweicloud.com/utiltg-obs/obs_11_0001.html)
- [CES ShowMetricData API](https://support.huaweicloud.com/api-ces/ces_03_0059.html)
- [CES OBS监控指标](https://support.huaweicloud.com/usermanual-ces/ces_03_0065.html)
- [OBS定价](https://www.huaweicloud.com/pricing.html#/obs)
