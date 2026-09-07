# Terraform Huawei Examples

这个目录收纳 `huawei-cloud-solution-ops` 已吸收并纳入校验流程的 Terraform 示例工程。

当前共有 73 套已吸收示例。建议先按场景找入口，而不是从服务名开始翻。

## Starter

- `ecs_stack`: 从零创建最小计算主链路
- `obs_stack`: 创建安全取向的 OBS Bucket
- `rds_stack`: 创建 PostgreSQL RDS 最小环境
- `elb_stack`: 创建公网入口型 ELB
- `cce_stack`: 创建标准 CCE 集群
- `vpcep_stack`: 创建 VPCEP 最小闭环

## Core Infrastructure

- `ecs_stack`: VPC / Subnet / Security Group / ECS
- `ecs_reuse_stack`: 复用现网 subnet / security group 创建 ECS
- `ecs_elb_rds_stack`: ECS + ELB + RDS 端到端 Web 服务拓扑
- `eip_stack`: 独立公网 EIP
- `evs_stack`: 独立 EVS 数据盘
- `obs_stack`: 安全取向的 OBS Bucket
- `rds_stack`: PostgreSQL RDS
- `rds_mysql_stack`: MySQL 单机实例
- `rds_postgresql_ha_stack`: PostgreSQL 高可用实例
- `rds_read_replica_stack`: MySQL 主实例 + 只读副本
- `rds_mysql_eip_stack`: MySQL 实例 + EIP 绑定
- `rds_sqlserver_stack`: SQL Server 单机实例
- `sfs_turbo_stack`: SFS Turbo 文件系统

## Container And Platform

- `cce_stack`: 标准 CCE 集群
- `cce_node_pool_stack`: 标准 CCE 集群 + 节点池
- `cce_node_pool_reuse_stack`: 复用现网 CCE 集群新增节点池
- `cce_addon_stack`: 复用现网 CCE 集群管理 autoscaler addon
- `cce_coredns_addon_stack`: 复用现网 CCE 集群管理 CoreDNS addon
- `cce_turbo_cluster_stack`: 创建 CCE Turbo 集群
- `cce_node_partition_stack`: 复用现网 CCE 集群创建分区和分区节点池
- `apig_stack`: APIG 专享实例与插件
- `dcs_stack`: Redis DCS
- `dms_stack`: RabbitMQ DMS
- `swr_stack`: SWR 组织与镜像仓库
- `ims_stack`: IMS 导出镜像到 OBS
- `fgs_stack`: FGS Trigger
- `cci_stack`: CCI Network

## Network And Traffic

- `elb_stack`: 公网入口型 ELB
- `elb_member_stack`: ELB + member + monitor 完整入口链
- `elb_reuse_stack`: 复用现网 ELB 创建 listener / pool / member / monitor
- `nat_snat_stack`: 统一出网 NAT
- `nat_dnat_stack`: 公网 DNAT 转发链路
- `nat_reuse_stack`: 复用现网 NAT Gateway / EIP 补 SNAT 和可选 DNAT 规则
- `nat_vpc_peering_stack`: NAT + VPC Peering 跨 VPC 出网/中转拓扑
- `vpc_peering_stack`: 两个 VPC 的 peering 和路由闭环
- `vpc_security_group_stack`: 独立安全组规则治理
- `vpn_stack`: VPN Gateway
- `er_stack`: ER + VPC Attachment
- `cc_stack`: CC Bandwidth Package
- `dc_stack`: DC Connect Gateway
- `esw_stack`: ESW Instance
- `dns_stack`: 公网 DNS Zone
- `cdn_stack`: CDN 加速域名
- `obs_cdn_dns_stack`: OBS 静态网站 + CDN + DNS CNAME 链路
- `vpcep_stack`: VPCEP Service / Endpoint

## Security And Governance

- `waf_stack`: WAF 云模式防护链路
- `antiddos_stack`: Anti-DDoS 告警闭环
- `cbh_stack`: CBH Instance
- `hss_stack`: HSS Host Group
- `iam_stack`: IAM 用户授权链路
- `identity_center_stack`: Identity Center Group
- `ram_stack`: RAM 资源共享
- `organizations_stack`: Organizations 成员账号
- `rgc_stack`: RGC Account
- `rms_stack`: RMS Resource Aggregator
- `secmaster_stack`: SecMaster Workspace
- `tms_stack`: TMS Preset Tags
- `sdrs_stack`: SDRS Protection Group
- `dew_stack`: DEW KMS Key
- `deh_stack`: DEH Instance

