# Huawei VPC Security Group Stack Example

这个示例从上游 Terraform 资产库中吸收并改写，用于创建一个独立安全组和一组可审查的安全组规则。

## 适用场景

- 单独管理安全组规则。
- 给后续 ECS、ELB、RDS、CCE 节点池等资源复用安全组。
- 将安全组规则从临时命令沉淀成可 review 的 IaC。

## 文件说明

- `versions.tf`: Terraform 和 Huawei Cloud provider 版本约束。
- `provider.tf`: provider 区域配置；认证由环境变量或本地受控配置提供。
- `variables.tf`: 安全组和规则变量。
- `main.tf`: 安全组与规则资源。
- `terraform.tfvars.example`: 示例变量文件，复制为本地 `terraform.tfvars` 后再改。

## 推荐流程

1. 先用 hcloud 查询现网 VPC、已有安全组和真实授权来源 CIDR。
2. 复制 `terraform.tfvars.example` 为本地 `terraform.tfvars`，把 `203.0.113.10/32` 替换为真实批准来源。
3. 运行 `terraform fmt`、`terraform init`、`terraform validate`、`terraform plan`。
4. 摘要 plan 中新增/修改的规则，用户确认后再 apply。
5. apply 后用 hcloud readback 校验安全组规则，并继续做业务连通性验证。

## 安全边界

- 示例不包含 AK/SK、token、密码或私钥。
- 不提交真实 `terraform.tfvars`。
- 不默认开放 SSH、数据库或管理端口到 `0.0.0.0/0`。
- 出站规则可以按业务需要放宽；入站规则必须按来源 CIDR、端口和协议逐条确认。
