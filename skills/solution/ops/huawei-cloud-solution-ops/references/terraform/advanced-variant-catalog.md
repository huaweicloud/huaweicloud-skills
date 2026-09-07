# Advanced Variant Catalog

这份文档用于吸收参考仓库里还没有单独升级成新 `*_stack` 的“高级变体”信息。

目的不是把所有变体立刻都做成新示例，而是先把可复用的模式沉淀到 skill 内部，避免后续删除参考仓库后丢失这些信息。

## 如何使用

- 当已有 `*_stack` 只能覆盖最小主链路时，优先从本目录挑选更接近用户需求的变体。
- 当准备设计组合型示例时，优先检查本目录，看看哪些变体可以直接作为拼装零件。
- 当用户提出的是“同一服务的高阶玩法”，优先从本目录判断应该补哪个方向，而不是从空白 HCL 重新猜。

## 计算与网络变体

### ECS

当前已吸收示例：
- `ecs_stack`
- `ecs_reuse_stack`

仍值得复用的高级变体：
- `attached-interface`: 适合多网卡、双臂流量、旁路接入场景
- `attached-volume`: 适合补 `ECS + EVS` 组合示例
- `instance-associate-eip`: 适合补“单机直接公网暴露”场景
- `instance-provisioners`: 适合演示初始化脚本和远程配置
- `instance-with-userdata`: 适合云初始化、自举和应用部署
- `prepaid-instance`: 适合包年包月与计费模式差异说明

### ELB

当前已吸收示例：
- `elb_stack`
- `elb_member_stack`
- `elb_reuse_stack`
- `elb_as_stack`

仍值得复用的高级变体：
- `dedicated-loadbalancer-with-full-configuration`: 适合补独享型 ELB 的全量监听、池、健康检查参数
- `shared-loadbalancer-with-full-configuration`: 适合共享型 ELB 的完整配置对照
- `dedicated-loadbalancer-with-as`: 已吸收为 `elb_as_stack`，适合 `ELB + AS + CES` 组合型入口拓扑

### CCE

当前已吸收示例：
- `cce_stack`
- `cce_node_pool_stack`
- `cce_node_pool_reuse_stack`
- `cce_addon_stack`
- `cce_coredns_addon_stack`
- `cce_turbo_cluster_stack`
- `cce_node_partition_stack`

仍值得复用的高级变体：
- `addon-autoscaler`: 已吸收为 `cce_addon_stack`，适合复用现网集群补 autoscaler 治理
- `addon-coredns`: 已吸收为 `cce_coredns_addon_stack`，适合补基础网络插件管理
- `node`: 适合直接管理独立节点
- `node-partition`: 已吸收为 `cce_node_partition_stack`，适合补分区磁盘配置
- `standard-cluster` / `turbo-cluster`: `turbo-cluster` 已吸收为 `cce_turbo_cluster_stack`，适合补不同集群形态对比
- `autopilot`: 当前参考资产中未发现可直接吸收的独立 autopilot 示例，后续需要基于真实 provider schema 和官方文档单独设计。

### NAT

当前已吸收示例：
- `nat_snat_stack`
- `nat_dnat_stack`
- `nat_reuse_stack`
- `nat_vpc_peering_stack`

仍值得复用的高级变体：
- `nat-gateway-vpc-peering`: 已吸收为 `nat_vpc_peering_stack`，适合跨 VPC 出网或中转拓扑

### VPC

当前已吸收示例：
- `ecs_stack`、`elb_stack`、`nat_*_stack` 已经内嵌最小 VPC 逻辑
- `vpc_peering_stack`
- `vpc_security_group_stack`

仍值得复用的高级变体：
- `peering`: 已吸收为 `vpc_peering_stack`，适合跨 VPC 互联
- `security-group`: 已吸收为 `vpc_security_group_stack`，适合单独展示规则治理
- `vip`: 适合高可用漂移 IP 或虚拟 IP 场景

### VPN / ER / CC / DC / ESW

这些服务已经有最小 `*_stack`，但参考仓库里还保留了更适合企业网络的变体：
- VPN: `connection`、`user`
- ER: `flow-log`、`route-table`
- CC: `central-network`、`global-connection-bandwidth`
- DC: `global-gateway`、`hosted-connect`、`virtual-interface`
- ESW: `connection`、`connection-vport-bind`

这些变体更适合后续做“企业广域网”和“多网络互通”组合型示例。

## 数据与平台变体

### OBS

当前已吸收示例：
- `obs_stack`
- `obs_cdn_dns_stack`

仍值得复用的高级变体：
- `bucket-with-website`: 已吸收进 `obs_cdn_dns_stack` 的静态网站链路
- `object-upload-with-content`: 已吸收进 `obs_cdn_dns_stack` 的页面对象上传链路
- `object-upload-with-source`: 适合本地文件上传
- `object-upload-with-encryption`: 适合对象级加密说明

