# Huawei CBR Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 VPC
- 一个 Subnet
- 一个 Security Group
- 一台用于备份演示的 ECS
- 一个绑定该 ECS 的 CBR Vault

## 设计目标

- 自包含
- 便于评审
- 默认通过 data source 发现 AZ、flavor、image

## 注意事项

- 当前先覆盖服务器备份型 CBR Vault，不展开策略编排和跨资源绑定
- `key_pair_name` 需要引用已存在的密钥对
- 如果 flavor 或 image 在当前 region / AZ 不可用，优先调整过滤条件
