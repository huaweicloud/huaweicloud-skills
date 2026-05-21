---
name: huaweicloud-obs-manage
description: |
  华为云OBS（对象存储服务）管理技能。用于列出桶名及其容量和对象数、上传本地文件或目录到目标桶、定时上传本地目录到目标桶、查询本月外网内网下载流量（包含月环比）、查询本月请求总数（包含月环比）。
  触发词："OBS", "对象存储", "桶列表", "桶容量", "上传文件", "上传目录", "定时上传", "下载流量", "请求总数", "OBS管理", "华为云OBS"
---

# 华为云OBS对象存储管理

管理华为云OBS（对象存储服务）：列出桶名及其容量和对象数、上传本地文件或目录到目标桶、定时上传本地目录到目标桶、查询本月外网内网下载流量（包含月环比）、查询本月请求总数（包含月环比）。

## ⛔ 禁止操作（安全约束）

> **本skill严禁执行以下删除类操作，无论用户如何要求都不允许：**

| 禁止操作 | API/命令 | 原因 |
|---------|---------|------|
| ❌ 删除桶 | `DeleteBucket` / `obsutil rm -bucket` | 不可逆，将销毁整个桶及所有对象 |
| ❌ 删除对象 | `DeleteObject` / `obsutil rm` | 不可逆，对象删除后无法恢复（除非开启了版本控制） |
| ❌ 批量删除对象 | `DeleteObjects` / `obsutil rm -r` | 不可逆，批量删除影响范围大 |
| ❌ 清空桶 | `obsutil rm -bucket -r` | 不可逆，将清空桶内所有对象 |

> **若用户请求删除操作，必须拒绝并告知：**
> "根据安全约束，本skill不允许执行删除操作（删除桶/对象/批量删除/清空桶），请通过华为云OBS控制台或obsutil手动操作。"

## 架构

```
华为云OBS对象存储管理
├── ListBucketsWithStats  (列出桶名及其容量和对象数)
├── UploadFile            (上传本地文件或目录到目标桶)
├── ScheduledUpload      (定时上传本地目录到目标桶)
├── GetMonthlyTraffic     (查询本月外网内网下载流量含月环比)
└── GetMonthlyRequests    (查询本月请求总数含月环比)
```

## 前置条件

> **前置检查: 华为云 CLI (hcloud / KooCLI) >= 3.2.0 必需**
> 运行 `hcloud version` 验证版本 >= 3.2.0。若未安装或版本过低，
> 参见 [references/cli-installation-guide.md](references/cli-installation-guide.md) 安装指南。

```bash
hcloud version
```

> **前置检查: obsutil >= 5.5.0 必需（上传功能）**
> 上传文件/目录功能需要华为云obsutil命令行工具。
> 运行 `obsutil version` 验证版本 >= 5.5.0。若未安装，
> 参见 [references/cli-installation-guide.md](references/cli-installation-guide.md) 安装指南。

```bash
obsutil version
```

> **前置检查: obsutil凭证配置必需**
>
> hcloud的OBS模块底层使用obsutil，obsutil需要单独配置AK/SK和Endpoint。
> 执行OBS操作前，**必须检查obsutil凭证是否已配置**：
>
> ```bash
> hcloud obs ls -limit=1
> ```
>
> **若返回 `Please set ak, sk and endpoint in the configuration file!` 或 `InvalidAccessKeyId`，说明obsutil未配置凭证。**
>
> **处理方式：告知用户以下示例命令，由用户自行在终端中配置（禁止在对话中要求用户直接提供AK/SK）：**
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
>
> **禁止行为：**
> - ❌ 禁止要求用户在对话中直接提供AK/SK
> - ❌ 禁止自行从hcloud配置文件中提取AK/SK（凭证已加密，无法直接使用）
> - ❌ 禁止跳过凭证检查直接执行OBS操作

