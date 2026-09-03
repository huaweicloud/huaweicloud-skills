# BSS 按需询价参考 / BSS On-Demand Pricing Inquiry

> 通过华为云 BSS（运营）API 查询 ModelArts 专属资源池节点的按需价格，在创建/扩容前向用户展示费用并确认。

---

## 概述

在执行 ModelArts 资源池的**创建**、**扩容**（新增节点池或扩容节点池）等会产生费用的操作前，应先通过 BSS API 查询目标规格的按需价格，向用户展示费用信息并获得确认后再执行操作。

### 适用场景

| 操作 | 是否需要询价 | 说明 |
|------|-------------|------|
| CreatePool | ✅ 是 | 创建资源池本身不收费，但需告知用户后续节点费用 |
| CreateNodePool | ✅ 是 | 新增节点池会产生按需费用 |
| PatchNodePool (扩容) | ✅ 是 | 扩容节点数量会增加费用 |
| BatchResizePoolNodes | ✅ 是 | 变更规格会改变费用 |
| DeletePool / DeleteNodePool | ❌ 否 | 删除操作减少费用，无需询价 |
| 查询类操作 (List/Show) | ❌ 否 | 只读操作不产生费用 |

---

## 询价流程

```
1. 获取规格 billing code  ← ModelArts ListResourceFlavors
2. 获取项目 ID            ← IAM KeystoneListAuthProjects
3. 调用 BSS 按需询价 API   ← BSS ListOnDemandResourceRatings
4. 展示价格给用户          ← 格式化输出
5. 用户确认后执行操作      ← CreatePool / CreateNodePool / PatchNodePool / BatchResizePoolNodes
```

---

## 固定参数

