---
name: huawei-terraform-skill
description: 当任务涉及华为云 Terraform/OpenTofu 时使用。既可生成和评审 IaC，也可通过 Terraform plan/apply 实际执行华为云基础设施任务，并支持与 huawei_skill 联动
version: "1.0.0"
---

# Huawei Terraform Skill

华为云 Terraform 执行型 skill。它是一个自包含 skill，提供 provider 认证、资源模型、依赖发现、示例、排障规则和后续扩展入口，并允许把 Terraform 当成真正的执行介质，而不只是代码模板。

## 什么时候使用

当任务符合以下任一条件时启用本 skill：
- 生成华为云 Terraform / OpenTofu 配置
- 评审或修改 `huaweicloud_*` 资源定义
- 将华为云现网资源整理成可审查的 Terraform
- 为华为云资源编写 Terraform 示例、模块、测试或 CI/CD 配置
- 通过 Terraform `plan` / `apply` 在华为云上创建、变更或销毁基础设施

## 如何与其他 skill 配合

### 与 `huawei_skill` 的关系
- `huawei_skill` 适合做现网查询、账号探测、region/project 校验、候选参数补齐。
- 本 skill 适合把经过确认的依赖和约束沉淀成 Terraform，并继续执行 `plan` / `apply`。
- 如果用户要求“先查现网，再生成 Terraform”或“先查现网，再帮我落地”，优先先走 `huawei_skill`，再进入 Terraform 路线。

## 核心规则

### 1. 不要套用 AWS 资源名和默认建议
- 华为云 Terraform 必须使用 `huaweicloud_*` 资源和 data source。
- 不要输出 `aws_*`、`hashicorp/aws`、S3 backend、AWS Secrets Manager 这类默认答案。
- 模块结构、测试和 CI/CD 也要以本 skill 内定义的华为云规则为准，不要默认依赖其他 skill 补全。

### 2. 默认先发现依赖，再写资源
在华为云上，很多配置是否可用取决于 region、AZ、flavor、image、subnet、security group、磁盘类型等约束。

默认流程：
1. 确认认证方式和 region
2. 确认是复用现网资源，还是创建新资源
3. 通过 data source 或 `huawei_skill` 探测依赖
4. 再生成 `resource` 定义

除非用户明确给出完整且可信的 ID/参数，否则不要硬编码 flavor、image、subnet。

### 3. 同时支持 `HW_*` 和 `HUAWEI_*`
- provider 官方环境变量是 `HW_ACCESS_KEY`、`HW_SECRET_KEY`、`HW_REGION_NAME`
- 项目现有 MCP 侧常用 `HUAWEI_ACCESS_KEY`、`HUAWEI_SECRET_KEY`、`HUAWEI_REGION`
- 文档和生成代码时优先说明 `HW_*`
- 但在分析和联动场景里，需要识别并兼容 `HUAWEI_*`
- 如果两套变量同时存在但值可能冲突，应提醒用户确认实际生效值

### 4. 优先使用已验证的 Full support 资源
当前用户列出的服务都已经进入 `Full support`，并且有经过验证的本地示例。

但真正开始产出代码时，不要平均地看待所有服务，优先顺序仍然是：
- 先从现有 starter examples 出发
- 再用变体指南决定是沿用最小模板还是切到高级变体
- 最后再从 inventory 文档里回查 provider 更宽的能力面

### 5. 默认支持“生成并执行”，不是只停在写代码
- 如果用户目标是“创建”“部署”“落地”“执行变更”“验证能不能跑通”，默认不要停在生成 `.tf`。
- 默认继续执行：
  1. 写入或更新 Terraform 文件
  2. `terraform fmt`
  3. `terraform init`
  4. `terraform plan`
  5. 在任务授权明确时执行 `terraform apply`
- 只有在以下情况才停在代码层：
  - 用户明确说“只生成代码”“不要执行”
  - 当前环境缺少必要凭证或 Terraform 运行条件
  - 任务风险较高且用户未授权真正变更资源

## 默认输出风格
- 优先输出可审查、可复用、可执行的最小可运行配置
- 优先把“发现型 data source”和“创建型 resource”分开写清楚
- 关键 provider 和变量必须包含 docstring/description 级别说明
- 需要时解释为什么用 data source，而不是只给结果

## 默认执行模式

### 代码模式
适用于：
- 用户明确说“只给 Terraform”
- 当前任务本质是评审、重构、示例编写

