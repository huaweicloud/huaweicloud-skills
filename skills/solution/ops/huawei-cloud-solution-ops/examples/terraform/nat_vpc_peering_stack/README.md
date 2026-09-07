# Huawei NAT With VPC Peering Stack Example

这个示例从上游 Terraform 资产库中吸收并改写，用于演示两个 VPC 通过 peering 互联，并由一个 NAT Gateway 提供 SNAT/DNAT 能力。

## 适用场景

- 跨 VPC 出网或中转拓扑原型。
- 同时评审 VPC、peering、NAT、EIP、SNAT、DNAT 和后端 ECS 的依赖。
- 后续改造成复用现网 VPC/NAT/EIP 的组合模板。

## 文件说明

- `versions.tf`: Terraform 和 Huawei Cloud provider 版本约束。
- `provider.tf`: provider 区域配置；认证由环境变量或本地受控配置提供。
- `variables.tf`: VPC、ECS、安全组、NAT、EIP、SNAT/DNAT 参数。
- `main.tf`: 网络、计算和 NAT 资源。
- `terraform.tfvars.example`: 示例变量文件。

## 推荐流程

1. 先用 hcloud 确认目标 region、可用 AZ、ECS 镜像/规格、VPC CIDR 和公网暴露边界。
2. 复制 `terraform.tfvars.example` 为本地 `terraform.tfvars`。
3. 在本地 `terraform.tfvars` 中填写 ECS 管理密码或改造成 key pair 模式，不要提交真实值。
4. 运行 `terraform fmt`、`terraform init`、`terraform validate`、`terraform plan`。
5. 摘要 plan 中 EIP、NAT 计费、公网端口、路由影响和 DNAT 暴露风险。
6. 用户确认 exact plan 后再 apply。
7. apply 后用 hcloud 校验 NAT Gateway、SNAT/DNAT、EIP 绑定、路由和 ECS 连通性。

## 安全边界

- 示例里的公网来源 CIDR 是文档占位，必须替换为真实授权来源。
- 真实 `ecs_admin_password` 只能保存在本地 `terraform.tfvars` 或更安全的本地凭据机制中。
- 不默认把 SSH、HTTP、HTTPS 或 ICMP 暴露给全网。
- 这是组合拓扑示例，不建议直接用于生产网络迁移。
