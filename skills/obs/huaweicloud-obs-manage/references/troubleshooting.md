# 故障排除 - 华为云OBS对象存储管理

## 目录

- [hcloud CLI问题](#hcloud-cli问题)
- [obsutil上传问题](#obsutil上传问题)
- [CES监控数据问题](#ces监控数据问题)
- [定时上传问题](#定时上传问题)
- [桶容量查询问题](#桶容量查询问题)
- [月环比计算问题](#月环比计算问题)

---

## hcloud CLI问题

### 1. hcloud OBS模块无ListAllMyBucketsType命令

**问题描述：**
运行 `hcloud OBS ListAllMyBucketsType` 时提示 `Error: No such command: "ListAllMyBucketsType"`。

**根因：**
hcloud CLI（v7.2.2实测）OBS模块**不包含** `ListAllMyBucketsType` 命令。hcloud OBS模块仅提供少量桶管理操作，列出桶需通过obsutil方式。

**解决方案：**
```bash
# 列出所有桶
hcloud obs ls

# 筛选指定地域的桶
hcloud obs ls 2>&1 | grep "cn-south-1"

# 提取桶名列表
hcloud obs ls 2>&1 | awk '/obs:\/\// && /cn-south-1/ {print $1}' | sed 's|obs://||'
```

### 2. hcloud OBS模块无GetBucketStorageInfo命令

**问题描述：**
运行 `hcloud OBS GetBucketStorageInfo` 时提示命令不存在。

**根因：**
hcloud CLI的OBS模块可能未包含所有OBS API操作，`GetBucketStorageInfo` 属于桶扩展API，部分hcloud版本不支持。

**解决方案：**

**方式一：使用CES容量指标（推荐，适合批量查询）**
```bash
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=capacity_total \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=average \
  --from=<当天0点时间戳ms> \
  --to=<当前时间戳ms>
```
返回 `datapoints[-1].average` 即为桶容量（Bytes）。

**方式二：使用obsutil替代**
```bash
# 使用obsutil列出桶内对象并统计
obsutil ls obs://<BucketName> -limit=0 -s
```

**方式三：使用OBS REST API直接调用**
```bash
# 通过curl调用OBS REST API获取桶存储信息
# GET /?storageInfo
curl -X GET "https://<BucketName>.obs.<RegionId>.myhuaweicloud.com/?storageInfo" \
  -H "Date: $(date -u '+%a, %d %b %Y %H:%M:%S GMT')" \
  -H "Authorization: OBS <Signature>"
```

**方式三：使用OBS REST API直接调用（方式二改名为方式三）**
```python
from obs import ObsClient

obs_client = ObsClient(...)
resp = obs_client.getBucketStorageInfo(bucketName)
print(f"Size: {resp.body.size}, Objects: {resp.body.objectNumber}")
```

### 2. hcloud CES ShowMetricData参数格式问题

**问题描述：**
CES ShowMetricData的dimensions参数格式错误。

**正确格式：**
```bash
--dimensions.0.name=bucket_name \
--dimensions.0.value=my-bucket
```

**常见错误：**
```bash
# ❌ 错误：dimensions索引从1开始
--dimensions.1.name=bucket_name

# ❌ 错误：维度名不正确
--dimensions.0.name=bucket

# ❌ 错误：缺少索引
--dimensions.name=bucket_name
```

> **hcloud CES参数索引从0开始**，不是从1开始。

### 3. hcloud凭证配置问题

| 错误消息 | 原因 | 解决 |
|---------|------|------|
| `No valid credential` | 未配置AK/SK | 运行 `hcloud configure` |
| `Access denied` | AK/SK无效或过期 | 重新配置凭证 |
| `Invalid region` | 区域ID不正确 | 使用正确的区域ID |
| `Please set ak, sk and endpoint` | obsutil凭证未配置 | 执行 `hcloud obs config -i=<AK> -k=<SK> -e=obs.<region>.myhuaweicloud.com` |
| `InvalidAccessKeyId` | obsutil配置的AK/SK无效 | 重新执行 `hcloud obs config` 配置正确凭证 |

> **⚠️ obsutil凭证检查流程**
>
> 执行任何OBS操作前，必须先验证obsutil凭证是否可用：
> ```bash
> hcloud obs ls -limit=1
> ```
> 若返回 `Please set ak, sk and endpoint in the configuration file!` 或 `InvalidAccessKeyId`，
> 直接告知用户以下示例命令，由用户自行在终端配置：
>
> ```
> obsutil凭证未配置，请在终端中执行以下命令完成配置（AK/SK可在华为云控制台"我的凭证"页面获取）：
>
>   hcloud obs config -i=<你的AK> -k=<你的SK> -e=obs.<区域>.myhuaweicloud.com
>
> 示例（广州地域）：
>   hcloud obs config -i=<你的AK> -k=<你的SK> -e=obs.cn-south-1.myhuaweicloud.com
>
> 常见Endpoint：
>   cn-north-4  → obs.cn-north-4.myhuaweicloud.com
>   cn-east-3   → obs.cn-east-3.myhuaweicloud.com
>   cn-south-1  → obs.cn-south-1.myhuaweicloud.com
>   cn-southwest-2 → obs.cn-southwest-2.myhuaweicloud.com
>
> 配置完成后重试即可。
> ```

---

## obsutil上传问题

### 1. 上传超时或速度慢

**问题描述：**
上传大文件或大量文件时超时或速度很慢。

**解决方案：**

```bash
# 增加并发数
obsutil cp <LocalPath> obs://<BucketName>/<Prefix> -r -flat -p=10

# 降低并发数（网络不稳定时）
obsutil cp <LocalPath> obs://<BucketName>/<Prefix> -r -flat -p=3

# 调整分片大小（大文件场景）
obsutil cp <LocalPath> obs://<BucketName>/<Prefix> -flat -threshold=100MB
```

### 2. 上传中断后恢复

**问题描述：**
上传过程中网络中断或程序异常退出。

**解决方案：**
```bash
# 使用断点续传（默认启用）
obsutil cp <LocalPath> obs://<BucketName>/<Prefix> -r -flat -fr

# 查看断点续传记录
obsutil ls -failed -limit=100
```

### 3. 上传报"access denied"

**问题描述：**
上传时报403 Access Denied。

**根因排查：**

1. **obsutil凭证未配置或无效**
   ```bash
   # 检查obsutil凭证是否配置：运行 ls 命令，若报错则未配置
   hcloud obs ls -limit=1
   ```
   
   若未配置，告知用户自行在终端执行：
   ```
   hcloud obs config -i=<你的AK> -k=<你的SK> -e=obs.<区域>.myhuaweicloud.com
   ```
   示例（广州地域）：
   ```bash
   hcloud obs config -i=<你的AK> -k=<你的SK> -e=obs.cn-south-1.myhuaweicloud.com
   ```
   > AK/SK可在华为云控制台"我的凭证"页面获取。禁止在对话中要求用户直接提供AK/SK。

2. **IAM权限不足**
   - 检查IAM策略是否包含 `obs:object:PutObject` 权限

3. **桶策略限制**
   - 检查桶策略是否限制了上传操作
   - 通过OBS控制台 → 桶 → 访问控制 → 桶策略 查看

4. **桶ACL限制**
   - 检查桶ACL是否允许当前账号上传

### 4. 上传报"bucket not exist"

**问题描述：**
上传时报404 Bucket Not Found。

**根因：**
- 桶名拼写错误（OBS桶名全局唯一，需精确匹配）
- 桶所在区域与obsutil配置的Endpoint不匹配

**解决方案：**
```bash
# 先列出桶，确认桶名和区域
obsutil ls -limit=100

# 确认Endpoint配置正确
obsutil config -help
```

---

## CES监控数据问题

### 1. CES查询返回空数据

**问题描述：**
CES ShowMetricData返回空datapoints数组。

**可能原因及解决：**

1. **桶名不正确**
   - 确认dimensions.0.value使用正确的桶名

2. **时间范围内无数据**
   - 桶在该时间段内无对应操作（如无下载流量、无请求）
   - 尝试扩大时间范围验证

3. **CES数据采集延迟**
   - CES指标数据通常有1-5分钟延迟
   - 若查询最近几分钟的数据，可能尚未采集

4. **命名空间或指标名错误**
   - 确认namespace为 `SYS.OBS`（不是 `OBS` 或 `SYS.OBJECT_STORAGE`）
   - 确认metric_name正确（如 `download_bytes` 不是 `download_flow`）

5. **period参数不匹配**
   - 数据粒度需与period匹配
   - OBS监控指标默认采集周期为5分钟
   - 查询长期数据时period设为86400（1天）

### 2. CES ShowMetricData参数格式错误

**关键参数对照：**

| 参数 | 正确值 | 常见错误 |
|------|--------|---------|
| `--namespace` | `SYS.OBS` | `OBS`, `SYS.OBJECT_STORAGE` |
| `--metric_name` | `download_bytes` | `downloadBytes`, `download_flow` |
| `--dimensions.0.name` | `bucket_name` | `bucket`, `bucketName` |
| `--period` | `86400` | `86400000`（毫秒而非秒） |
| `--filter` | `sum` | `SUM`, `total` |
| `--from`/`--to` | 毫秒时间戳(13位) | 秒时间戳(10位) |

### 3. CES ShowMetricData不支持--User-Agent参数

**问题描述：**
运行 `hcloud CES ShowMetricData --User-Agent=xxx` 报错 `[USE_ERROR]不正确的参数:User-Agent`。

**根因：**
CES模块的ShowMetricData命令**不支持** `--User-Agent` 参数。该参数仅在OBS模块部分命令中可用。

**解决方案：**
CES查询命令**禁止附加** `--User-Agent` 参数。

### 4. 月环比上月数据为0

**问题描述：**
上月流量或请求数据为0，无法计算月环比。

**可能原因：**
- 桶在上月刚创建，无操作数据
- CES监控未开通或数据采集未覆盖上月
- 时间范围计算错误

**处理方式：**
- 上月=0且本月>0：显示 "新增（上月为0）"
- 上月=0且本月=0：显示 "N/A"

---

## 定时上传问题

### 1. crontab定时任务未执行

**问题描述：**
已设置crontab但上传脚本未按时执行。

**排查步骤：**

1. **检查crontab是否设置成功**
   ```bash
   crontab -l
   ```

2. **检查cron服务是否运行**
   ```bash
   # Linux
   systemctl status cron
   # macOS
   sudo launchctl list | grep cron
   ```

3. **检查脚本执行权限**
   ```bash
   ls -la $HOME/obs-scheduled-upload-<BucketName>.sh
   chmod +x $HOME/obs-scheduled-upload-<BucketName>.sh
   ```

4. **检查PATH环境变量**
   ```bash
   # crontab环境中PATH最小，需在脚本中添加
   # 在脚本开头添加：
   export PATH=/usr/local/bin:/usr/bin:/bin:$PATH
   ```

5. **查看上传日志**
   ```bash
   tail -f $HOME/obs-scheduled-upload-<BucketName>.log
   ```

### 2. crontab执行但上传失败

**问题描述：**
crontab日志显示执行但obsutil上传报错。

**常见原因：**
- obsutil凭证文件在crontab环境中无法访问
- 网络问题
- 磁盘空间不足

**解决方案：**
```bash
# 在上传脚本中使用obsutil完整路径
/usr/local/bin/obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -flat

# 指定obsutil配置文件路径
obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -flat -config=/home/user/.obsutilconfig
```

### 3. 删除定时任务

```bash
# 删除特定OBS上传的定时任务
crontab -l | grep -v "obs-scheduled-upload-<BucketName>" | crontab -

# 清除所有定时任务（谨慎操作！）
# crontab -r
```

---

## 桶容量查询问题

### 1. 归档存储桶容量显示不完整

**问题描述：**
GetBucketStorageInfo返回的容量和对象数小于实际值。

**根因：**
归档存储类的对象需恢复后才能访问，未恢复对象不计入统计。

**解决方案：**
- 归档对象需先恢复（RestoreObject）才能被统计
- 若需精确统计归档对象，通过CES监控指标 `cold_storage_bytes` / `cold_object_count` 获取

### 2. GetBucketStorageInfo性能问题

**问题描述：**
对象数较多的桶（百万级以上）查询容量耗时较长。

**解决方案：**
- 使用CES监控指标 `standard_storage_bytes` / `standard_object_count` 替代（实时性略差但性能好）
- 设置查询超时并重试

---

## 月环比计算问题

### 1. 时间范围计算错误

**正确计算方法：**

```bash
# 本月起始时间
current_month_start = "$(date +%Y-%m-01)"  # 如 2026-05-01
# 转换为毫秒时间戳
from_timestamp = $(date -d "$current_month_start" +%s)000  # 如 1746057600000

# 本月截止时间（当前时间）
to_timestamp = $(date +%s)000

# 上月起始时间
last_month_start = "$(date -d "$(date +%Y-%m-01) -1 month" +%Y-%m-01)"

# 上月截止时间（上月最后一天23:59:59）
last_month_end = "$(date -d "$(date +%Y-%m-01) -1 second" +%Y-%m-%dT23:59:59)"
```

### 2. 流量单位转换

```
Bytes → KB: / 1024
Bytes → MB: / (1024 * 1024)
Bytes → GB: / (1024 * 1024 * 1024)
Bytes → TB: / (1024 * 1024 * 1024 * 1024)
```

**建议：** 根据流量大小选择合适的显示单位：
- < 1 MB → 显示 KB
- < 1 GB → 显示 MB
- < 1 TB → 显示 GB
- >= 1 TB → 显示 TB

---

## 官方文档

- [hcloud故障排除](https://support.huaweicloud.com/cli/cli_hcloud_faq.html)
- [obsutil故障排除](https://support.huaweicloud.com/utiltg-obs/obs_11_0006.html)
- [CES FAQ](https://support.huaweicloud.com/ces_faq/ces_faq_0001.html)
- [OBS错误码参考](https://support.huaweicloud.com/api-obs/obs_04_0115.html)