### 执行模式
适用于：
- 用户说“帮我创建”“帮我部署”“帮我在华为云上落地”
- 用户要求“验证 Terraform 能不能跑通”
- 用户要求“直接通过 Terraform 完成资源创建或变更”

执行模式下，默认把 Terraform 当成实施手段，而不是只把 `.tf` 当交付物。

## 输出文件结构

默认按以下文件拆分输出，不要把所有内容塞进一个 `main.tf`：
- `versions.tf`: Terraform 和 provider 版本约束
- `provider.tf`: provider 配置
- `variables.tf`: 输入变量与说明
- `main.tf`: data source 和 resource 定义
- `outputs.tf`: 关键输出值

如果用户明确要求单文件示例，可以简化；否则默认保持这种结构。

## 常见错误模式

### Agent 必须避免
- 不要硬编码 `flavor_id`、`image_id`、`subnet_id` 这类强依赖 region 或现网状态的值，除非用户已经明确给出可信 ID
- 不要默认把 SSH 或数据库端口开放到 `0.0.0.0/0`
- 不要把真实凭证、数据库密码、KMS Key 直接写进示例代码
- 不要输出 `aws_*` 资源、S3 backend、AWS Secrets Manager 这类跨云默认答案

### 推荐对比

错误示例：

```hcl
resource "huaweicloud_compute_instance" "web" {
  flavor_id = "s6.large.2"
}
```

推荐写法：

```hcl
data "huaweicloud_compute_flavors" "ecs" {
  availability_zone = data.huaweicloud_availability_zones.current.names[0]
  performance_type  = "normal"
  cpu_core_count    = 2
  memory_size       = 4
}

resource "huaweicloud_compute_instance" "web" {
  flavor_id = data.huaweicloud_compute_flavors.ecs.ids[0]
}
```

## 如何开始

当前 `huawei-cloud-solution-ops` 已维护 73 套 Terraform 示例。新增示例进入当前 skill 后，需要继续按当前项目的 hcloud-first、敏感信息和显式 apply 门禁使用；不要直接沿用原独立 skill 的执行入口。

推荐入口：
- 想直接找可运行模板：看 [examples/terraform/README.md](../../examples/terraform/README.md)
- 想知道同一服务有哪些高阶玩法：看 [Advanced Variant Catalog](advanced-variant-catalog.md)
- 想知道该选哪个服务变体：看 [Service Variant Guide](service-variant-guide.md)
- 想知道什么时候该用 data source：看 [Data Source Selection Guide](data-source-selection-guide.md)
- 想全面回查 provider 覆盖面：看三份 inventory 文档

## 当前收尾结论

当前这套 skill 已经可以作为华为云 Terraform 的基础工作底座来使用：
- 已覆盖常见上云基础能力，而不只是单一 ECS 场景
- 已建立统一示例、统一校验脚本、统一排障文档
- 已支持“直接生成 Terraform”“生成并执行 Terraform”“联动 `huawei_skill` 后生成或执行 Terraform”三种路径

如果只是继续补单个资源，不先看整体优先级，后续很容易出现示例越来越多但边界越来越模糊的问题。
后续新增能力前，优先参考路线图文档，确认当前应补“复用型示例”“组合型示例”还是“企业级约束”。

## 广覆盖策略

当前用户列出的服务已经全部升级为 `Full support`。

后续扩展建议改成“先验证价值，再继续做深”：
- 优先补复用型示例
- 优先补组合型业务拓扑
- 优先补企业级约束，而不是继续堆服务名

## 参考资料
- [Provider & Auth](provider-auth.md)
- [Discovery Workflow](discovery-workflow.md)
- [Resource Mapping](resource-mapping.md)
- [Module Blueprints](module-blueprints.md)
- [Advanced Variant Catalog](advanced-variant-catalog.md)
- [Service Variant Guide](service-variant-guide.md)
- [Interop With hcloud](interop-with-hcloud.md)
- [Data Source Selection Guide](data-source-selection-guide.md)
- [Provider Capability Index](inventories/provider-capability-index.md)
- [Reference Example Inventory](inventories/reference-example-inventory.md)
- [Provider Resource Inventory](inventories/provider-resource-inventory.md)
- [Provider Data Source Inventory](inventories/provider-data-source-inventory.md)
- [Troubleshooting](troubleshooting.md)
- [Roadmap](roadmap.md)
