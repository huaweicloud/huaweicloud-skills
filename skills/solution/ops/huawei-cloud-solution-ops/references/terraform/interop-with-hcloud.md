# Interop With hcloud

本文件定义 Terraform 资产与 `huawei-cloud-solution-ops` / `hcloud` 主链路的协作边界。

## 什么时候联动

以下情况建议联动：
- 用户说“先看下我当前账号里有什么，再帮我写 Terraform”
- 用户说“先看下现网，再直接帮我用 Terraform 落地”
- 用户只给了资源名，没有 ID
- 需要判断复用现网资源还是新建资源
- region、project、subnet、security group、image、flavor 不明确
- 之前 API 创建报过错，希望沉淀成更稳的 Terraform

## 推荐联动流程

### 场景 1：复用现网网络资源创建 ECS
1. 用 `hcloud` 查询候选 VPC / subnet / security group
2. 确认最终要复用的资源 ID
3. Terraform 中优先用变量承接这些 ID
4. 若需要在代码里再次校验，可补 `data "huaweicloud_vpc_subnet"` / `data "huaweicloud_networking_secgroup"`
5. 如果用户目标是直接创建资源，继续执行 Terraform `plan` / `apply`

### 场景 2：根据现网成功样板生成 Terraform
1. 用 `hcloud` 查询已有 ECS 成功样板
2. 提取关键信息：
   - region
   - availability zone
   - flavor
   - image
   - subnet
   - security group
3. 把这些信息转成 Terraform 输入变量或 data source 条件
4. 输出可审查的 Terraform，而不是只给口头建议
5. 在任务授权明确时，继续执行 Terraform，而不是停在代码生成

### 场景 3：RDS / OBS 复用现网依赖
1. 用 `hcloud` 确认 VPC、subnet、security group、KMS 等依赖
2. 再产出 `huaweicloud_rds_instance` 或 `huaweicloud_obs_bucket`
3. 若用户目标是落地执行，则继续走 Terraform 执行链路

## 代码生成规则

### 已知 ID 时
优先输出变量：

```hcl
variable "subnet_id" {
  description = "Existing subnet ID discovered from Huawei Cloud."
  type        = string
}
```

然后在代码里引用：

```hcl
data "huaweicloud_vpc_subnet" "selected" {
  id = var.subnet_id
}
```

### 仅知道名称时
- 不要直接假设名称唯一
- 先建议或执行现网查询
- 如果仍要写 Terraform，优先把名称保留为输入变量，并注明该名称需要保证唯一

## 不建议联动的场景

以下情况可以直接用 Terraform 路线：
- 用户已经给了完整、可信的资源 ID
- 用户明确要“从零创建一套新环境”
- 用户只要一个示例或模块模板，不关心现网

## 常见错误边界

- `huawei-cloud-solution-ops` / `hcloud` 负责现网真相、只读验证和后置验收
- Terraform 资产负责 IaC 结构化表达、plan、apply 和 drift review

不要让 Terraform 生成阶段承担“猜测现网资源”的职责。