### RDS

当前已吸收示例：
- `rds_stack`
- `rds_mysql_stack`
- `rds_postgresql_ha_stack`
- `rds_read_replica_stack`
- `rds_mysql_eip_stack`
- `rds_sqlserver_stack`

仍值得复用的高级变体：
- `mysql-single-instance`: 已吸收为 `rds_mysql_stack`
- `mysql-instance-associate-eip`: 已吸收为 `rds_mysql_eip_stack`
- `postgresql-ha-instance`: 已吸收为 `rds_postgresql_ha_stack`
- `read-replica-instance`: 已吸收为 `rds_read_replica_stack`
- `sqlserver-single-instance`: 已吸收为 `rds_sqlserver_stack`

这些变体已经形成第一版数据库形态矩阵，后续再根据真实命中补参数细化、备份策略和企业项目约束。

### DMS

当前已吸收示例：
- `dms_stack` 只覆盖 RabbitMQ

仍值得复用的高级变体：
- `kafka`
- `rocketmq`

后续如果用户更多命中消息流处理、事件中台或日志管道，再补这两条更有价值。

### DCS

当前已吸收示例：
- `dcs_stack`

仍值得复用的高级变体：
- `redis-high-availability-instance`
- `redis-data-sync`

### CBR

当前已吸收示例：
- `cbr_stack`

仍值得复用的高级变体：
- `vault-volume`
- `vault-turbo`

后续可以把备份能力从“服务器备份”扩展到“云盘备份”和“SFS Turbo 备份”。

### EVS

当前已吸收示例：
- `evs_stack`

仍值得复用的高级变体：
- `snapshot`
- `snapshot-group`

### SWR

当前已吸收示例：
- `swr_stack`

仍值得复用的高级变体：
- `organization`
- `retention-policy`

适合后续做“仓库治理”和“镜像生命周期”增强。

## 接入、安全与治理变体

### APIG

当前已吸收示例：
- `apig_stack`

仍值得复用的高级变体：
- `api-custom-authorizer-with-functiongraph`
- `kafka-forward-plugin`
- `proxy-cache-plugin`

这三类很适合后续补高阶 APIG 场景，不需要从零猜插件组合。

### WAF

当前已吸收示例：
- `waf_stack`

仍值得复用的高级变体：
- `dedicated-instance`
- `dedicated-domain`

适合补独享模式、实例容量和域名绑定关系。

### Anti-DDoS

当前已吸收示例：
- `antiddos_stack`

仍值得复用的高级变体：
- `default-protection-policy`
- `lts-config`

适合补防护策略和日志联动。

### AOM / CES / COC / CTS / LTS / SMN

这些服务都已有最小示例，但参考仓库里还保留了更接近日常运维的平台型变体：
- AOM: `alarm-rule`
- CES: `dashboard`、`resource-group`
- COC: `script-execution`、`script-order-execution`
- CTS: `data-tracker`、`notification`
- LTS: `log-transfer`、`sql-alarm-rule`
- SMN: `ces-event-alarm-rule`、`topic-with-aom-alarm-notification`

这些内容很适合后续做“日志-告警-通知-自动化”联动示例。

### RAM / Organizations / RGC / RMS / SecMaster / SMS

这些服务已经有最小 `*_stack`，但更高阶的治理和迁移场景仍值得沉淀：
- RAM: `automated-resource-share-invitation-processing`、`fine-grained-permission-management`
- Organizations: `organization`、`organization-unit`
- RGC: `account-enroll`、`template`
- RMS: `assignment-package`、`policy-assignment`
- SecMaster: `playbook`、`workflow-version`
- SMS: `migration-task`、`server-template`

## 身份、镜像和主机安全变体

### IAM / Identity Center

当前已吸收示例：
- `iam_stack`
- `identity_center_stack`

仍值得复用的高级变体：
- IAM: `v5`
- Identity Center: `instance-configuration`、`password-policy`

### IMS

当前已吸收示例：
- `ims_stack`

仍值得复用的高级变体：
- `cross-account-migration-with-data-image`
- `cross-account-migration-with-whole-image`

### HSS / CBH / BMS / DEH / DEW

这些服务的最小示例已经具备，但仍有更接近生产的变体值得保留：
- HSS: `postpaid-host-protection`、`prepaid-quota`
- CBH: `change-instance-type`、`ha-instance`
- BMS: `bms-reset-password`、`volume-attach`
- DEH: `associate-ecs-instance`、`query-resource-quota`
- DEW: `csms-secret`、`kps-keypair`

## 后续如何使用本目录

当准备继续深化 skill 时，优先顺序建议是：
1. 先挑最接近真实业务链路的高级变体
2. 再把它们整理成新的组合型示例
3. 最后再决定是否需要新增独立 `*_stack`

不建议把所有变体一口气都做成新目录，否则 examples 会快速膨胀，反而降低可维护性。
