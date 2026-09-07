# Huawei CCE Addon Stack Example

这个示例从上游 Terraform 资产库中吸收并改写，用于给现有 CCE 集群安装或管理 autoscaler addon。

## 适用场景

- 已有 CCE 集群，需要把 autoscaler addon 纳入 Terraform 管理。
- 需要从 addon template 读取默认配置，再补齐 cluster/project 上下文字段。
- 后续扩展到 coredns、everest 等 addon 变体。

## 文件说明

- `versions.tf`: Terraform 和 Huawei Cloud provider 版本约束。
- `provider.tf`: provider 区域配置；认证由环境变量或本地受控配置提供。
- `variables.tf`: 集群定位、addon template 和 project 参数。
- `main.tf`: addon template data source 和 `huaweicloud_cce_addon` 资源。
- `terraform.tfvars.example`: 示例变量文件。

## 推荐流程

1. 先用 hcloud 查询现有 CCE 集群 ID、名称、版本和所在 project。
2. 确认目标集群版本与 `addon_version` 兼容。
3. 复制 `terraform.tfvars.example` 为本地 `terraform.tfvars`，填写 `cluster_id` 或 `cluster_name`。
4. 运行 `terraform fmt`、`terraform init`、`terraform validate`、`terraform plan`。
5. 用户确认 addon 版本和配置 diff 后再 apply。
6. apply 后用 hcloud 或 kubectl 校验 addon 状态、节点伸缩行为和集群事件。

## 安全边界

- 本示例只面向已有 CCE 集群，不创建集群或节点池。
- addon 版本不能猜测，必须来自现网集群版本和 provider/template 查询。
- 不在示例中保存 kubeconfig、token、AK/SK 或集群管理凭据。
