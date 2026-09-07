# Baseline Scenarios

本文件用于验证 `huawei-cloud-solution-ops` 的 Terraform 资产面是否真的让模型在华为云场景下输出正确风格的 Terraform。

## 已有的可执行校验

除了下面这些面向模型行为的基线场景，示例工程还提供了可执行校验脚本：

```bash
examples/validate_examples.sh
```

这个脚本会对示例目录执行：
- `terraform fmt -check -recursive`
- `terraform init -backend=false`
- `terraform validate`

## 场景 1：创建华为云 ECS

用户请求：
“帮我写一个华为云 ECS 的 Terraform，2 核 4G，Ubuntu，复用已有安全组和子网。”

期望行为：
- 输出 `huaweicloud_compute_instance`
- 使用 `huaweicloud_images_image`、`huaweicloud_compute_flavors`
- 使用 `huaweicloud_vpc_subnet`、`huaweicloud_networking_secgroup`
- 不要默认把 SSH 开放到 `0.0.0.0/0`
- 不输出 `aws_instance`

## 场景 2：创建华为云 OBS Bucket

用户请求：
“写一个华为云 OBS bucket 的 Terraform，要私有、开启版本控制和默认加密。”

期望行为：
- 输出 `huaweicloud_obs_bucket`
- 默认 ACL 为 `private`
- 提到 bucket 名全局唯一
- 不输出 `aws_s3_bucket`

## 场景 3：创建华为云 RDS

用户请求：
“帮我写 PostgreSQL 的华为云 RDS Terraform，用已有 VPC、子网和安全组。”

期望行为：
- 输出 `huaweicloud_rds_instance`
- 清楚区分 `vpc_id`、`subnet_id`、`security_group_id`
- 优先使用 `huaweicloud_rds_flavors` 自动发现 flavor，必要时再显式覆盖
- 不套用 AWS RDS 资源名

## 场景 4：联动发现后生成 Terraform

用户请求：
“先帮我查一下当前账号里可用的子网和安全组，再生成 ECS Terraform。”

期望行为：
- 先建议或使用 `hcloud` 发现依赖
- 再生成 Terraform
- 生成代码中优先用 data source 或输入变量承接查询结果

## 场景 5：双变量兼容

用户请求：
“我环境里只有 `HUAWEI_ACCESS_KEY`、`HUAWEI_SECRET_KEY` 和 `HUAWEI_REGION`，帮我生成 Terraform。”

期望行为：
- 能识别这是项目已有变量
- 提醒 provider 官方默认用 `HW_*`
- 给出兼容建议，但不强迫用户统一变量名

## 场景 6：输出结构规范

用户请求：
“直接给我一个华为云 Terraform 模板。”

期望行为：
- 默认拆分为 `versions.tf`、`provider.tf`、`variables.tf`、`main.tf`、`outputs.tf`
- 不把全部配置塞进一个文件，除非用户明确要求单文件示例

## 场景 7：反模式约束

用户请求：
“帮我快速写一个华为云 ECS Terraform，能跑就行。”

期望行为：
- 不硬编码 `aws_*` 资源或 AWS backend
- 不硬编码明显依赖 region 的 flavor ID，除非用户已提供可信值
- 不把真实凭证、数据库密码、KMS Key 直接写进示例代码

## 场景 8：创建华为云 CCE 集群

用户请求：
“帮我写一个华为云 CCE 的 Terraform，新建网络和 EIP，创建一个标准集群。”

期望行为：
- 输出 `huaweicloud_cce_cluster`
- 使用 `huaweicloud_cce_flavor_specifications` 或显式 `cluster_flavor_id`
- 子网显式包含 DNS 配置
- 不一上来就混入节点池、Addon 等额外复杂资源

## 场景 9：创建华为云 CCE 节点池

用户请求：
“帮我写一个华为云 CCE 节点池的 Terraform，自动选节点规格，用已有 key pair。”

期望行为：
- 输出 `huaweicloud_cce_node_pool`
- 使用 `huaweicloud_compute_flavors` 做节点 flavor discovery，必要时再显式覆盖
- 显式写出 `root_volume` 和 `data_volumes`
- 提醒用户确认 key pair 已存在

## 场景 10：创建华为云 ELB 公网入口

用户请求：
“帮我写一个华为云 ELB 的 Terraform，要有公网入口和 HTTP listener。”

期望行为：
- 输出 `huaweicloud_lb_loadbalancer`
- 输出 `huaweicloud_lb_listener` 和 `huaweicloud_lb_pool`
- 公网入口通过 EIP 关联实现
- 不默认混入后端 ECS

## 场景 11：创建华为云 NAT 出网链路

用户请求：
“帮我写一个华为云 NAT Terraform，让私网子网统一出网。”

期望行为：
- 输出 `huaweicloud_nat_gateway`
- 输出 `huaweicloud_nat_snat_rule`
- 输出 `huaweicloud_vpc_eip`
- 清楚区分 subnet 型和 CIDR 型 SNAT

## 场景 12：独立创建公网 EIP

用户请求：
“给我一个华为云 EIP 的 Terraform 模板。”

期望行为：
- 输出 `huaweicloud_vpc_eip`
- 明确带宽配置
- 不把“创建 EIP”和“绑定到目标资源”混为一谈

## 场景 13：创建华为云 NAT DNAT 映射

用户请求：
“帮我写一个华为云 NAT DNAT Terraform，把公网 8080 转发到一台 ECS 的 80 端口。”

期望行为：
- 输出 `huaweicloud_nat_dnat_rule`
- 清楚区分 `external_service_port` 和 `internal_service_port`
- 后端安全组需要显式放行对应端口
- 不默认对全网放开后端端口

## 场景 14：创建华为云 ELB 完整入口链

用户请求：
“帮我写一个华为云 ELB Terraform，要有 listener、backend member 和 health check。”

期望行为：
- 输出 `huaweicloud_lb_member`
- 输出 `huaweicloud_lb_monitor`
- 根据后端协议配置合适的健康检查
- 不把入口层和后端健康检查混成模糊描述
