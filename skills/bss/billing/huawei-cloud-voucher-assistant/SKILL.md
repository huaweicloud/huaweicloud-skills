---
name: huawei-cloud-voucher-assistant
description: |
  Invoke this skill when a user is purchasing a Huawei Cloud (华为云) service and wants to know what coupons (代金券), discounts, or savings options are available. Reads the account's coupons via AK/SK and presents applicable voucher deductions; when the balance is insufficient, recommends lower-spec alternatives or voucher+cash combos. Triggers include: "购买云服务", "下单", "选购", "买一台", "续费", "有什么优惠", "优惠方案", "代金券", "优惠券", "折扣", "代金券余额", "抵扣", "省钱", "代金券适不适用", "能抵多少", "够不够抵", "代金券怎么用", "任务列表", "成长中心任务", "推荐任务", "任务推荐", "buy Huawei Cloud", "coupon", "discount", "voucher balance", "purchase ECS/OBS/RDS".
---

> [!IMPORTANT]
> 本 Skill 是华为云「代金券」的**购买优惠咨询助手**。用户在购买华为云服务、想了解有哪些优惠时，本 Skill 通过已授权的华为云账号权限（AK/SK）读取代金券余额与明细，给出可抵扣方案；余额不足时推荐低规格替代与「代金券+现金」组合。它**不直接下单购买**（下单由对应服务 Skill 负责），也不查询账单/用量明细（那是 `huawei-cloud-billing-scout` 的职责）。

# Overview

华为云代金券助手：用户在购买华为云服务、想了解优惠时，读取「代金券」余额与明细，给出可抵扣金额；余额不足时推荐低规格与组合付款方案。

## Scenario Description

本 Skill 的定位是**购买时的优惠方案咨询**：

- **优惠查询**：用户购买华为云服务时，查询有哪些代金券/折扣可抵扣
- **余额不足推荐**：余额不足以全额抵扣时，推荐低规格服务或「代金券+现金」组合

### Use Cases

- "我要买一台 ECS，有没有代金券能用？"
- "有什么优惠方案？代金券能抵多少？"
- "我的华为云代金券还剩多少？"
- "这个代金券能在哪些云服务上用？"
- "余额不够买这台 ECS 怎么办？"
- "我要买一台 c7.large.2，代金券够不够抵？不够的话推荐什么方案？"

## Prerequisites