以下参数为 ModelArts 询价的固定值，无需每次查询：

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
  --product_infos.1.resource_spec=modelarts.vm.cpu.8ud \
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
  --product_infos.2.resource_spec=modelarts.vm.cpu.16u64g.d \
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
  "amount": 23.94,
  "discount_amount": 0.0,
  "official_website_amount": 23.94,
  "measure_id": 1,
  "currency": "CNY",
  "product_rating_results": [
    {
      "id": "1",
      "amount": 3.5,
      "discount_amount": 0.0,
      "official_website_amount": 3.5,
      "measure_id": 1
    },
    {
      "id": "2",
      "amount": 7.41,
      "discount_amount": 0.0,
      "official_website_amount": 7.41,
      "measure_id": 1
    },
    {
      "id": "3",
      "amount": 13.03,
      "discount_amount": 0.0,
      "official_website_amount": 13.03,
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
bash scripts/query-pricing.sh --region cn-north-4 --billing modelarts.vm.cpu.8ud

# 查询多个规格
bash scripts/query-pricing.sh --region cn-north-4 --billing modelarts.vm.cpu.8ud --billing modelarts.vm.cpu.16u64g.d --billing modelarts.vm.cpu.48u96g.d
```

脚本会自动：
1. 获取目标区域的项目 ID
2. 调用 BSS 询价 API
3. 格式化输出价格表

---

## 获取规格 billing code

通过 ModelArts ListResourceFlavors API 获取规格列表，每个规格的 `billingCode` 字段即为 BSS 询价所需的 `resource_spec`：

```bash
hcloud ModelArts ListResourceFlavors --cli-region={region}
```

响应中每个规格包含：
- `flavorId`：规格 ID（用于创建资源池/节点池）
- `billingCode`：计费编码（用于 BSS 询价的 `resource_spec`）
- `billingModes`：支持的计费模式（`[0]` = 按需，`[1]` = 包周期）

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

## 询价后用户确认流程

```
Agent: 检测到创建/扩容操作
  ↓
Agent: 查询 ListResourceFlavors 获取可用规格
  ↓
Agent: 调用 BSS ListOnDemandResourceRatings 查询价格
  ↓
Agent: 展示价格表给用户
  ┌─────────────────────────────────────────────────────┐
  │ 规格                配置        按需价格(元/小时)    │
  │ modelarts.vm.cpu.8ud  8核32Gi   3.50               │
  │ modelarts.vm.cpu.16u64g.d  16核64Gi  7.41          │
  │ modelarts.vm.cpu.48u96g.d  48核96Gi  13.03         │
  └─────────────────────────────────────────────────────┘
  ↓
User: 确认规格和价格
  ↓
Agent: 执行创建/扩容操作
```

---

## PatchNodePool 扩容询价流程（必须执行）

> ⚠️ **强制要求**：在调用 `PatchNodePool` 增加 `spec.resources.count` 前，**必须**先完成 BSS 询价并向用户展示费用。未询价直接扩容属于违规操作。

### 扩容场景识别

当 `PatchNodePool` 的 `--spec.resources.count` 值**大于**当前节点池的 `count` 时，即为扩容操作，新增节点会产生按需费用。

### 完整流程

```
1. 查询当前节点池    ← ListNodePools / ShowNodePool（获取当前 count 和 flavor）
2. 计算新增节点数    ← new_count - current_count
3. 获取规格 billing code ← ModelArts ListResourceFlavors（用 flavorId 匹配 billingCode）
4. 调用 BSS 询价     ← BSS ListOnDemandResourceRatings（查询单节点按需价格）
5. 计算扩容费用      ← 单节点价格 × 新增节点数
6. 展示费用给用户    ← 格式化输出（含新增节点数、单价、月费用估算）
7. 用户确认后执行    ← PatchNodePool
```

### 询价示例

假设当前节点池有 1 个节点，用户要求扩容到 2 个节点（新增 1 个节点），规格为 `modelarts.vm.cpu.16u64g.d`：

```bash
# Step 1: 查询当前节点池，确认当前 count=1
hcloud ModelArts ShowNodePool --cli-region=cn-north-4 \
  --pool_name={pool_name} --nodepool_name={nodepool_name}

# Step 2: 获取 billing code
hcloud ModelArts ListResourceFlavors --cli-region=cn-north-4
# → 找到 flavorId=modelarts.vm.cpu.16u64g.d 对应的 billingCode

# Step 3: BSS 询价（查询单节点每小时价格）
hcloud BSS ListOnDemandResourceRatings --cli-region=cn-north-1 \
  --project_id={project_id} \
  --product_infos.1.id=1 \
  --product_infos.1.cloud_service_type=hws.service.type.modelarts \
  --product_infos.1.resource_type=hws.resource.type.modelarts \
  --product_infos.1.resource_spec={billing_code} \
  --product_infos.1.region=cn-north-4 \
  --product_infos.1.usage_factor=Duration \
  --product_infos.1.usage_measure_id=4 \
  --product_infos.1.usage_value=1 \
  --product_infos.1.subscription_num=1 \
  --product_infos.1.resource_size=1 \
  --product_infos.1.size_measure_id=14

# Step 4: 展示费用给用户
# ┌──────────────────────────────────────────────────────────────┐
# │ 扩容确认                                                      │
# │ ──────────────────────────────────────────────────────────── │
# │ 资源池:     {pool_name}                                      │
# │ 节点池:     {nodepool_name}                                  │
# │ 规格:       modelarts.vm.cpu.16u64g.d (16核64Gi)             │
# │ 当前节点数: 1                                                │
# │ 目标节点数: 2                                                │
# │ 新增节点数: 1                                                │
# │ 单节点价格: 7.41 元/小时                                     │
# │ 新增费用:   7.41 元/小时 (≈ 5,335 元/月)                    │
# │ ──────────────────────────────────────────────────────────── │
# │ 是否确认扩容？                                               │
# └──────────────────────────────────────────────────────────────┘

# Step 5: 用户确认后，执行扩容
hcloud ModelArts PatchNodePool --cli-region=cn-north-4 \
  --pool_name={pool_name} \
  --nodepool_name={nodepool_name} \
  --spec.resources.count=2 \
  --spec.resources.flavor=modelarts.vm.cpu.16u64g.d \
  --spec.resources.maxCount=2
```

### 费用计算公式

| 项目 | 公式 |
|------|------|
| 单节点小时费用 | BSS 询价返回的 `product_rating_results[].amount` |
| 新增节点数 | `new_count - current_count` |
| 扩容小时费用 | 单节点小时费用 × 新增节点数 |
| 月费用估算 | 扩容小时费用 × 730 小时 |

> **注意**：缩容（count 减小）不产生新费用，无需询价，但仍需用户确认。

---

## 常见问题

### Q: CreateOrderId API 能否用于创建前询价？

**不能**。`CreateOrderId` 仅对已存在的资源池生成订单，不能用于创建前的价格查询。必须使用 BSS `ListOnDemandResourceRatings` API。

### Q: 为什么 usage_measure_id 用 4 而不是 1？

BSS 度量单位中，`1` = 元（货币），`4` = 小时（时长）。ModelArts 按需计费以小时为单位，因此 `usage_measure_id` 必须为 `4`。

### Q: 为什么需要 resource_size 和 size_measure_id？

ModelArts 虚拟计算实例在 BSS 中被归类为线性产品，必须指定资源容量。`resource_size=1` 表示 1 个实例，`size_measure_id=14` 表示度量单位为"个"。

### Q: 如何查询包周期（包月/包年）价格？

包周期价格使用 BSS `ListRatingRecords` 或 `ListOnDemandResourceRatings` 配合不同的 `usage_factor` 和周期参数。目前本 skill 仅支持按需询价。
