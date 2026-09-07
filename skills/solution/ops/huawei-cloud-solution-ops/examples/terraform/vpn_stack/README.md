# Huawei VPN Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 VPC
- 一个 Subnet
- 两个 EIP
- 一个 VPN Gateway

## 设计目标

- 自包含
- 便于评审
- 默认通过 data source 发现 VPN Gateway 可用 AZ

## 注意事项

- 当前先覆盖 VPN Gateway 本体，不展开连接、对端网关和用户管理
- VPN Gateway 需要两条公网链路，因此会创建两个 EIP
- flavor 和 attachment type 会影响可用区返回结果