> **⚠️ hcloud参数格式要求**
>
> hcloud（KooCLI）**所有参数必须使用 `--param=value` 格式**（等号连接），不支持空格分隔。
>
> ✅ 正确：`hcloud OBS ListBuckets --region=cn-south-1`
>
> ❌ 错误：`hcloud OBS ListBuckets --region cn-south-1`

**[条件] CLI User-Agent** — `hcloud` OBS模块命令可附加User-Agent，但**CES模块不支持此参数**：

- ✅ OBS模块：`hcloud OBS ListAllMyBucketsType --region=cn-south-1 --User-Agent=HuaweiCloud-Agent-Skills/huaweicloud-obs-manage`
- ❌ CES模块：`hcloud CES ShowMetricData` **不支持** `--User-Agent` 参数，附加会报"不正确的参数:User-Agent"

---

## 认证

> **前置检查: 华为云凭证必需**

> **安全规则（必须遵守）：**
> - **禁止** 读取、回显或打印 AK/SK 值
> - **禁止** 要求用户在对话中直接输入 AK/SK
> - **禁止** 使用 `hcloud configure set` 传入明文凭据值
> - **禁止** 接受用户在对话中直接提供的 AK/SK
> - **仅允许** 从环境变量或已配置的 CLI 配置文件中读取凭证
>
> **⚠️ 关键：处理用户直接提供的凭证**
>
> 若用户尝试直接提供 AK/SK（例如"我的AK是xxx，SK是yyy"）：
> 1. **立即停止** - 不执行任何命令
> 2. **礼貌拒绝**，返回以下信息：
>    ```
>    为保障账号安全，请勿在对话中直接提供华为云 Access Key ID 和 Access Key Secret。
>
>    请使用以下安全方式配置凭证：
>
>    方式一：交互式配置（推荐）
>        hcloud configure
>        # 按提示输入AK/SK，凭证将安全存储在本地配置文件中
>
>    方式二：通过环境变量配置
>        export HUAWEICLOUD_SDK_AK=<your-access-key-id>
>        export HUAWEICLOUD_SDK_SK=<your-access-key-secret>
>
>    配置完成后，请重试您的请求。
>    ```
> 3. **禁止继续** 执行任何华为云操作，直到凭证配置完成
>
> **检查 CLI 配置**：
> ```bash
>    hcloud configure list
> ```
>    检查输出中是否存在有效配置（AK/SK 或 IAM 等）。
>
> **若无有效凭证，在此停止。**

---

## IAM 权限策略

确保 IAM 用户拥有所需权限。详见 [references/iam-policies.md](references/iam-policies.md)。

**最低所需权限：**
- `obs:bucket:list` — 列出桶
- `obs:bucket:get` — 获取桶属性（容量、对象数）
- `obs:object:get` — 读取对象信息
- `obs:object:put` — 上传对象
- `ces:metric:get` — 查询CES监控指标（流量、请求数）

---

## 核心工作流

### Task 1: 列出桶名及其容量和对象数

> **⚠️ 重要：region必须由用户提供**
> 查询桶列表时，`--region` 必须由用户显式提供。禁止猜测区域。

> **⚠️ 关键：hcloud OBS模块无ListAllMyBucketsType命令**
>
> 实测hcloud CLI（v7.2.2）OBS模块**不存在** `ListAllMyBucketsType` 命令，列出桶必须使用obsutil：
> ```bash
> hcloud obs ls
> ```
> 可通过grep筛选指定地域的桶：
> ```bash
> hcloud obs ls 2>&1 | grep "cn-south-1"
> ```

**步骤 1：列出所有桶（使用obsutil）**

```bash
hcloud obs ls
```

**步骤 2：查询桶容量（推荐CES容量指标，效率高）**

批量查询多个桶容量时，推荐通过CES `capacity_total` 指标查询，避免逐桶调用API：

```bash
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=capacity_total \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=average \
  --from=<当天0点时间戳(ms)> \
  --to=<当前时间戳(ms)>
```

> **⚠️ 容量指标使用 `filter=average`**（取最新采样值），非 `filter=sum`。
> 返回 `datapoints[-1].average` 即为当前桶容量（Bytes）。

