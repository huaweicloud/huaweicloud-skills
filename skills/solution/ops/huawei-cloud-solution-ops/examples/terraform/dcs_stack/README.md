# Huawei DCS Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 VPC
- 一个 Subnet
- 一个 Redis 单机 DCS Instance

## 设计目标

- 自包含
- 便于评审
- 默认通过 data source 发现 flavor 和 AZ

## 注意事项

- 当前先覆盖最小 Redis 单机场景
- 如果要做高可用、数据同步或公网访问，建议在此基础上扩展
- `instance_password` 是敏感变量，推荐通过 `TF_VAR_instance_password` 注入
