# Huawei Organizations Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 Organizations Account

## 设计目标

- 自包含
- 便于评审
- 先覆盖组织账号创建，不展开组织根、OU 和批量治理流程

## 注意事项

- 这个示例要求当前账号已经开通 Organizations 并具备对应权限
- `email` 必须是未被华为云账号占用的邮箱
- `parent_id` 留空时，默认挂到组织根节点