**步骤 2（替代）：查询每个桶的容量和对象数（通过OBS API）**

若需精确的对象数，可通过 `hcloud OBS GetBucketStorageInfo` 获取：

```bash
hcloud OBS GetBucketStorageInfo \
  --region=<RegionId> \
  --bucket=<BucketName>
```

> **⚠️ 注意：GetBucketStorageInfo可能不被hcloud支持**
> 若报"No such command"，替代方案：`obsutil ls obs://<BucketName> -limit=0 -s`

**响应关键字段：**

| 字段 | 描述 |
|------|------|
| `size` | 桶中对象总大小（字节） |
| `objectNumber` | 桶中对象总数 |

**输出格式示例：**

```
桶名                容量(GB)    对象数
my-bucket-1         125.3       1024
my-bucket-2         0.5         15
my-bucket-3         2048.0      50000
```

> **⚠️ 注意：GetBucketStorageInfo不适用于归档存储桶的未恢复对象**
>
> 归档存储类的对象需要恢复后才可访问，未恢复对象不计入统计。
> 若桶包含归档存储对象，返回的容量和对象数可能不包含未恢复的归档对象。

> **💡 实战经验：容量Top N桶快速查询**
>
> 查询容量前N的桶时，流程为：
> 1. `hcloud obs ls` 列出目标地域所有桶名
> 2. 逐桶调用CES `capacity_total` 指标获取容量
> 3. 按容量降序排序，取Top N
>
> 此方式效率远高于逐桶调用GetBucketStorageInfo API。

### Task 2: 上传本地文件或目录到目标桶

> **⚠️ 关键：上传操作需使用obsutil，非hcloud**
>
> hcloud CLI不支持OBS对象上传操作（无PutObject/UploadPart等CLI命令）。
> 上传文件/目录必须使用 **obsutil** 命令行工具。

> **前置条件：**
> - obsutil >= 5.5.0 必需
> - obsutil需已配置AK/SK：`obsutil config -ak=<AK> -sk=<SK> -e=<Endpoint>`
>   - **禁止在对话中要求用户直接输入AK/SK**，引导用户自行通过obsutil config配置

> **⚠️ 关键：必需参数必须由用户提供，禁止猜测**

| 序号 | 询问内容 | 说明 |
|------|---------|------|
| 1 | **本地文件/目录路径** | 上传的本地路径，必须存在且可读 |
| 2 | **目标桶名** | 上传目标OBS桶名 |
| 3 | **目标路径前缀（可选）** | 桶内目标路径前缀，默认上传到桶根目录 |

**上传单个文件：**

```bash
obsutil cp <LocalFilePath> obs://<BucketName>/<ObjectKey> -flat
```

**示例：**

```bash
obsutil cp /home/user/data/report.csv obs://my-bucket/reports/report.csv -flat
```

**上传整个目录：**

```bash
obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -flat
```

**示例：**

```bash
obsutil cp /home/user/data/ obs://my-bucket/data/ -r -flat
```

> **⚠️ `-flat` 参数说明**
>
> `-flat`：不上传本地目录结构，只上传文件。若需保留目录结构，去掉 `-flat`。
> - 使用 `-flat`：`/home/user/data/sub/file.txt` → `obs://bucket/prefix/file.txt`
> - 不使用 `-flat`：`/home/user/data/sub/file.txt` → `obs://bucket/prefix/sub/file.txt`

> **⚠️ 上传大文件自动分片**
>
> obsutil上传大文件时自动使用分片上传，默认分片大小为9MB。
> 可通过 `-p` 参数指定并发数（默认5），`-threshold` 指定分片阈值。

**错误处理**
1. 若提示"bucket not exist"，提示用户确认桶名是否正确
2. 若提示"access denied"，提示用户检查obsutil配置和桶权限
3. 若本地路径不存在，提示用户确认路径是否正确
4. 若上传超时或网络错误，建议使用 `-p` 降低并发数或重试

### Task 3: 定时上传本地目录到目标桶

