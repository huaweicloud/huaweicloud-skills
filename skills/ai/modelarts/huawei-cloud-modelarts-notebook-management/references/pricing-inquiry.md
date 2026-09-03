# BSS 按需询价参考 / BSS On-Demand Pricing Inquiry


> 通过华为云 BSS（运营）API 查询 ModelArts Notebook 实例的按需价格，在创建/启动前向用户展示费用并确认。

---

## 概述

在执行 ModelArts Notebook 的**创建**、**启动**等会产生费用的操作前，应先通过 BSS API 查询目标规格的按需价格，向用户展示费用信息并获得确认后再执行操作。

### 适用场景

| 操作 | 是否需要询价 | 说明 |
|------|-------------|------|
| CreateNotebook | ✅ 是 | 创建实例会产生按需费用 |
| StartNotebook | ✅ 是 | 启动已停止的实例恢复计费 |
| StopNotebook | ❌ 否 | 停止实例暂停计费，无需询价 |
| DeleteNotebook | ❌ 否 | 删除操作减少费用，无需询价 |
| 查询类操作 (List/Show) | ❌ 否 | 只读操作不产生费用 |
| UpdateNotebook | ❌ 否 | 更新元数据不改变规格费用 |
| AttachDynamicStorage | ❌ 否 | 挂载存储不改变实例规格费用 |

---

## 询价流程

```
1. 获取规格 billing code  ← ModelArts ListFlavors（flavor ID 即 billing code）
2. 获取项目 ID            ← IAM KeystoneListAuthProjects
3. 调用 BSS 按需询价 API   ← BSS ListOnDemandResourceRatings
4. 展示价格给用户          ← 格式化输出
5. 用户确认后执行操作      ← CreateNotebook / StartNotebook
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
  --product_infos.1.resource_spec={flavor_id} \
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
  --product_infos.1.resource_spec=modelarts.vm.cpu.2u \
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
  --product_infos.2.resource_spec=modelarts.vm.cpu.8u \
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
  "amount": 10.91,
  "discount_amount": 0.0,
  "official_website_amount": 10.91,
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
    }
  ]
}
```

---

## 辅助脚本

使用 `scripts/query-pricing.sh` 快速查询价格：

```bash
# 查询单个规格
bash scripts/query-pricing.sh cn-north-4 modelarts.vm.cpu.2u

# 查询多个规格
bash scripts/query-pricing.sh cn-north-4 modelarts.vm.cpu.2u modelarts.vm.cpu.8u modelarts.bm.4xlarge.pro
```

脚本会自动：
1. 获取目标区域的项目 ID
2. 调用 BSS 询价 API
3. 格式化输出价格表

---

## 获取规格 billing code

通过 ModelArts ListFlavors API 获取 Notebook 规格列表，`flavorId` 字段即为 BSS 询价所需的 `resource_spec`：

```bash
hcloud ModelArts ListFlavors --cli-region={region}
```

响应中每个规格包含：
- `flavorId`：规格 ID（用于创建 Notebook 的 `--flavor` 参数，同时作为 BSS 询价的 `resource_spec`）
- `flavorType`：规格类型（CPU/GPU/ASCEND）
- `arch`：架构（X86_64/AARCH64）

> **Notebook 与资源池的区别**：Notebook 的 `flavorId` 直接作为 BSS 询价的 `resource_spec`，无需额外的 `billingCode` 字段。

---

## 获取项目 ID

```bash
hcloud IAM KeystoneListAuthProjects --cli-region={region} 2>/dev/null | \
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
Agent: 检测到创建/启动操作
  ↓
Agent: 查询 ListFlavors 获取可用规格
  ↓
Agent: 调用 BSS ListOnDemandResourceRatings 查询价格
  ↓
Agent: 展示价格表给用户
  ┌─────────────────────────────────────────────────────┐
  │ 规格                配置        按需价格(元/小时)    │
  │ modelarts.vm.cpu.2u   2核8Gi    3.50               │
  │ modelarts.vm.cpu.8u   8核32Gi   7.41               │
  │ modelarts.bm.4xlarge.pro  16核64Gi  13.03          │
  └─────────────────────────────────────────────────────┘
  ↓
User: 确认规格和价格
  ↓
Agent: 执行创建/启动操作
```

---

## CreateNotebook 询价流程（必须执行）

> ⚠️ **强制要求**：在调用 `CreateNotebook` 前，**必须**先完成 BSS 询价并向用户展示费用。未询价直接创建属于违规操作。

### 完整流程

```
1. 查询可用规格       ← ModelArts ListFlavors（获取 flavorId 列表）
2. 获取项目 ID        ← IAM KeystoneListAuthProjects
3. 调用 BSS 询价      ← BSS ListOnDemandResourceRatings（查询目标 flavor 按需价格）
4. 展示费用给用户     ← 格式化输出（含规格、单价、月费用估算）
5. 用户确认后执行     ← CreateNotebook
```

### 询价示例

假设用户要创建规格为 `modelarts.vm.cpu.2u` 的 Notebook：

