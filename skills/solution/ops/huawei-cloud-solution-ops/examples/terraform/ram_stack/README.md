# Huawei RAM Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 RAM Resource Share

## 设计目标

- 自包含
- 便于评审
- 先覆盖跨账号资源共享本体，不展开资源创建部分

## 注意事项

- `principals` 需要填写真实账号 ID 或组织 ID
- `resource_urns` 需要填写真实的资源 URN
- 这个示例更适合与现网发现或已有资源联动使用
