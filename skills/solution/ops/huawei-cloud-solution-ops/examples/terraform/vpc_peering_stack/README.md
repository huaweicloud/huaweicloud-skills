# Huawei VPC Peering Stack Example

这个示例从上游 Terraform 资产库中吸收并改写，用于创建两个 VPC、对应 subnet、VPC peering connection 和双向路由。

## 适用场景

- 新建两个测试 VPC 并建立互联。
- 演示 VPC peering 的资源依赖和路由闭环。
- 后续改造成“复用现网 VPC 后补 peering”的模板。

## 文件说明

- `versions.tf`: Terraform 和 Huawei Cloud provider 版本约束。
- `provider.tf`: provider 区域配置；认证由环境变量或本地受控配置提供。
- `variables.tf`: 两个 VPC/subnet 和 peering 名称。
- `main.tf`: VPC、subnet、peering connection 和路由资源。
- `terraform.tfvars.example`: 示例变量文件。

## 推荐流程

1. 如果目标是复用现网 VPC，先用 hcloud 查询 VPC、subnet、CIDR 和路由表。
2. 确认两个 VPC CIDR 不重叠。
3. 复制 `terraform.tfvars.example` 为本地 `terraform.tfvars` 并调整 CIDR。
4. 运行 `terraform fmt`、`terraform init`、`terraform validate`、`terraform plan`。
5. 用户确认 exact plan 后再 apply。
6. apply 后用 hcloud 查询 peering 状态和两侧路由，并做跨 VPC 连通性验证。

## 安全边界

- 本示例默认创建新 VPC，不自动接管生产现网 VPC。
- 复用现网资源前必须先做 hcloud 发现和路由影响评估。
- 不自动 destroy；删除 peering 前必须确认两侧依赖。
