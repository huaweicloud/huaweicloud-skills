# Huawei DNS Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 DNS Zone

## 设计目标

- 自包含
- 便于评审
- 适合作为公网或私网 DNS 区域最小模板

## 使用建议

- 公网 zone 直接使用默认示例
- 如果要做私网 zone，把 `zone_type` 改为 `private`，并补 `routers`