> **⚠️ 关键：定时上传基于操作系统定时任务机制**
>
> 本skill通过操作系统级定时任务（Linux: crontab / macOS: crontab / Windows: Task Scheduler）
> 实现定时上传，**不依赖额外守护进程**。

> **⚠️ 关键：必需参数必须由用户提供，禁止猜测**

| 序号 | 询问内容 | 说明 |
|------|---------|------|
| 1 | **本地目录路径** | 需定时上传的本地目录，必须存在 |
| 2 | **目标桶名** | 上传目标OBS桶名 |
| 3 | **目标路径前缀（可选）** | 桶内目标路径前缀，默认上传到桶根目录 |
| 4 | **定时周期** | 定时执行周期，如每小时、每天8:00、每30分钟等 |
| 5 | **crontab表达式（可选）** | 若用户熟悉cron表达式可直接提供 |

**实现方式（Linux/macOS）：**

> **⚠️ 关键：脚本和日志存放位置**
>
> - 若用户指定了存放路径，使用用户指定路径
> - 若用户未指定，脚本和日志存放在**用户家目录**（`$HOME`）中，禁止使用 `/tmp`（重启可能丢失）
> - 脚本路径：`$HOME/obs-scheduled-upload-<BucketName>.sh`
> - 日志路径：`$HOME/obs-scheduled-upload-<BucketName>.log`

**步骤 1：生成obsutil上传命令脚本**

创建上传脚本 `$HOME/obs-scheduled-upload-<BucketName>.sh`：

```bash
#!/bin/bash
# OBS定时上传脚本
# 桶：<BucketName>
# 本地目录：<LocalDirPath>
# 生成时间：<Timestamp>

LOG_FILE="$HOME/obs-scheduled-upload-<BucketName>.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始定时上传" >> "$LOG_FILE"

obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -flat -f >> "$LOG_FILE" 2>&1

RESULT=$?
if [ $RESULT -eq 0 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 上传成功" >> "$LOG_FILE"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 上传失败，退出码: $RESULT" >> "$LOG_FILE"
fi
```

**步骤 2：设置crontab定时任务**

```bash
# 每小时执行
(crontab -l 2>/dev/null; echo "0 * * * * /bin/bash $HOME/obs-scheduled-upload-<BucketName>.sh") | crontab -

# 每天8:00执行
(crontab -l 2>/dev/null; echo "0 8 * * * /bin/bash $HOME/obs-scheduled-upload-<BucketName>.sh") | crontab -

# 每30分钟执行
(crontab -l 2>/dev/null; echo "*/30 * * * * /bin/bash $HOME/obs-scheduled-upload-<BucketName>.sh") | crontab -
```

**步骤 3：验证定时任务已设置**

```bash
crontab -l
```

**实现方式（Windows - Task Scheduler）：**

```powershell
# 创建定时任务（每天8:00执行）
schtasks /create /tn "OBS-ScheduledUpload-<BucketName>" /tr "obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -flat" /sc daily /st 08:00 /f
```

> **⚠️ 重要：定时上传的注意事项**
>
> 1. **幂等性**：obsutil cp默认跳过已存在且相同的对象（通过MD5比对），重复上传不会产生冗余
> 2. **增量上传**：只上传本地新增或修改的文件，已存在且未修改的文件不会重复上传
> 3. **日志**：上传日志记录在 `/tmp/obs-scheduled-upload-<BucketName>.log`
> 4. **删除不同步**：定时上传仅同步新增/修改文件，**不会删除桶中本地已删除的对象**（需用户手动清理）
> 5. **crontab环境**：crontab执行环境与交互式shell不同，需确保obsutil在PATH中，建议在脚本中使用obsutil完整路径

**管理定时任务：**

```bash
# 查看当前用户的定时任务
crontab -l

# 删除特定定时任务
crontab -l | grep -v "obs-scheduled-upload-<BucketName>" | crontab -
```

### Task 4: 查询本月外网内网下载流量（包含月环比）

