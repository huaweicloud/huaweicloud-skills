# Huawei SMS Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 SMS Migration Project

## 设计目标

- 自包含
- 便于评审
- 先覆盖迁移项目本体，不展开任务和模板编排

## 注意事项

- `migration_project_region` 是迁移目标区域，可能和 provider region 不同
- 当前示例不自动创建源端和目标端服务器，只负责迁移项目定义
- 迁移项目参数通常与迁移策略强相关，建议先由用户确认
