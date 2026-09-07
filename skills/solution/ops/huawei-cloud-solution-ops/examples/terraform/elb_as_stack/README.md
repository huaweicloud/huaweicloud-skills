# Huawei ELB With Auto Scaling Stack Example

这个示例从上游 Terraform 资产库中吸收并改写，用于创建独享型 ELB、监听器、后端池、AS 配置、AS 组和 CES 触发的伸缩策略。

## 适用场景

- 需要一个可 review 的弹性 Web 入口拓扑。
- 需要把 ELB、AS、CES 告警和 EIP 关联到一个组合示例里。
- 后续改造成复用现网 VPC/ELB 或复用现网镜像/规格的生产模板。

## 文件说明

- `versions.tf`: Terraform 和 Huawei Cloud provider 版本约束。
- `provider.tf`: provider 区域配置；认证由环境变量或本地受控配置提供。
- `variables.tf`: VPC、ELB、EIP、ECS/AS、CES 告警和伸缩策略参数。
- `main.tf`: 独享 ELB、AS、CES 及相关资源。
- `terraform.tfvars.example`: 示例变量文件。

## 推荐流程

1. 先用 hcloud 查询 region/AZ、ELB flavor、ECS 镜像/规格和现网安全边界。
2. 复制 `terraform.tfvars.example` 为本地 `terraform.tfvars`。
3. 根据真实应用修改 `configuration_user_data`，不要写入密码、token 或私钥。
4. 运行 `terraform fmt`、`terraform init`、`terraform validate`、`terraform plan`。
5. 摘要 plan 中 ELB/EIP 计费、AS 初始实例数、伸缩阈值、健康检查和替换风险。
6. 用户确认 exact plan 后再 apply。
7. apply 后用 hcloud 校验 ELB、listener、pool、AS group、CES alarm 和后端健康状态。

## 安全边界

- `user_data` 只能放无敏感信息的启动脚本。
- 不默认把管理端口暴露给公网。
- AS 组容量、删除实例策略和 EIP 计费要在 apply 前明确确认。