> **⚠️ 关键：流量数据通过CES（云监控服务）获取**
>
> OBS的流量监控指标由CES（云监控服务）采集和管理，需通过CES API查询。

> **⚠️ 重要：必需参数必须由用户提供**
> 查询流量时，`--region` 和桶名必须由用户显式提供。禁止猜测。

> **⚠️ 关键：时间范围必须精确匹配用户表述**
>
> 用户可能使用不同的时间表述，必须严格区分：
>
> | 用户表述 | 时间范围 | 说明 |
> |---------|---------|------|
> | "本月" | 当月1日 00:00:00 ~ 当前时间 | 自然月 |
> | "最近一个月" / "最近30天" | 当前时间-30天 ~ 当前时间 | 滚动30天窗口 |
> | "上月" | 上月1日 00:00:00 ~ 上月最后一天 23:59:59 | 上个自然月 |
> | 具体日期范围 | 用户指定的起止时间 | 如"5月1日到5月19日" |
>
> **⚠️ "本月"和"最近一个月"是不同的时间范围！**
> - "本月"：从当月1日算起（如5月1日~5月19日，共19天）
> - "最近一个月"：从当前时间往前推30天（如4月19日~5月19日，共30天）
> - 华为云OBS控制台默认统计周期为"最近30天"，若用户提到控制台数据，应使用最近30天范围
>
> **月环比对照期计算：**
> - 若用户查询"本月"，对照期为"上月"（上个自然月）
> - 若用户查询"最近一个月"，对照期为"再往前推30天"（即前30~60天）
> - 若用户查询具体日期范围，对照期为前一个等长周期

**步骤 1：根据用户表述确定时间范围**

> **月环比计算公式：**
> `月环比 = (当前周期值 - 对照周期值) / 对照周期值 × 100%`

**步骤 2：查询外网下载流量**

> **⚠️ CES ShowMetricData不支持--User-Agent参数，禁止附加**

```bash
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=download_traffic_extranet \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<起始时间戳(ms)> \
  --to=<截止时间戳(ms)>
```

**步骤 3：查询内网下载流量**

```bash
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=download_traffic_intranet \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<起始时间戳(ms)> \
  --to=<截止时间戳(ms)>
```

**步骤 4：查询对照期外网/内网下载流量（用于计算月环比）**

将步骤2、3中的时间范围替换为对照期时间范围，分别查询对照期外网和内网下载流量。

**步骤 5：汇总输出**

```
OBS下载流量统计 - 桶: <BucketName>
═══════════════════════════════════════════════════════
指标              本月              上月              月环比
───────────────────────────────────────────────────────
外网下载流量      125.3 GB          98.7 GB           +26.95%
内网下载流量      50.2 GB           45.0 GB           +11.56%
总计下载流量      175.5 GB          143.7 GB          +22.13%
═══════════════════════════════════════════════════════
统计周期: 2026-05-01 ~ 2026-05-19
```

> **⚠️ CES ShowMetricData参数说明**
>
> - `--namespace=SYS.OBS`：OBS的CES命名空间
> - `--dim.0=bucket_name,<BucketName>`：维度格式为 `key,value`，OBS维度key为 `bucket_name`
> - `--period=86400`：聚合周期86400秒（1天），用于按天聚合后求和
> - `--filter=sum`：聚合方式为求和
> - `--from`/`--to`：时间戳，毫秒级Unix时间戳

> **⚠️ 关键：必须使用流量指标，不能使用带宽指标**
>
> - ✅ `download_traffic_extranet`：公网下载流量（单位Bytes，累计量）
> - ✅ `download_traffic_intranet`：内网下载流量（单位Bytes，累计量）
> - ❌ `download_bytes`：总下载带宽（单位Bytes/s，速率值，不是累计量）
> - ❌ `download_bytes_extranet`/`download_bytes_intranet`：带宽指标（速率值）
>
> 流量指标直接求和即可得到总流量，带宽指标需要乘以聚合周期才能换算，容易出错，**必须使用流量指标**。

**CES OBS流量指标参考：**

