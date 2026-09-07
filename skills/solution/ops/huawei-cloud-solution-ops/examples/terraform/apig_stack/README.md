# Huawei APIG Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 VPC
- 一个 Subnet
- 一个 Security Group
- 一个 APIG Instance
- 一个 Proxy Cache Plugin

## 设计目标

- 自包含
- 便于评审
- 适合作为 APIG 最小平台模板

## 注意事项

- 当前先覆盖实例和插件，不直接展开 API、环境、发布和后端通道
- 如果要做完整 API 发布链路，建议在此基础上继续扩展
