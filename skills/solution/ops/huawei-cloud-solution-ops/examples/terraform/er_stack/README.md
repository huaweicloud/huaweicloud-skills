# Huawei ER Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 VPC
- 一个 Subnet
- 一个 ER Instance
- 一个 ER VPC Attachment

## 设计目标

- 自包含
- 便于评审
- 默认通过 data source 发现 ER 可用 AZ

## 注意事项

- 当前先覆盖 ER 实例和单个 VPC 连接，不展开 route table 和 flow log
- `asn` 需要和你的网络规划保持一致
