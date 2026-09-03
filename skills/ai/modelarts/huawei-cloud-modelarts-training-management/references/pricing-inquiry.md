# BSS 按需询价参考 / BSS On-Demand Pricing Inquiry

> 通过华为云 BSS（运营）API 查询 ModelArts 训练作业的按需价格，在创建训练作业前向用户展示费用并确认。

---

## 概述

在执行 ModelArts 训练作业的**创建**操作前，若使用**公共资源池**（非专属资源池），应先通过 BSS API 查询目标规格的按需价格，向用户展示费用信息并获得确认后再执行操作。

### 适用场景

| 操作 | 是否需要询价 | 说明 |
|------|-------------|------|
| CreateTrainingJob（公共池） | ✅ 是 | 使用公共资源池的作业按 flavor 按需计费 |
| CreateTrainingJob（专属池） | ❌ 否 | 专属资源池已付费，作业不再额外计费 |
| CreateTrainingExperiment | ✅ 是 | 实验可能启动训练作业，需告知潜在费用 |
| CreateSaveImageJob | ❌ 否 | 镜像保存费用极低，通常可忽略 |
| StopTrainingJob | ❌ 否 | 停止作业减少费用 |
| DeleteTrainingJob | ❌ 否 | 删除作业减少费用 |
| 查询类操作 (List/Show) | ❌ 否 | 只读操作不产生费用 |

> ⚠️ **关键判断**：CreateTrainingJob 时，若参数中包含 `pool_id` 或 `spec.pool_id`（指定了专属资源池），则**无需询价**，因为专属资源池已按节点计费。

---

## 询价流程

```
1. 判断是否使用专属资源池  ← 检查 pool_id 参数
2. 若是专属池 → 跳过询价，直接创建
3. 若是公共池 → 获取训练规格 billing code  ← ShowTrainingJobFlavors
4. 获取项目 ID              ← IAM KeystoneListAuthProjects
5. 调用 BSS 按需询价 API     ← BSS ListOnDemandResourceRatings
6. 计算预估费用             ← 单价 × node_count × 预估时长
7. 展示价格给用户            ← 格式化输出
8. 用户确认后执行操作        ← CreateTrainingJob
```

---

## 固定参数

以下参数为 ModelArts 训练作业询价的固定值，无需每次查询：

| 参数 | 值 | 说明 |
|------|-----|------|
| `cloud_service_type` | `hws.service.type.modelarts` | ModelArts 云服务类型编码 |
| `resource_type` | `hws.resource.type.modelarts` | ModelArts 虚拟计算实例资源类型编码 |
| `usage_factor` | `Duration` | 使用量因子：时长 |
| `usage_measure_id` | `4` | 使用量度量单位：小时 |
| `usage_value` | `1` | 查询 1 小时的价格 |
| `size_measure_id` | `14` | 资源容量度量：个（实例数） |
| `resource_size` | `1` | 资源容量：1 个实例 |

> ⚠️ **注意**：`usage_measure_id` 必须为 `4`（小时），不是 `1`（元）。ModelArts 被视为线性产品，`resource_size` 和 `size_measure_id` 为必填。

---

## BSS ListOnDemandResourceRatings API 调用

### 请求参数

```bash
hcloud BSS ListOnDemandResourceRatings --cli-region=cn-north-1 \
  --project_id={project_id} \
  --product_infos.1.id=1 \
  --product_infos.1.cloud_service_type=hws.service.type.modelarts \
  --product_infos.1.resource_type=hws.resource.type.modelarts \
  --product_infos.1.resource_spec={billing_code} \
  --product_infos.1.region={target_region} \
  --product_infos.1.usage_factor=Duration \
  --product_infos.1.usage_measure_id=4 \
  --product_infos.1.usage_value=1 \
  --product_infos.1.subscription_num=1 \
  --product_infos.1.resource_size=1 \
  --product_infos.1.size_measure_id=14
```

### 批量询价

支持一次查询多个规格的价格，使用 `product_infos.1`, `product_infos.2`, ... 索引：

```bash
hcloud BSS ListOnDemandResourceRatings --cli-region=cn-north-1 \
  --project_id={project_id} \
  --product_infos.1.id=1 \
  --product_infos.1.cloud_service_type=hws.service.type.modelarts \
  --product_infos.1.resource_type=hws.resource.type.modelarts \
  --product_infos.1.resource_spec=modelarts.bm.gpu.v100 \
  --product_infos.1.region=cn-north-4 \
  --product_infos.1.usage_factor=Duration \
  --product_infos.1.usage_measure_id=4 \
  --product_infos.1.usage_value=1 \
  --product_infos.1.subscription_num=1 \
  --product_infos.1.resource_size=1 \
  --product_infos.1.size_measure_id=14 \
  --product_infos.2.id=2 \
  --product_infos.2.cloud_service_type=hws.service.type.modelarts \
  --product_infos.2.resource_type=hws.resource.type.modelarts \
  --product_infos.2.resource_spec=modelarts.cpu.8u32g \
  --product_infos.2.region=cn-north-4 \
  --product_infos.2.usage_factor=Duration \
  --product_infos.2.usage_measure_id=4 \
  --product_infos.2.usage_value=1 \
  --product_infos.2.subscription_num=1 \
  --product_infos.2.resource_size=1 \
  --product_infos.2.size_measure_id=14
```

### 响应字段

| 字段 | 说明 |
|------|------|
| `amount` | 总金额（元） |
| `currency` | 币种（CNY） |
| `official_website_amount` | 官网价格 |
| `discount_amount` | 折扣金额 |
| `product_rating_results[].id` | 对应请求中的 `id` |
| `product_rating_results[].amount` | 单个规格价格（元/小时） |