| 指标名 | 描述 | 单位 |
|--------|------|------|
| `download_traffic_extranet` | 公网下载流量 | Bytes |
| `download_traffic_intranet` | 内网下载流量 | Bytes |

详细指标说明参见 [references/obs-metrics.md](references/obs-metrics.md)。

### Task 5: 查询本月请求总数（包含月环比）

> **⚠️ 关键：请求数据通过CES（云监控服务）获取**
>
> OBS的请求监控指标由CES采集和管理，需通过CES API查询。

> **⚠️ 重要：必需参数必须由用户提供**
> 查询请求数时，`--region` 和桶名必须由用户显式提供。禁止猜测。

> **⚠️ 关键：时间范围必须精确匹配用户表述**（同Task 4）
>
> 必须严格区分"本月"（自然月）和"最近一个月"（滚动30天）等表述，
> 详见Task 4中的时间范围对照表。

**步骤 1：根据用户表述确定时间范围**（同Task 4）

**步骤 2：查询各类请求总数**

> **⚠️ CES ShowMetricData不支持--User-Agent参数，禁止附加**

```bash
# 查询本月GET请求数
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=get_request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<起始时间戳(ms)> \
  --to=<截止时间戳(ms)>

# 查询PUT请求数
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=put_request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<起始时间戳(ms)> \
  --to=<截止时间戳(ms)>

# 查询POST/DELETE/HEAD请求数（如需完整统计）
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=post_request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<起始时间戳(ms)> \
  --to=<截止时间戳(ms)>
```

> **总请求数 = GET + PUT + POST + DELETE + HEAD**（CES无 `request_count` 单一指标）

**步骤 3：查询上月各类请求数（用于计算月环比）**

将步骤2中的时间范围替换为上月时间范围，分别查询上月总请求数、GET请求数、PUT请求数。

**步骤 4：汇总输出**

```
OBS请求统计 - 桶: <BucketName>
═══════════════════════════════════════════════════════
指标              本月              上月              月环比
───────────────────────────────────────────────────────
总请求数          1,250,000         980,000           +27.55%
GET请求数         1,000,000         800,000           +25.00%
PUT请求数         200,000           160,000           +25.00%
其他请求数        50,000            20,000            +150.00%
═══════════════════════════════════════════════════════
统计周期: 2026-05-01 ~ 2026-05-19
```

> **⚠️ 注意：月环比特殊情况处理**
>
> - 上月值为0时，月环比显示"N/A"（无法计算）
> - 上月值为0且本月值>0时，月环比显示"新增（上月为0）"
> - 本月值和上月值都为0时，月环比显示"N/A"

**CES OBS请求指标参考：**

| 指标名 | 描述 | 单位 |
|--------|------|------|
| `get_request_count` | GET类请求数 | Count |
| `put_request_count` | PUT类请求数 | Count |
| `post_request_count` | POST类请求数 | Count |
| `delete_request_count` | DELETE类请求数 | Count |
| `head_request_count` | HEAD类请求数 | Count |

> **⚠️ 注意：OBS无 `request_count` 指标**
>
> CES中不存在名为 `request_count` 的OBS指标。总请求数需通过各类型请求求和：
> `总请求数 = get_request_count + put_request_count + post_request_count + delete_request_count + head_request_count`

详细指标说明参见 [references/obs-metrics.md](references/obs-metrics.md)。

---

## 流量与请求数统计 - 思考过程

> 本节总结了在实际操作中踩过的坑和关键经验，确保后续查询准确无误。

### 1. 必须使用流量指标，禁止使用带宽指标

**问题：** 初次查询时使用了 `download_bytes` / `download_bytes_intranet`，结果算出的流量与控制台相差1000倍（GB vs MB）。

**根因：**
- `download_bytes` 是**带宽指标**（单位 Bytes/s，速率），不是累计流量
- `download_traffic_extranet` / `download_traffic_intranet` 才是**流量指标**（单位 Bytes，累计量）

**正确选择：**

