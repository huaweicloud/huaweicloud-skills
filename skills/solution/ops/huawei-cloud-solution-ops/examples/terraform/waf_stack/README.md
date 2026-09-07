# Huawei WAF Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 WAF Cloud Instance
- 一个受保护的 WAF Domain

## 设计目标

- 自包含
- 便于评审
- 适合作为 WAF 云模式最小模板

## 注意事项

- 这个示例默认走云模式，不覆盖独享模式
- `origin_servers` 需要按真实源站修改
- 证书可通过 `certificate_id` 或 `certificate_name` 对接现网证书
