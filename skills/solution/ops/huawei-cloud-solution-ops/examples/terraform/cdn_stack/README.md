# Huawei CDN Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 CDN Domain

## 设计目标

- 自包含
- 便于评审
- 先覆盖加速域名本体和基础缓存策略

## 注意事项

- 当前先默认 HTTP 回源，不强制启用 HTTPS 证书
- `domain_name` 和 `origin_server` 需要填写真实可用值
- 如果后续要做证书托管或高级规则，可以在此基础上继续扩展
