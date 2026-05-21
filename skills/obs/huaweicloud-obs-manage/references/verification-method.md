# 验证方法 - 华为云OBS对象存储管理

## 目录

- [验证桶列表查询](#验证桶列表查询)
- [验证文件上传](#验证文件上传)
- [验证定时上传](#验证定时上传)
- [验证流量查询](#验证流量查询)
- [验证请求查询](#验证请求查询)
- [端到端验证脚本](#端到端验证脚本)

---

## 验证桶列表查询

### 步骤 1：列出桶

```bash
hcloud OBS ListAllMyBucketsType \
  --region=cn-south-1 \
  --User-Agent HuaweiCloud-Agent-Skills/huaweicloud-obs-manage
```

**预期结果：**
- 返回桶列表，每个桶包含 `Name`、`Location`、`CreationDate`
- 若无桶，返回空列表（正常）

### 步骤 2：查询桶容量和对象数

```bash
hcloud OBS GetBucketStorageInfo \
  --region=cn-south-1 \
  --bucket=<BucketName> \
  --User-Agent HuaweiCloud-Agent-Skills/huaweicloud-obs-manage
```

**预期结果：**
- 返回 `size`（字节）和 `objectNumber`（对象数）
- size >= 0，objectNumber >= 0

### 步骤 3：验证输出格式

```
桶名                容量(GB)    对象数
my-bucket-1         125.3       1024
my-bucket-2         0.5         15
```

**验证项：**
- ✅ 容量以GB为单位，保留1位小数
- ✅ 对象数为整数
- ✅ 所有桶均已查询

---

## 验证文件上传

### 步骤 1：上传测试文件

```bash
# 创建测试文件
echo "test content" > /tmp/obs-upload-test.txt

# 上传
obsutil cp /tmp/obs-upload-test.txt obs://<BucketName>/test/obs-upload-test.txt -flat
```

**预期结果：**
- 返回上传成功信息
- 显示上传文件大小和耗时

### 步骤 2：验证文件已上传

```bash
obsutil ls obs://<BucketName>/test/ -limit=10
```

**预期结果：**
- 列表中包含 `test/obs-upload-test.txt`
- 文件大小与本地文件一致

### 步骤 3：清理测试文件

```bash
# 通过OBS控制台删除测试对象，或通过obsutil手动删除
obsutil rm obs://<BucketName>/test/obs-upload-test.txt -flat
```

> **⚠️ 注意**：此清理步骤为验证流程中的必要操作，非skill功能，需手动执行。

---

## 验证定时上传

### 步骤 1：创建上传脚本

```bash
# 创建测试目录和文件
mkdir -p /tmp/obs-scheduled-test
echo "test $(date)" > /tmp/obs-scheduled-test/test.txt

# 创建上传脚本
cat > $HOME/obs-scheduled-upload-test.sh << 'EOF'
#!/bin/bash
export PATH=/usr/local/bin:$PATH
LOG_FILE="$HOME/obs-scheduled-upload-test.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始定时上传" >> "$LOG_FILE"
obsutil cp /tmp/obs-scheduled-test/ obs://<BucketName>/scheduled-test/ -r -flat >> "$LOG_FILE" 2>&1
EOF
chmod +x $HOME/obs-scheduled-upload-test.sh
```

### 步骤 2：设置crontab（每5分钟执行，仅用于测试）

```bash
(crontab -l 2>/dev/null; echo "*/5 * * * * /bin/bash $HOME/obs-scheduled-upload-test.sh") | crontab -
```

### 步骤 3：验证定时任务

```bash
# 检查crontab
crontab -l

# 等待5分钟后检查日志
sleep 310
cat $HOME/obs-scheduled-upload-test.log

# 检查OBS桶中文件
obsutil ls obs://<BucketName>/scheduled-test/ -limit=10
```

### 步骤 4：清理定时任务

```bash
crontab -l | grep -v "obs-scheduled-upload-test" | crontab -
rm $HOME/obs-scheduled-upload-test.sh $HOME/obs-scheduled-upload-test.log
```

---

## 验证流量查询

### 步骤 1：计算时间范围

```bash
# 本月起始时间戳(ms)
FROM_TS=$(($(date -d "$(date +%Y-%m-01)" +%s) * 1000))
# 当前时间戳(ms)
TO_TS=$(($(date +%s) * 1000))
# 上月起始时间戳(ms)
LAST_MONTH_FROM_TS=$(($(date -d "$(date -d "$(date +%Y-%m-01) -1 month" +%Y-%m-01)" +%s) * 1000))
# 上月截止时间戳(ms)
LAST_MONTH_TO_TS=$(($(date -d "$(date +%Y-%m-01) -1 second" +%s) * 1000))
```

### 步骤 2：查询本月外网下载流量

```bash
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=download_bytes \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=$FROM_TS \
  --to=$TO_TS \
  --User-Agent HuaweiCloud-Agent-Skills/huaweicloud-obs-manage
```

**预期结果：**
- 返回datapoints数组
- 每个datapoint包含timestamp和sum值

### 步骤 3：查询上月外网下载流量

```bash
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=download_bytes \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=$LAST_MONTH_FROM_TS \
  --to=$LAST_MONTH_TO_TS \
  --User-Agent HuaweiCloud-Agent-Skills/huaweicloud-obs-manage
```

### 步骤 4：验证月环比计算

```
月环比 = (本月流量 - 上月流量) / 上月流量 × 100%
```

**验证项：**
- ✅ 流量值以Bytes返回，需转换为GB显示
- ✅ 月环比百分比保留2位小数
- ✅ 上月值为0时特殊处理

---

## 验证请求查询

### 步骤 1：查询本月总请求数

```bash
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=request_count \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=$FROM_TS \
  --to=$TO_TS \
  --User-Agent HuaweiCloud-Agent-Skills/huaweicloud-obs-manage
```

**预期结果：**
- 返回datapoints数组，sum值为请求数

### 步骤 2：查询分类型请求数

```bash
# GET请求数
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=get_request_count \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=$FROM_TS \
  --to=$TO_TS \
  --User-Agent HuaweiCloud-Agent-Skills/huaweicloud-obs-manage

# PUT请求数
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=put_request_count \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=$FROM_TS \
  --to=$TO_TS \
  --User-Agent HuaweiCloud-Agent-Skills/huaweicloud-obs-manage
```

### 步骤 3：验证汇总

**验证项：**
- ✅ request_count >= get_request_count + put_request_count
- ✅ 所有请求数 >= 0
- ✅ 月环比计算正确

---

## 端到端验证脚本

```bash
#!/bin/bash
# OBS管理技能端到端验证脚本

REGION="${1:-cn-south-1}"
BUCKET_NAME="${2}"

if [ -z "$BUCKET_NAME" ]; then
  echo "用法: $0 <region> <bucket_name>"
  exit 1
fi

echo "=========================================="
echo "OBS管理技能端到端验证"
echo "区域: $REGION"
echo "桶名: $BUCKET_NAME"
echo "=========================================="

# 1. 验证hcloud
echo -e "\n[1/6] 验证hcloud版本..."
hcloud version

# 2. 验证obsutil
echo -e "\n[2/6] 验证obsutil版本..."
obsutil version

# 3. 验证桶列表
echo -e "\n[3/6] 验证桶列表查询..."
hcloud OBS ListAllMyBucketsType \
  --region=$REGION \
  --User-Agent HuaweiCloud-Agent-Skills/huaweicloud-obs-manage

# 4. 验证桶容量
echo -e "\n[4/6] 验证桶容量查询..."
hcloud OBS GetBucketStorageInfo \
  --region=$REGION \
  --bucket=$BUCKET_NAME \
  --User-Agent HuaweiCloud-Agent-Skills/huaweicloud-obs-manage

# 5. 验证CES流量指标
FROM_TS=$(($(date -d "$(date +%Y-%m-01)" +%s) * 1000))
TO_TS=$(($(date +%s) * 1000))

echo -e "\n[5/6] 验证CES外网下载流量查询..."
hcloud CES ShowMetricData \
  --region=$REGION \
  --namespace=SYS.OBS \
  --metric_name=download_bytes \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=$BUCKET_NAME \
  --period=86400 \
  --filter=sum \
  --from=$FROM_TS \
  --to=$TO_TS \
  --User-Agent HuaweiCloud-Agent-Skills/huaweicloud-obs-manage

# 6. 验证CES请求指标
echo -e "\n[6/6] 验证CES请求总数查询..."
hcloud CES ShowMetricData \
  --region=$REGION \
  --namespace=SYS.OBS \
  --metric_name=request_count \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=$BUCKET_NAME \
  --period=86400 \
  --filter=sum \
  --from=$FROM_TS \
  --to=$TO_TS \
  --User-Agent HuaweiCloud-Agent-Skills/huaweicloud-obs-manage

echo -e "\n=========================================="
echo "验证完成！"
echo "=========================================="
```

---

## 错误处理

| 错误码 | 描述 | 排障命令 |
|--------|------|---------|
| 403 | 权限不足 | `hcloud configure list` 检查凭证 |
| 404 | 桶不存在 | `obsutil ls -limit=100` 列出桶 |
| 400 | 请求参数错误 | 检查region、桶名等参数 |
| 500 | 服务内部错误 | 稍后重试或联系华为云技术支持 |
| Empty datapoints | CES无数据 | 检查namespace、metric_name、时间范围 |
