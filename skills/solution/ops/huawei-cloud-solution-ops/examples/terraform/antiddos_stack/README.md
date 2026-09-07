# Huawei Anti-DDoS Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 EIP
- 一个 SMN Topic
- 一个 SMN Subscription
- 一个 Anti-DDoS Basic 配置

## 设计目标

- 自包含
- 便于评审
- 先覆盖 Anti-DDoS Basic 的最小告警闭环

## 注意事项

- 当前示例会顺带创建 SMN 资源，因为 Anti-DDoS Basic 需要告警主题
- `subscription_endpoint` 和 `subscription_protocol` 需要填写真实可用值
- `bandwidth_name` 和 `bandwidth_size` 在 `share_type = "PER"` 时必填