| 用途 | 使用指标 | 单位 | 说明 |
|------|---------|------|------|
| ✅ 查询下载流量 | `download_traffic_extranet` | Bytes | 公网下载累计字节数，直接求和 |
| ✅ 查询下载流量 | `download_traffic_intranet` | Bytes | 内网下载累计字节数，直接求和 |
| ❌ 禁止用于流量统计 | `download_bytes` | Bytes/s | 下载带宽（速率），需乘周期才能换算 |
| ❌ 禁止用于流量统计 | `download_bytes_extranet` / `download_bytes_intranet` | Bytes/s | 带宽指标（速率） |

**同理上传流量：** 使用 `upload_traffic_extranet` / `upload_traffic_intranet`，禁止 `upload_bytes` 系列。

### 2. hcloud CES维度参数格式与SDK/REST API不同

**问题：** 使用 `--dimensions.0.name=bucket_name --dimensions.0.value=xxx` 报错"不正确的参数"。

**根因：** hcloud CES ShowMetricData的维度参数使用 `--dim.N=key,value` 格式，与SDK的 `dimensions` 对象格式不同。

**正确格式：**
```bash
--dim.0=bucket_name,my-bucket
```

**错误格式（SDK格式，hcloud不支持）：**
```bash
--dimensions.0.name=bucket_name --dimensions.0.value=my-bucket
```

### 3. 时间范围必须精确匹配用户表述

**问题：** 用户说"最近一个月"，我按"本月"（自然月）计算，结果与控制台不一致。

**根因：**
- "本月" = 当月1日 ~ 当前时间（自然月，天数不固定）
- "最近一个月" / "最近30天" = 当前时间-30天 ~ 当前时间（滚动30天窗口）
- **华为云OBS控制台默认统计"最近30天"**

**对照表：**

| 用户表述 | 时间范围 | 对照期（月环比） |
|---------|---------|---------|
| "本月" | 当月1日 ~ 当前 | 上月（上个自然月） |
| "最近一个月" / "最近30天" | 当前-30天 ~ 当前 | 前30~60天 |
| 具体日期范围 | 用户指定起止 | 前一个等长周期 |

> **关键原则：** 若用户提到"控制台看到的数据"，应优先考虑使用"最近30天"范围，因为控制台默认统计周期为最近30天。

### 4. OBS无 `request_count` 单一总请求数指标

**问题：** 初次使用 `request_count` 指标查询总请求数。

**根因：** CES中**不存在**名为 `request_count` 的OBS指标。OBS只按请求类型分别上报。

**正确做法：** 分别查询各类型请求数后求和：
```
总请求数 = get_request_count + put_request_count + post_request_count + delete_request_count + head_request_count
```

### 5. CES流量指标返回值直接求和即为总字节数

**确认：** 使用流量指标（`download_traffic_extranet` 等）+ `filter=sum` + `period=86400` 时：
- CES返回每个聚合周期（1天）的 `sum` 值，单位为 Bytes
- 将所有天的 `sum` 值累加，即为总字节数
- 无需额外乘以聚合周期（这与带宽指标不同）

**单位换算：**
```
GB = bytes / (1024³)
MB = bytes / (1024²)
KB = bytes / 1024
```

根据流量大小自适应选择显示单位（< 1GB 显示 MB，< 1MB 显示 KB）。

### 6. hcloud OBS模块无ListAllMyBucketsType命令

**问题：** 运行 `hcloud OBS ListAllMyBucketsType` 提示 `Error: No such command: "ListAllMyBucketsType"`。

**根因：** hcloud CLI（v7.2.2实测）OBS模块**不包含** `ListAllMyBucketsType` 命令。

**解决方案：** 使用obsutil方式列出桶：
```bash
hcloud obs ls
```
通过grep筛选地域：`hcloud obs ls 2>&1 | grep "cn-south-1"`

### 7. CES ShowMetricData不支持--User-Agent参数

**问题：** 运行 `hcloud CES ShowMetricData --User-Agent=xxx` 报错 `[USE_ERROR]不正确的参数:User-Agent`。

