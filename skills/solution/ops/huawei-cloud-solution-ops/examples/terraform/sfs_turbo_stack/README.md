# Huawei SFS Turbo Stack Example

这是一个最小可运行的华为云 Terraform 示例，用于创建：
- 一个 VPC
- 一个 Subnet
- 一个 Security Group
- 一个 SFS Turbo 文件系统

## 设计目标

- 自包含
- 便于评审
- 默认通过 data source 发现 AZ

## 注意事项

- 当前先覆盖标准 `NFS` 文件系统，不展开权限规则和 OBS 目标配置
- 如果要使用 `HPC` 类型，需要额外提供 `hpc_bandwidth`
- `charging_mode = "prePaid"` 时，需要同时填写 `period_unit` 和 `period`