### 响应示例

```json
{
  "amount": 15.82,
  "discount_amount": 0.0,
  "official_website_amount": 15.82,
  "measure_id": 1,
  "currency": "CNY",
  "product_rating_results": [
    {
      "id": "1",
      "amount": 12.52,
      "discount_amount": 0.0,
      "official_website_amount": 12.52,
      "measure_id": 1
    },
    {
      "id": "2",
      "amount": 3.30,
      "discount_amount": 0.0,
      "official_website_amount": 3.30,
      "measure_id": 1
    }
  ]
}
```

---

## 辅助脚本

使用 `scripts/query-pricing.sh` 快速查询价格：

```bash
# 查询单个规格
bash scripts/query-pricing.sh --region cn-north-4 --flavor modelarts.bm.gpu.v100

# 查询多个规格
bash scripts/query-pricing.sh --region cn-north-4 --flavor modelarts.bm.gpu.v100 --flavor modelarts.cpu.8u32g --flavor modelarts.bm.ascend910
```

脚本会自动：
1. 获取目标区域的项目 ID
2. 调用 BSS 询价 API
3. 格式化输出价格表

---

## 获取训练作业规格

### 方法 1: ShowTrainingJobFlavors API

```bash
# 查询 CPU 规格
hcloud ModelArts ShowTrainingJobFlavors --cli-region={region} --flavor_type=CPU

# 查询 GPU 规格
hcloud ModelArts ShowTrainingJobFlavors --cli-region={region} --flavor_type=GPU

# 查询 ASCEND 规格
hcloud ModelArts ShowTrainingJobFlavors --cli-region={region} --flavor_type=ASCEND
```

响应中每个规格包含：
- `flavor_id`：规格 ID（用于创建训练作业的 `flavor_id` 参数）
- `flavor_code`：计费编码（用于 BSS 询价的 `resource_spec`）

### 方法 2: 从训练作业配置中提取

CreateTrainingJob 时，`spec.resource.flavor_id` 参数指定了训练规格。将该值作为 `resource_spec` 传入 BSS 询价 API。

---

## 获取项目 ID

```bash
hcloud IAM KeystoneListAuthProjects --cli-region={region} 2>&1 | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for p in data.get('projects', []):
    if p.get('name') == '{region}':
        print(p.get('id'))
        break
"
```

---

## 费用估算公式

训练作业的费用取决于：

```
总费用 = 规格单价(元/小时) × node_count × 运行时长(小时)
```

| 参数 | 来源 | 说明 |
|------|------|------|
| 规格单价 | BSS 询价结果 | 每个节点的按需价格 |
| node_count | CreateTrainingJob 参数 `spec.resource.node_count` | 训练作业的节点数 |
| 运行时长 | 用户预估 | 训练预计运行的小时数 |

### 估算示例

```
规格: modelarts.bm.gpu.v100
单价: 12.52 元/小时
node_count: 2
预估时长: 10 小时

总费用 = 12.52 × 2 × 10 = 250.40 元
```

---

## 询价后用户确认流程

```
Agent: 检测到 CreateTrainingJob 操作
  ↓
Agent: 检查是否指定了专属资源池 (pool_id)
  ├─ 是 → 跳过询价，专属池已付费，直接创建
  └─ 否 → 继续询价
  ↓
Agent: 从 spec.resource.flavor_id 提取规格
  ↓
Agent: 调用 BSS ListOnDemandResourceRatings 查询价格
  ↓
Agent: 展示价格和费用估算给用户
  ┌──────────────────────────────────────────────────────────────┐
  │ 训练作业费用估算                                             │
  │                                                              │
  │ 规格: modelarts.bm.gpu.v100                                  │
  │ 单价: 12.52 元/小时/节点                                     │
  │ 节点数 (node_count): 2                                       │
  │ 预估时长: 10 小时                                            │
  │                                                              │
  │ 预估总费用: 12.52 × 2 × 10 = 250.40 元                      │
  └──────────────────────────────────────────────────────────────┘
  ↓
User: 确认规格和价格
  ↓
Agent: 执行 CreateTrainingJob
```

---

## 常见问题

### Q: 使用专属资源池的训练作业需要询价吗？

**不需要**。专属资源池已按节点按需计费（或包周期计费），运行在其上的训练作业不再额外收费。只有使用**公共资源池**的训练作业才需要询价。

### Q: 如何判断训练作业使用的是公共池还是专属池？

检查 CreateTrainingJob 的参数：
- 若包含 `spec.resource.pool_id` 或 JSON 中有 `pool_id` 字段 → 专属资源池
- 若不包含 `pool_id` → 公共资源池

### Q: CreateTrainingExperiment 需要询价吗？

**建议询价**。训练实验本身不直接收费，但实验会启动训练作业。应在创建实验前告知用户潜在的计算费用，特别是当实验配置了自动搜索（超参调优）时，可能同时启动多个 trial，费用会成倍增加。

### Q: Auto Search（超参调优）的费用如何估算？

自动搜索会启动多个 trial（试验），每个 trial 都是一个独立的训练作业。费用估算：

```
总费用 = 规格单价 × node_count × 预估时长 × trial 数量
```

### Q: 为什么 usage_measure_id 用 4 而不是 1？

BSS 度量单位中，`1` = 元（货币），`4` = 小时（时长）。ModelArts 按需计费以小时为单位，因此 `usage_measure_id` 必须为 `4`。

### Q: 如何查询包周期（包月/包年）价格？

包周期价格使用 BSS `ListRatingRecords` 或 `ListOnDemandResourceRatings` 配合不同的 `usage_factor` 和周期参数。目前本 skill 仅支持按需询价。