**根因：** CES模块的ShowMetricData命令**不支持** `--User-Agent` 参数，该参数仅在OBS模块部分命令中可用。

**正确做法：** CES查询命令**禁止附加** `--User-Agent` 参数。

### 8. 批量查询桶容量优先使用CES容量指标

**问题：** 需查询多个桶的容量排名（如Top 10），逐桶调用GetBucketStorageInfo效率低。

**解决方案：** 通过CES `capacity_total` 指标批量查询：
- 指标：`capacity_total`，单位Bytes
- 聚合方式：`filter=average`（取最新采样值，非sum）
- 返回 `datapoints[-1].average` 即为当前桶容量
- CES容量指标采集周期为30分钟，非实时值，但对排名统计足够准确

---

## 脚本工具

本skill提供以下Python脚本，封装了流量和请求数统计的最佳实践：

### obs_traffic_stats.py — 下载/上传流量统计

```bash
# 最近30天下载流量
python3 scripts/obs_traffic_stats.py --region cn-south-1 --bucket obs-60030508 --period last_30d

# 本月下载+上传流量
python3 scripts/obs_traffic_stats.py --region cn-south-1 --bucket obs-60030508 --period this_month --direction both

# 自定义日期范围
python3 scripts/obs_traffic_stats.py --region cn-south-1 --bucket obs-60030508 --from 2026-04-20 --to 2026-05-20
```

### obs_request_stats.py — 请求总数统计

```bash
# 最近30天请求数
python3 scripts/obs_request_stats.py --region cn-south-1 --bucket obs-60030508 --period last_30d

# 本月请求数（含4xx/5xx错误统计）
python3 scripts/obs_request_stats.py --region cn-south-1 --bucket obs-60030508 --period this_month --include-errors

# 自定义日期范围
python3 scripts/obs_request_stats.py --region cn-south-1 --bucket obs-60030508 --from 2026-04-20 --to 2026-05-20
```

脚本内置关键经验：流量指标vs带宽指标、hcloud维度参数格式、时间范围精确匹配、OBS无request_count单一指标等。

---

## 成功验证

详见 [references/verification-method.md](references/verification-method.md)。

**快速验证：**
```bash
# 检查OBS桶列表（使用obsutil）
hcloud obs ls -limit=1

# 检查obsutil配置
obsutil ls -limit=1

# 验证流量统计脚本
python3 scripts/obs_traffic_stats.py --region cn-south-1 --bucket <BucketName> --period last_30d

# 验证请求统计脚本
python3 scripts/obs_request_stats.py --region cn-south-1 --bucket <BucketName> --period last_30d
```

---

## 参考链接

| 参考文档 | 描述 |
|----------|------|
| [related-apis.md](references/related-apis.md) | API和CLI命令详细说明 |
| [iam-policies.md](references/iam-policies.md) | IAM权限策略 |
| [obs-metrics.md](references/obs-metrics.md) | OBS CES监控指标参考 |
| [verification-method.md](references/verification-method.md) | 验证步骤 |
| [acceptance-criteria.md](references/acceptance-criteria.md) | 正确/错误模式对照 |
| [cli-installation-guide.md](references/cli-installation-guide.md) | CLI安装指南 |
| [troubleshooting.md](references/troubleshooting.md) | 故障排除与实战经验 |
| [obs_traffic_stats.py](scripts/obs_traffic_stats.py) | 流量统计脚本 |
| [obs_request_stats.py](scripts/obs_request_stats.py) | 请求数统计脚本 |
| [OBS产品页](https://www.huaweicloud.com/product/obs.html) | 官方产品页 |
| [OBS API参考](https://support.huaweicloud.com/api-obs/obs_04_0001.html) | 官方API参考 |
| [obsutil文档](https://support.huaweicloud.com/utiltg-obs/obs_11_0001.html) | obsutil命令行工具指南 |
| [CES监控指标参考](https://support.huaweicloud.com/usermanual-ces/ces_03_0065.html) | CES OBS监控指标 |
