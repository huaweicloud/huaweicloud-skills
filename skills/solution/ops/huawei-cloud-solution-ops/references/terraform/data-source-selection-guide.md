# Data Source Selection Guide

这份文档用于补齐“什么时候该用哪个 data source”的规则。

很多 Terraform 代码不是写不出来，而是会在以下两种错误之间摇摆：
- 该 discovery 的地方直接硬编码
- 明明用户已经给了稳定 ID，却还在滥用 data source

本指南专门解决这个问题。

## 总规则

### 优先用 data source 的场景
- region / AZ / flavor / image 会随环境变化
- 用户说“复用现网资源”
- 用户只给了名字、标签、用途，没有给 ID
- 当前 provider 对该对象本来就提供成熟 discovery 能力

### 优先用显式输入的场景
- 用户已经给了可信 ID
- 资源名称在不同环境可能重复
- discovery 条件很多，容易因过滤过严返回空结果
- 该值本身是企业标准值，而不是每次都要动态挑选

## ECS

### 建议优先用 data source
- `huaweicloud_availability_zones`
- `huaweicloud_compute_flavors`
- `huaweicloud_images_image`
- `huaweicloud_vpc_subnet`
- `huaweicloud_networking_secgroup`

### 建议优先显式输入
- `subnet_id`
- `security_group_id`
- `key_pair_name`

原因：
- AZ / flavor / image 是强 discovery 类型
- subnet / secgroup 如果已经有现网 ID，直接输入比按名字查更稳

## ELB

### 建议优先用 data source
- 现有 EIP
- 现有 member 所属 ECS
- 现有 subnet / VPC

### 建议优先显式输入
- `loadbalancer_provider`
- `listener_protocol`
- `listener_port`
- `pool_algorithm`

原因：
- ELB 的“类型”和“监听/调度策略”是架构决策，不是 discovery 结果

## CCE

### 建议优先用 data source
- `huaweicloud_cce_flavor_specifications`
- `huaweicloud_compute_flavors`
- `huaweicloud_availability_zones`

### 建议优先显式输入
- `cluster_type`
- `cluster_version`
- `container_network_type`
- `key_pair_name`
- `root_volume_type` / `data_volume_type`

原因：
- 集群类型和网络类型是设计决策
- 集群 flavor 和节点 flavor 更适合动态发现

## RDS

### 建议优先用 data source
- `huaweicloud_rds_flavors`
- 现有 subnet / security group / VPC

### 建议优先显式输入
- `db_type`
- `db_version`
- `instance_mode`
- `group_type`
- `password`

原因：
- 引擎类型和部署形态是业务决策
- flavor 才是适合 discovery 的对象

## OBS

### 建议优先用 data source
- 复用已有 bucket
- 查询已有 object

### 建议优先显式输入
- `bucket_name`
- `acl`
- `versioning`
- `sse_algorithm`
- `kms_key_id`

原因：
- bucket 名、权限和加密策略属于意图输入，不适合动态猜

## IMS / EVS

### IMS 建议优先用 data source
- `huaweicloud_images_image`
- `huaweicloud_images_images`
- `huaweicloud_ims_os_versions`
- `huaweicloud_ims_images_by_tags`

### EVS 建议优先用 data source
- `huaweicloud_evs_volume_types`
- `huaweicloud_evs_availability_zones`
- `huaweicloud_evs_snapshots`

### 建议优先显式输入
- 镜像导入源对象 ID
- volume 大小
- 目标盘型企业标准

## VPCEP / DCS / DNS

### VPCEP
- discovery 优先：`huaweicloud_vpcep_public_services`、`huaweicloud_vpcep_services`
- 显式输入优先：`vpc_id`、`subnet_id`、`port_id`

### DCS
- discovery 优先：`huaweicloud_dcs_flavors`、`huaweicloud_dcs_az`
- 显式输入优先：`engine_version`、`password`、维护窗口

### DNS
- discovery 优先：`huaweicloud_dns_zones`、`huaweicloud_dns_nameservers`
- 显式输入优先：`zone_type`、`recordset type`、`ttl`、`records`

## IAM / RAM / Organizations / RGC / RMS

这类治理型服务有一个共同特点：
- “对象是否存在”适合查
- “权限或组织关系怎么设计”不适合猜

### 建议优先用 data source
- 查已有用户、用户组、账号、资源共享、聚合器、策略包

### 建议优先显式输入
- 最终授权关系
- 最终组织结构
- 最终治理策略绑定

### 实操建议
- 如果用户没有给清晰组织结构，优先先联动 `hcloud`
- Terraform 更适合沉淀最终结果，不适合负责“猜出治理结构”

## APIG / WAF / CDN / DMS

### APIG
- discovery 优先：instance、group、environment、plugin 可关联对象
- 显式输入优先：API 发布意图、插件类型、后端协议

### WAF
- discovery 优先：protectable resources、policy、certificate
- 显式输入优先：域名、源站、接入模式

### CDN
- discovery 优先：已有域名、证书、回源配置
- 显式输入优先：业务类型、缓存策略、源站类型

### DMS
- discovery 优先：可用规格、AZ、实例清单
- 显式输入优先：消息引擎、版本、分区/队列设计

## 一个简单判断法

如果一个值回答的是“环境里现在有什么”，优先考虑 data source。  
如果一个值回答的是“这套架构想怎么设计”，优先考虑显式输入。