- **Python 3.6+**（`python` 或 `python3` 在 `PATH` 中），纯标准库，零第三方依赖
- **网络访问**：`bss.myhuaweicloud.com`（BSS）+ `devdata.huaweicloud.com`（成长中心 fwdo 任务列表）
- **华为云 AK/SK**：环境变量 `HW_ACCESS_KEY`/`HW_SECRET_KEY` 或 `HUAWEICLOUD_SDK_AK`/`HUAWEICLOUD_SDK_SK`
- **HW_DOMAIN_ID**（可选）：租户 ID（BSS 全局服务需 X-Domain-Id 头参与签名）
- 任务列表（fwdo 匿名）零配置可用；代金券查询需 AK/SK，未配置时返回提示。分析类 action 始终可离线运行（见 [Data Source](#data-source)）
- **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
  - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

> All `hcloud` commands in this skill are wrapped with `skill-quality-cli run` for telemetry. No manual action required.

## Data Source

> **双数据源，自动选择**：
> 1. **BSS 开放 API**（AK/SK 签名）：已有代金券账户余额/明细。
> 2. **成长中心前端 API（fwdo 匿名）**：公开任务列表（零配置，无需 Cookie/CSRF/appcode）。
> 底层客户端：`scripts/data/bss_client.py`（BSS）、`scripts/data/hdcommunity_client.py`（fwdo）。

数据读取通过**可替换 Adapter** 实现，统一接口定义在 [scripts/data/](scripts/data/)。
- 代金券：`coupon_api.py` `get_adapter()` —— 有 AK/SK → BSS；否则 → None。
- 任务列表：`growth_api.py` `get_adapter()` —— fwdo 匿名，始终可用。

| Adapter | 职责 | 认证 | 状态 |
|---------|------|------|------|
| `coupon_api.py` `BssCouponAdapter` | 已有代金券账户余额/明细 | AK/SK + X-Domain-Id（SDK-HMAC-SHA256 签名） | ✅ 已接入 |
| `growth_api.py` `HdgrowthWebAdapter` | 成长中心公开任务列表 | 无（fwdo 匿名） | ✅ 已接入 |

**配置**（环境变量）：

| 环境变量 | 说明 | 必填 |
|----------|------|:----:|
| `HW_ACCESS_KEY` / `HW_SECRET_KEY` | 华为云 AK/SK（BSS 代金券查询） | 否 |
| `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` | 同上（备选环境变量名） | 否 |
| `HW_DOMAIN_ID` | 租户 ID（BSS 全局服务需 X-Domain-Id 头参与签名） | 否 |
| `HDGROW_WEB_BASE` | 成长中心 web 域名，默认 `https://devdata.huaweicloud.com` | 否 |

> BSS 代金券查询（`GET /v2/promotions/benefits/coupons`）用 SDK-HMAC-SHA256 签名 + X-Domain-Id 头，AK/SK 从环境变量读取。
> 代金券抵扣需 BSS 订单系统（订单创建时指定 coupon_id）。
> 代金券适用服务列表由本地知识库 [references/voucher-taxonomy.md](references/voucher-taxonomy.md) 提供。
> fwdo 匿名任务列表仅含公开字段（不含个人完成状态）；积分余额需 fwdu 登录态，本 skill 不提供。

`scripts/analyzer.py`（分析层）与上表**解耦**，仅依赖结构化输入，可离线运行与单测。

## Core Workflow and Core Commands

主入口 `scripts/voucher_assistant.py` 按 action 分发，action 命名遵循 `huawei_<service>_<action>`（snake_case）。

### 查询类（R3，只读自动执行）

```bash
python scripts/voucher_assistant.py list_vouchers
python scripts/voucher_assistant.py list_tasks
python scripts/voucher_assistant.py recommend_tasks
python scripts/voucher_assistant.py list_voucher_applicable_services
```

### 分析类（R3，只读自动执行，无需数据源即可运行本地逻辑）

```bash
python scripts/voucher_assistant.py analyze_voucher_coverage --balance 100 --price 80
python scripts/voucher_assistant.py recommend_discount_plan --balance 50 --price 80 --alt "ecs:c7.large.2:40"
```

### 管理类（R2，预览 + 确认，依赖数据源接入）

```bash
python scripts/voucher_assistant.py apply_voucher --order-ref <ref> --amount <amt> --confirm
```

> 管理类 action 在**未接入数据源**或**未带 `--confirm`** 时，只输出预览方案，不执行任何真实变更。

## Action Reference

| Action | 分级 | 说明 |
|--------|:----:|------|
| `huawei_list_vouchers` | R3 | 代金券余额 + 明细（面额/有效期/状态） |
| `huawei_list_tasks` | R3 | 成长中心公开任务列表（fwdo 匿名，零配置，含周期类型） |
| `huawei_recommend_tasks` | R3 | 根据任务列表按积分收益推荐值得优先做的任务 |
| `huawei_list_voucher_applicable_services` | R3 | 代金券适用云服务 + 抵扣规则 |
| `huawei_analyze_voucher_coverage` | R3 | 判断余额是否够买目标服务（充足/部分/不足） |
| `huawei_recommend_discount_plan` | R3 | 余额不足时推荐低规格 / 组合付款方案 |
| `huawei_apply_voucher` | R2 | 购买时代金券抵用（预览 + 确认，需 BSS 订单系统） |

## Decision Flow

```
购买华为云服务时 → 主动提醒 + 抵扣闭环
   ┌─────────────────────────────────────────────────────┐
   │ 读取代金券余额 (list_vouchers)                       │
   │ ├─ 有可用代金券 → 计算覆盖 → 提醒抵扣 → apply_voucher │
   │ │                             ⚠️ 需 BSS/订单        │
   │ └─ 余额不足 → ① 推荐低规格 ② 现金组合               │
   │              (recommend_discount_plan)               │
   └─────────────────────────────────────────────────────┘
```

## Parameters

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `action` | ✅ | 上述 action 名（不含 `huawei_` 前缀） |
| `--balance` | 分析类 | 代金券余额（`analyze_voucher_coverage`/`recommend_discount_plan`，数据源未接入时手动传入） |
| `--price` | 分析类 | 目标价格（同上两个分析类 action，必填） |
| `--alt` | 分析类 | 低规格替代 `service:spec:price`，可多次（`recommend_discount_plan`） |
| `--order-ref` | 抵扣类 | 订单/购买引用（`apply_voucher`） |
| `--amount` | 抵扣类 | 抵扣金额 |
| `--confirm` | 管理类 | 显式确认才执行抵扣，缺省仅预览 |
| `--top-n` | 推荐类 | 推荐任务返回数量（`recommend_tasks`，默认 5） |

## Reference Documentation

| Document | Description |
|----------|-------------|
| [references/voucher-taxonomy.md](references/voucher-taxonomy.md) | 代金券规则/适用服务/抵扣规则知识库（本地离线） |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | 验收标准 |
| [references/iam-policies.md](references/iam-policies.md) | IAM 权限说明 |
| [references/verification-method.md](references/verification-method.md) | 验证方法 |

## Notes

- 本 Skill 是**辅助决策器**，不直接下单；下单由对应服务 Skill 完成。
- 抵扣必须显式确认（`--confirm`），且金额需二次校验、不得超余额。
- 数据源：① BSS（AK/SK）查代金券余额/明细；② fwdo 匿名查成长中心公开任务列表（零配置）。未配置 AK/SK 时代金券查询返回配置提示，任务列表始终可用。代金券抵扣需 BSS 订单系统。
- 代金券适用服务列表由 `references/voucher-taxonomy.md` 本地知识库提供（BSS 不直接提供该字段）。
- fwdo 匿名任务列表仅含公开字段（不含个人完成状态/积分余额）；任务周期类型：LIMIT（仅一次）/ DAILY / WEEKLY / MONTHLY。