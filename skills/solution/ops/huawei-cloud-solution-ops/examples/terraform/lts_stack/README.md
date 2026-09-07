# Huawei LTS Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 LTS Log Group
- 一个 LTS Log Stream

## 设计目标

- 自包含
- 便于评审
- 先覆盖日志组和日志流主链路

## 注意事项

- 当前先覆盖最小日志采集容器，不展开 SQL 告警和日志转储
- 日志保留天数可以分开给 group 和 stream 指定