```bash
# Step 1: 查询可用规格
hcloud ModelArts ListFlavors --cli-region=cn-north-4

# Step 2: 获取项目 ID
hcloud IAM KeystoneListAuthProjects --cli-region=cn-north-4 2>/dev/null | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for p in data.get('projects', []):
    if p.get('name') == 'cn-north-4':
        print(p.get('id'))
        break
"

# Step 3: BSS 询价
hcloud BSS ListOnDemandResourceRatings --cli-region=cn-north-1 \
  --project_id={project_id} \
  --product_infos.1.id=1 \
  --product_infos.1.cloud_service_type=hws.service.type.modelarts \
  --product_infos.1.resource_type=hws.resource.type.modelarts \
  --product_infos.1.resource_spec=modelarts.vm.cpu.2u \
  --product_infos.1.region=cn-north-4 \
  --product_infos.1.usage_factor=Duration \
  --product_infos.1.usage_measure_id=4 \
  --product_infos.1.usage_value=1 \
  --product_infos.1.subscription_num=1 \
  --product_infos.1.resource_size=1 \
  --product_infos.1.size_measure_id=14

# Step 4: 展示费用给用户
# ┌──────────────────────────────────────────────────────────────┐
# │ 创建 Notebook 确认                                            │
# │ ──────────────────────────────────────────────────────────── │
# │ 规格:       modelarts.vm.cpu.2u (2核8Gi)                     │
# │ 按需价格:   3.50 元/小时                                     │
# │ 月费用估算: 3.50 × 730 ≈ 2,555 元/月                        │
# │ ──────────────────────────────────────────────────────────── │
# │ 是否确认创建？                                               │
# └──────────────────────────────────────────────────────────────┘

# Step 5: 用户确认后，执行创建
hcloud ModelArts CreateNotebook --cli-region=cn-north-4 \
  --image_id={image_id} \
  --name=my-notebook \
  --flavor=modelarts.vm.cpu.2u \
  --volume.category=OBS \
  --volume.ownership=DEDICATED \
  --volume.uri=obs://{bucket_name}/ \
  --volume.mount_path=/home/ma-user/work/
```

---

## StartNotebook 询价流程

> ⚠️ **强制要求**：在调用 `StartNotebook` 前，**必须**先完成 BSS 询价并向用户展示费用。

### 完整流程

```
1. 查询实例详情       ← ModelArts ShowNotebook（获取当前 flavor）
2. 获取项目 ID        ← IAM KeystoneListAuthProjects
3. 调用 BSS 询价      ← BSS ListOnDemandResourceRatings（查询当前 flavor 按需价格）
4. 展示费用给用户     ← 格式化输出（含规格、单价、月费用估算）
5. 用户确认后执行     ← StartNotebook
```

### 询价示例

```bash
# Step 1: 查询实例详情，获取 flavor
hcloud ModelArts ShowNotebook --cli-region=cn-north-4 --id={instance_id}
# → 从响应中获取 flavor 字段

# Step 2: BSS 询价（使用实例当前 flavor）
hcloud BSS ListOnDemandResourceRatings --cli-region=cn-north-1 \
  --project_id={project_id} \
  --product_infos.1.id=1 \
  --product_infos.1.cloud_service_type=hws.service.type.modelarts \
  --product_infos.1.resource_type=hws.resource.type.modelarts \
  --product_infos.1.resource_spec={flavor_from_instance} \
  --product_infos.1.region=cn-north-4 \
  --product_infos.1.usage_factor=Duration \
  --product_infos.1.usage_measure_id=4 \
  --product_infos.1.usage_value=1 \
  --product_infos.1.subscription_num=1 \
  --product_infos.1.resource_size=1 \
  --product_infos.1.size_measure_id=14

# Step 3: 展示费用给用户
# ┌──────────────────────────────────────────────────────────────┐
# │ 启动 Notebook 确认                                            │
# │ ──────────────────────────────────────────────────────────── │
# │ 实例 ID:    {instance_id}                                    │
# │ 规格:       modelarts.vm.cpu.2u (2核8Gi)                     │
# │ 按需价格:   3.50 元/小时                                     │
# │ 月费用估算: 3.50 × 730 ≈ 2,555 元/月                        │
# │ ──────────────────────────────────────────────────────────── │
# │ 是否确认启动？                                               │
# └──────────────────────────────────────────────────────────────┘

# Step 4: 用户确认后，执行启动
hcloud ModelArts StartNotebook --cli-region=cn-north-4 --id={instance_id}
```

### 费用计算公式

| 项目 | 公式 |
|------|------|
| 单实例小时费用 | BSS 询价返回的 `product_rating_results[].amount` |
| 月费用估算 | 单实例小时费用 × 730 小时 |

---

## 常见问题

### Q: 为什么 BSS API 的 region 用 cn-north-1？

BSS（运营）API 的 endpoint 固定在 `cn-north-1`（华为云运营大区），与目标资源所在 region 无关。目标资源的 region 通过 `product_infos.N.region` 参数指定。

### Q: usage_measure_id 为什么用 4 而不是 1？

BSS 度量单位中，`1` = 元（货币），`4` = 小时（时长）。ModelArts 按需计费以小时为单位，因此 `usage_measure_id` 必须为 `4`。

### Q: 为什么需要 resource_size 和 size_measure_id？

ModelArts 虚拟计算实例在 BSS 中被归类为线性产品，必须指定资源容量。`resource_size=1` 表示 1 个实例，`size_measure_id=14` 表示度量单位为"个"。

### Q: 如何查询包周期（包月/包年）价格？

包周期价格使用 BSS `ListRatingRecords` 或 `ListOnDemandResourceRatings` 配合不同的 `usage_factor` 和周期参数。目前本 skill 仅支持按需询价。

### Q: Notebook 的 flavor ID 和资源池的 billing code 一样吗？

不完全一样。资源池需要通过 `ListResourceFlavors` 获取 `billingCode` 字段；Notebook 的 `flavorId`（通过 `ListFlavors` 获取）直接作为 BSS 询价的 `resource_spec`，无需额外转换。