## Ops And Observability

- `aom_stack`: AOM Action Callback
- `ces_stack`: CES Alarm Template
- `coc_stack`: COC Script
- `cts_stack`: CTS System Tracker
- `lts_stack`: LTS 日志组与日志流
- `smn_stack`: SMN Publish Message

## Migration And Specialty

- `cbr_stack`: CBR Vault
- `sms_stack`: SMS Migration Project
- `oms_stack`: OMS Migration Task
- `as_stack`: AS Scaling Group
- `elb_as_stack`: ELB + AS + CES 伸缩入口拓扑
- `bms_stack`: BMS Instance
- `eg_stack`: EG Event Subscription

## Imported Minimal Examples

- `bms_stack`
- `cbh_stack`
- `cc_stack`
- `cci_stack`
- `ces_stack`
- `coc_stack`
- `cts_stack`
- `dc_stack`
- `deh_stack`
- `dew_stack`
- `dms_stack`
- `eg_stack`
- `esw_stack`
- `fgs_stack`
- `hss_stack`
- `iam_stack`
- `identity_center_stack`
- `ims_stack`
- `oms_stack`
- `rgc_stack`
- `rms_stack`
- `sdrs_stack`
- `secmaster_stack`
- `smn_stack`
- `tms_stack`

这些示例大多来自参考示例标准化导入，已经通过验证，但后续仍值得继续统一风格和增强说明。

## 使用建议

- 如果只是要一个能跑的起点，先从 `Starter` 选。
- 如果用户已经明确是某条业务链路，优先在相关分类里找最近的示例。
- 如果相关示例只有 imported minimal version，后续实现时要优先参考：
  - `references/terraform/advanced-variant-catalog.md`
  - `references/terraform/service-variant-guide.md`
  - `references/terraform/data-source-selection-guide.md`
- 如果后面开始做组合型示例，优先在当前分类基础上拼装，而不是从零设计目录结构。

### 52. `sdrs_stack`
- 路径: `examples/sdrs_stack/`
- 适合: 创建最小 SDRS Protection Group
- 包含: VPC、SDRS Domain Discovery、SDRS Protection Group

### 53. `secmaster_stack`
- 路径: `examples/secmaster_stack/`
- 适合: 创建最小 SecMaster Workspace
- 包含: SecMaster Workspace

### 54. `smn_stack`
- 路径: `examples/smn_stack/`
- 适合: 创建最小 SMN Publish Message
- 包含: SMN Topic、SMN Subscription、Message Template、Message Publish

### 55. `tms_stack`
- 路径: `examples/tms_stack/`
- 适合: 创建最小 TMS Preset Tags
- 包含: TMS Preset Tags

## 当前验证状态

示例进入 catalog 前至少要跑过以下检查：
- `terraform fmt -check -recursive`
- catalog 重新生成并能被 router 命中
- 不包含真实 AK/SK、密码、私钥、`terraform.tfvars`、state 或 `.terraform/` 运行缓存

具备本地 provider cache 或可访问 provider mirror 时，再运行：
- `terraform init -backend=false`
- `terraform validate`

说明：
- 本 Skill 发行目录不包含或提交 `.terraform.lock.hcl`；用户实际部署工程可自行维护生成的锁文件，用于固定 provider 版本选择
- `.terraform/` 运行缓存不保留
- 每个示例目录都提供了 `terraform.tfvars.example`
- 可通过 `examples/terraform/validate_examples.sh` 统一跑格式化和校验检查

## 使用建议

- 如果用户要“直接给我一个能跑的模板”，优先从这里选最接近的示例
- 如果用户要“基于现网资源改写”，优先从 `ecs_reuse_stack` 这一类复用型示例开始
- 如果用户只是问某段资源怎么写，再退回到 references 中的最小片段

## 下一阶段建议

当前 examples 已经覆盖基础计算、存储、数据库、容器、入口、出网、服务接入、镜像仓库、备份、组织治理、迁移项目、VPN、ER、CDN、日志、安全、消息、标签、迁移、运维链路、复用型改造和端到端业务拓扑。
如果继续扩展，建议优先做这几类，而不是继续零散补单个资源：

- APIG / DMS / DCS 等高频中间件和接入层变体
- 多 region、provider alias、`enterprise_project_id` 等企业级约束
- CI、provider schema cache、import/drift review 等工程化验证能力

更完整的阶段规划见 [references/terraform/roadmap.md](../../references/terraform/roadmap.md)。
