# Resource Mapping

第一轮优先覆盖的华为云 Terraform 资源与 data source 映射如下。

## 网络

### VPC
- Resource: `huaweicloud_vpc`
- Doc source: `docs/resources/vpc.md`
- 关键字段: `name`, `cidr`, `tags`, `secondary_cidrs`

### Subnet
- Resource: `huaweicloud_vpc_subnet`
- Data source: `huaweicloud_vpc_subnet`, `huaweicloud_vpc_subnets`
- 常见用途:
  - 复用现网子网
  - 从 subnet 反查 `vpc_id`

### Security Group
- Resource: `huaweicloud_networking_secgroup`
- Resource: `huaweicloud_networking_secgroup_rule`
- Data source: `huaweicloud_networking_secgroup`

## 计算

### ECS
- Resource: `huaweicloud_compute_instance`
- 常用 data source:
  - `huaweicloud_availability_zones`
  - `huaweicloud_compute_flavors`
  - `huaweicloud_images_image`
  - `huaweicloud_vpc_subnet`
  - `huaweicloud_networking_secgroup`

关键字段：
- `name`
- `image_id` / `image_name`
- `flavor_id`
- `security_group_ids`
- `availability_zone`
- `network`
- `key_pair` 或 `admin_pass`
- `system_disk_type`

变体选择参考：
- 需要自举安装时优先看 `instance-with-userdata`
- 需要挂数据盘时优先看 `attached-volume`
- 需要直接公网暴露时优先看 `instance-associate-eip`
- 需要包年包月时优先看 `prepaid-instance`

### CCE Cluster
- Resource: `huaweicloud_cce_cluster`
- 常用 data source:
  - `huaweicloud_availability_zones`
  - `huaweicloud_cce_flavor_specifications`

关键字段：
- `name`
- `flavor_id`
- `cluster_type`
- `cluster_version`
- `container_network_type`
- `vpc_id`
- `subnet_id`
- `eip`

形态差异重点：
- `cluster_type` 决定标准型和 Turbo 的差异
- addon、日志、节点池配置不要和集群本体混成一个最小模板

### CCE Node Pool
- Resource: `huaweicloud_cce_node_pool`
- 常用 data source:
  - `huaweicloud_compute_flavors`
  - `huaweicloud_availability_zones`

关键字段：
- `cluster_id`
- `name`
- `flavor_id`
- `availability_zone`
- `key_pair` 或 `password`
- `root_volume`
- `data_volumes`
- `min_node_count` / `max_node_count`

变体选择参考：
- `node-partition` 适合分区和磁盘布局更复杂的节点
- `addon-*` 适合在集群稳定后再补，而不是一开始混入最小模板

### IMS
- 常见 Resource:
  - `huaweicloud_ims_image_registration`
  - `huaweicloud_ims_ecs_system_image`
  - `huaweicloud_ims_evs_system_image`
  - `huaweicloud_ims_obs_system_image`
- 常见 Data source:
  - `huaweicloud_images_image`
  - `huaweicloud_images_images`
  - `huaweicloud_ims_os_versions`
  - `huaweicloud_ims_images_by_tags`

常见用途：
- 发现可用公共镜像或私有镜像
- 从 ECS / EVS / OBS 导入镜像
- 按标签筛选镜像资产

### EVS
- 常见 Resource:
  - `huaweicloud_evs_volume`
  - `huaweicloud_evs_snapshot`
  - `huaweicloud_evs_snapshot_group`
- 常见 Data source:
  - `huaweicloud_evs_volume_types`
  - `huaweicloud_evs_availability_zones`
  - `huaweicloud_evs_volumes`
  - `huaweicloud_evs_snapshots`

关键字段：
- `availability_zone`
- `volume_type`
- `size`
- `snapshot_id`
- `tags`

形态差异重点：
- 普通 volume、snapshot、snapshot_group 是三类不同生命周期对象
- 与 ECS 组合时，优先先决定是“独立数据盘”还是“快照恢复”

## 公网访问

### EIP
- Resource: `huaweicloud_vpc_eip`
- 关联资源：`huaweicloud_vpc_eip_associate`, `huaweicloud_vpc_eipv3_associate`, `huaweicloud_compute_eip_associate`
- 常见用途：
  - 给 ECS 绑定公网 IP
  - 给 ELB 绑定公网入口
  - 给 NAT Gateway 提供公网出口

关键字段：
- `publicip`
- `bandwidth`
- `address`
- `status`

### ELB
- Resource: `huaweicloud_lb_loadbalancer`
- Resource: `huaweicloud_lb_listener`
- Resource: `huaweicloud_lb_pool`
- 常见关联资源：
  - `huaweicloud_vpc_eipv3_associate`
  - `huaweicloud_lb_member`
  - `huaweicloud_lb_monitor`

关键字段：
- `vip_subnet_id`
- `listener_id`
- `protocol` / `protocol_port`
- `lb_method`
- `public_ip`
- `address` / `protocol_port` of member
- `type` / `delay` / `timeout` of monitor

形态差异重点：
- 独享型和共享型字段集合不同
- `loadbalancer_provider`、`l4_flavor_id`、`l7_flavor_id` 是高价值区分点
- 完整入口链要额外考虑 `member`、`monitor`、EIP 关联

### NAT Gateway
- Resource: `huaweicloud_nat_gateway`
- Resource: `huaweicloud_nat_snat_rule`
- Resource: `huaweicloud_nat_dnat_rule`

关键字段：
- `vpc_id`
- `subnet_id`
- `spec`
- `floating_ip_id`
- `source_type`
- `subnet_id` 或 `cidr`
- `port_id`
- `internal_service_port` / `external_service_port`

### VPCEP
- 常见 Resource:
  - `huaweicloud_vpcep_endpoint`
  - `huaweicloud_vpcep_service`
  - `huaweicloud_vpcep_approval`
- 常见 Data source:
  - `huaweicloud_vpcep_services`
  - `huaweicloud_vpcep_public_services`
  - `huaweicloud_vpcep_endpoints`
  - `huaweicloud_vpcep_service_connections`

关键字段：
- `service_name`
- `vpc_id`
- `subnet_id`
- `port_id`
- `endpoint_service_name`

## 存储

### OBS Bucket
- Resource: `huaweicloud_obs_bucket`
- Data source: `huaweicloud_obs_buckets`, `huaweicloud_obs_bucket_object`

关键字段：
- `bucket`
- `acl`
- `versioning`
- `encryption`
- `sse_algorithm`
- `kms_key_id`
- `logging`
- `lifecycle_rule`

形态差异重点：
- bucket 级加密和 object 级加密不要混为一谈
- website hosting 只适合静态站点，不适合默认放进私有加密模板

## 数据库

### RDS Instance
- Resource: `huaweicloud_rds_instance`
- Data source: `huaweicloud_rds_instances`

关键字段：
- `name`
- `flavor`
- `vpc_id`
- `subnet_id`
- `security_group_id`
- `availability_zone`
- `db`
- `volume`
- `backup_strategy`

形态差异重点：
- single、HA、read replica 的约束明显不同
- `db.type` / `db.version` 先决定数据库路线，再去 discovery flavor

### DCS
- 常见 Resource:
  - `huaweicloud_dcs_instance`
  - `huaweicloud_dcs_account`
  - `huaweicloud_dcs_backup`
- 常见 Data source:
  - `huaweicloud_dcs_instances`
  - `huaweicloud_dcs_flavors`
  - `huaweicloud_dcs_az`
  - `huaweicloud_dcs_templates`
  - `huaweicloud_dcs_maintainwindow`

关键字段：
- `engine`
- `engine_version`
- `capacity`
- `flavor`
- `available_zones`
- `password`
- `maintain_begin` / `maintain_end`

形态差异重点：
- single、HA、data sync 是三条不同线路
- flavor 和 capacity 受 engine/version 影响很强

### SWR
- 常见 Resource:
  - `huaweicloud_swr_repository`
  - `huaweicloud_swr_organization`
  - `huaweicloud_swr_image_retention_policy`
- 常见 Data source:
  - `huaweicloud_swr_repositories`
  - `huaweicloud_swr_image_tags`
  - `huaweicloud_swr_quotas`
  - `huaweicloud_swr_sync_regions`

关键字段：
- `organization`
- `repository`
- `retention_policy`
- `tag`
- `sync_region`

## 流量治理与安全

### DNS
- 常见 Resource:
  - `huaweicloud_dns_zone`
  - `huaweicloud_dns_recordset`
  - `huaweicloud_dns_resolver_rule`
  - `huaweicloud_dns_endpoint`
- 常见 Data source:
  - `huaweicloud_dns_zones`
  - `huaweicloud_dns_recordsets`
  - `huaweicloud_dns_nameservers`
  - `huaweicloud_dns_endpoints`
  - `huaweicloud_dns_resolver_rules`

关键字段：
- `zone_type`
- `name`
- `ttl`
- `records`
- `router_id`

### WAF
- 常见 Resource:
  - `huaweicloud_waf_cloud_instance`
  - `huaweicloud_waf_dedicated_instance`
  - `huaweicloud_waf_domain`
  - `huaweicloud_waf_policy`
  - `huaweicloud_waf_certificate`
- 常见 Data source:
  - `huaweicloud_waf_domains`
  - `huaweicloud_waf_policies`
  - `huaweicloud_waf_protectable_resources`
  - `huaweicloud_waf_certificate`
  - `huaweicloud_waf_alarm_notifications`

关键字段：
- `domain`
- `policy_id`
- `certificate_id`
- `protect_status`
- `dedicated_instance_id`

### AS
- 常见 Resource:
  - `huaweicloud_as_group`
  - `huaweicloud_as_configuration`
  - `huaweicloud_as_policy`
  - `huaweicloud_as_notification`
- 常见 Data source:
  - `huaweicloud_as_groups`
  - `huaweicloud_as_configurations`
  - `huaweicloud_as_policies`
  - `huaweicloud_as_quotas`

关键字段：
- `scaling_group_name`
- `scaling_configuration_id`
- `min_instance_number`
- `max_instance_number`
- `scaling_policy_type`
- `cool_down_time`

### APIG
- 常见 Resource:
  - `huaweicloud_apig_instance`
- `huaweicloud_apig_group`
- `huaweicloud_apig_api`
- `huaweicloud_apig_environment`
- `huaweicloud_apig_api_publishment`

形态差异重点：
- 最小实例、认证插件、缓存插件、Kafka 转发是不同层次的场景
- `group`、`environment`、`api`、`publishment` 要串成一条链
  - `huaweicloud_apig_vpc_channel`
- 常见 Data source:
  - `huaweicloud_apig_instances`
  - `huaweicloud_apig_groups`
  - `huaweicloud_apig_environments`
  - `huaweicloud_apig_quotas`
  - `huaweicloud_apig_availability_zones`

关键字段：
- `instance_id`
- `group_id`
- `path`
- `method`
- `backend_type`
- `environment_id`

### CDN
- 常见 Resource:
  - `huaweicloud_cdn_domain`
  - `huaweicloud_cdn_rule_engine_rule`
  - `huaweicloud_cdn_cache_refresh`
  - `huaweicloud_cdn_cache_preheat`
- 常见 Data source:
  - `huaweicloud_cdn_domains`
  - `huaweicloud_cdn_quotas`
  - `huaweicloud_cdn_domain_statistics`
  - `huaweicloud_cdn_logs`

关键字段：
- `domain_name`
- `origin`
- `service_area`
- `business_type`
- `sources`

### ER
- 常见 Resource:
  - `huaweicloud_er_instance`
  - `huaweicloud_er_vpc_attachment`
  - `huaweicloud_er_route_table`
  - `huaweicloud_er_static_route`
- 常见 Data source:
  - `huaweicloud_er_instances`
  - `huaweicloud_er_attachments`
  - `huaweicloud_er_route_tables`
  - `huaweicloud_er_available_routes`
  - `huaweicloud_er_quotas`

关键字段：
- `instance_id`
- `route_table_id`
- `attachment_id`
- `vpc_id`
- `destination`

### VPN
- 常见 Resource:
  - `huaweicloud_vpn_gateway`
  - `huaweicloud_vpn_customer_gateway`
  - `huaweicloud_vpn_connection`
  - `huaweicloud_vpn_server`
- 常见 Data source:
  - `huaweicloud_vpn_gateways`
  - `huaweicloud_vpn_connections`
  - `huaweicloud_vpn_customer_gateways`
  - `huaweicloud_vpn_quotas`

关键字段：
- `vpc_id`
- `subnet_id`
- `local_subnets`
- `peer_address`
- `peer_subnets`

### CBR
- 常见 Resource:
  - `huaweicloud_cbr_vault`
  - `huaweicloud_cbr_policy`
  - `huaweicloud_cbr_checkpoint`
  - `huaweicloud_cbr_backup_share`
- 常见 Data source:
  - `huaweicloud_cbr_vaults`
  - `huaweicloud_cbr_policies`
  - `huaweicloud_cbr_backups`
  - `huaweicloud_cbr_protectable_instances`
  - `huaweicloud_cbr_storage_usages`

关键字段：
- `vault_name`
- `billing`
- `resources`
- `policy_id`
- `backup_id`

### IAM
- 当前按基础身份治理支持处理。
- 常见关注对象：
  - 用户
  - 用户组
  - 委托 / agency
  - 权限策略 / policy
  - 项目级与全局级授权关系

使用建议：
- 当 Terraform 需要依赖账号、委托、授权关系时，优先先通过 `hcloud` 或控制台确认真实结构
- 当前先作为治理型基础支持，不承诺独立 validated example

### LTS
- 常见 Resource:
  - `huaweicloud_lts_group`
  - `huaweicloud_lts_stream`
  - `huaweicloud_lts_transfer`
  - `huaweicloud_lts_notification_template`
- 常见 Data source:
  - `huaweicloud_lts_groups`
  - `huaweicloud_lts_streams`
  - `huaweicloud_lts_logs`
  - `huaweicloud_lts_transfers`

关键字段：
- `group_name`
- `stream_name`
- `log_transfer_type`
- `notification_template_id`

### SMN
- 常见 Resource:
  - `huaweicloud_smn_topic`
  - `huaweicloud_smn_subscription`
  - `huaweicloud_smn_message_template`
  - `huaweicloud_smn_notify_policy`
- 常见 Data source:
  - `huaweicloud_smn_topics`
  - `huaweicloud_smn_subscriptions`
  - `huaweicloud_smn_message_templates`
  - `huaweicloud_smn_protocols`

关键字段：
- `name`
- `protocol`
- `endpoint`
- `topic_urn`

### TMS
- 常见 Resource:
  - `huaweicloud_tms_tags`
  - `huaweicloud_tms_resource_tags`
- 常见 Data source:
  - `huaweicloud_tms_tags`
  - `huaweicloud_tms_resource_tags`
  - `huaweicloud_tms_resource_types`
  - `huaweicloud_tms_quotas`

关键字段：
- `resource_type`
- `resource_id`
- `tags`

## 运维、消息与专用平台

### Anti-DDoS
- 常见 Resource:
  - `huaweicloud_antiddos_basic`
  - `huaweicloud_antiddos_open_protection`
  - `huaweicloud_antiddos_default_protection_policy`
  - `huaweicloud_antiddos_lts_config`
- 常见 Data source:
  - `huaweicloud_antiddos`
  - `huaweicloud_antiddos_quota`
  - `huaweicloud_antiddos_config_ranges`
  - `huaweicloud_antiddos_eip_defense_statuses`

关键字段：
- `eip_id` 或防护对象
- `policy`
- `traffic_trigger`
- `log_config`

### AOM
- 常见 Resource:
  - `huaweicloud_aom_alarm_rule`
  - `huaweicloud_aom_alarm_action_rule`
  - `huaweicloud_aom_dashboard`
  - `huaweicloud_aom_prom_instance`
  - `huaweicloud_aom_message_template`
- 常见 Data source:
  - `huaweicloud_aom_alarm_rules`
  - `huaweicloud_aom_alarm_action_rules`
  - `huaweicloud_aom_dashboards`
  - `huaweicloud_aom_prom_instances`

关键字段：
- `alarm_name`
- `metric`
- `prometheus_instance_id`
- `notification_target`

### BMS
- 常见 Resource:
  - `huaweicloud_bms_instance`
  - `huaweicloud_bms_volume_attach`
  - `huaweicloud_bms_os_reinstall`
- 常见 Data source:
  - `huaweicloud_bms_instances`
  - `huaweicloud_bms_flavors`
  - `huaweicloud_bms_available_resources`
  - `huaweicloud_bms_quotas`

关键字段：
- `flavor_id`
- `image_id`
- `availability_zone`
- `root_volume`
- `data_volumes`

### CBH
- 常见 Resource:
  - `huaweicloud_cbh_instance`
  - `huaweicloud_cbh_ha_instance`
  - `huaweicloud_cbh_asset_agency_authorization`
- 常见 Data source:
  - `huaweicloud_cbh_instances`
  - `huaweicloud_cbh_flavors`
  - `huaweicloud_cbh_availability_zones`
  - `huaweicloud_cbh_instance_quota`

关键字段：
- `flavor`
- `availability_zone`
- `vpc_id`
- `subnet_id`
- `security_group_id`

### CCI
- 常见 Resource:
  - `huaweicloud_cci_namespace`
  - `huaweicloud_cci_network`
  - `huaweicloud_cci_pvc`
  - `huaweicloud_cci_agency`
- 常见 Data source:
  - `huaweicloud_cci_namespaces`

关键字段：
- `namespace`
- `vpc_id`
- `subnet_id`
- `storage_class`

### COC
- 常见 Resource:
  - `huaweicloud_coc_application`
  - `huaweicloud_coc_group`
  - `huaweicloud_coc_script`
  - `huaweicloud_coc_document`
  - `huaweicloud_coc_scheduled_task`
  - `huaweicloud_coc_incident`
- 常见 Data source:
  - `huaweicloud_coc_applications`
  - `huaweicloud_coc_groups`
  - `huaweicloud_coc_scripts`
  - `huaweicloud_coc_documents`
  - `huaweicloud_coc_incidents`

关键字段：
- `application_id`
- `group_id`
- `script_id`
- `document_id`
- `schedule`

### CTS
- 常见 Resource:
  - `huaweicloud_cts_tracker`
  - `huaweicloud_cts_data_tracker`
  - `huaweicloud_cts_notification`
  - `huaweicloud_cts_configuration`
- 常见 Data source:
  - `huaweicloud_cts_trackers`
  - `huaweicloud_cts_traces`
  - `huaweicloud_cts_notifications`
  - `huaweicloud_cts_quotas`

关键字段：
- `tracker_name`
- `obs_bucket_name`
- `smn_topic`
- `trace_scope`

### DMS
- 常见 Resource:
  - `huaweicloud_dms_instance`
  - `huaweicloud_dms_kafka_instance`
  - `huaweicloud_dms_rabbitmq_instance`
  - `huaweicloud_dms_rocketmq_instance`
  - `huaweicloud_dms_kafka_topic`
  - `huaweicloud_dms_queue`
- 常见 Data source:
  - `huaweicloud_dms_product`
  - `huaweicloud_dms_az`
  - `huaweicloud_dms_maintainwindow`
  - `huaweicloud_dms_kafka_instances`
  - `huaweicloud_dms_rabbitmq_instances`
  - `huaweicloud_dms_rocketmq_instances`

关键字段：
- `engine`
- `flavor`
- `storage_space`
- `available_zones`
- `vpc_id`
- `subnet_id`
- `security_group_id`

### FGS
- 常见 Resource:
  - `huaweicloud_fgs_function`
  - `huaweicloud_fgs_trigger`
  - `huaweicloud_fgs_function_trigger`
  - `huaweicloud_fgs_dependency`
  - `huaweicloud_fgs_application`
- 常见 Data source:
  - `huaweicloud_fgs_functions`
  - `huaweicloud_fgs_trigger_types`
  - `huaweicloud_fgs_dependencies`
  - `huaweicloud_fgs_runtime_types`
  - `huaweicloud_fgs_quotas`

关键字段：
- `runtime`
- `handler`
- `memory_size`
- `timeout`
- `trigger_type`

### CC
- 常见 Resource:
  - `huaweicloud_cc_central_network`
  - `huaweicloud_cc_connection`
  - `huaweicloud_cc_network_instance`
  - `huaweicloud_cc_bandwidth_package`
  - `huaweicloud_cc_global_connection_bandwidth`
- 常见 Data source:
  - `huaweicloud_cc_central_networks`
  - `huaweicloud_cc_connections`
  - `huaweicloud_cc_network_instances`
  - `huaweicloud_cc_bandwidth_packages`
  - `huaweicloud_cc_permissions`

关键字段：
- `central_network_id`
- `connection_id`
- `network_instance_id`
- `bandwidth_package_id`
- `region`

### CES
- 常见 Resource:
  - `huaweicloud_ces_alarmrule`
  - `huaweicloud_ces_alarm_template`
  - `huaweicloud_ces_dashboard`
  - `huaweicloud_ces_resource_group`
- 常见 Data source:
  - `huaweicloud_ces_alarmrules`
  - `huaweicloud_ces_alarm_templates`
  - `huaweicloud_ces_dashboards`
  - `huaweicloud_ces_metrics`
  - `huaweicloud_ces_quotas`

关键字段：
- `alarm_name`
- `metric_name`
- `namespace`
- `comparison_operator`
- `period`

### DC
- 常见 Resource:
  - `huaweicloud_dc_connect_gateway`
  - `huaweicloud_dc_virtual_gateway`
  - `huaweicloud_dc_virtual_interface`
  - `huaweicloud_dc_global_gateway`
- 常见 Data source:
  - `huaweicloud_dc_connect_gateways`
  - `huaweicloud_dc_virtual_gateways`
  - `huaweicloud_dc_virtual_interfaces`
  - `huaweicloud_dc_global_gateways`
  - `huaweicloud_dc_quotas`

关键字段：
- `gateway_id`
- `vlan`
- `bandwidth`
- `route_mode`
- `remote_ep_group`

### DEH
- 常见 Resource:
  - `huaweicloud_deh_instance`
- 常见 Data source:
  - `huaweicloud_deh_instances`
  - `huaweicloud_deh_instances_by_tags`
  - `huaweicloud_deh_types`
  - `huaweicloud_deh_quotas`

关键字段：
- `flavor`
- `availability_zone`
- `auto_placement`
- `host_type`

### DEW
- 当前按密钥与证书能力支持处理。
- 常见能力域：
  - KMS
  - CCM
  - 私有 CA
  - 证书导入、签发、部署
- 常见 Resource:
  - `huaweicloud_ccm_certificate`
  - `huaweicloud_ccm_private_ca`
  - `huaweicloud_ccm_private_certificate`
- 常见 Data source:
  - `huaweicloud_ccm_certificates`
  - `huaweicloud_ccm_private_cas`
  - `huaweicloud_ccm_private_certificates`

使用建议：
- Terraform 更适合管理稳定的密钥、证书和 CA 对象
- 如果只是临时取密钥、签名或排障，优先先联动现网工具确认

### EG
- 常见 Resource:
  - `huaweicloud_eg_connection`
  - `huaweicloud_eg_event_channel`
  - `huaweicloud_eg_custom_event_source`
  - `huaweicloud_eg_event_subscription`
  - `huaweicloud_eg_event_stream`
- 常见 Data source:
  - `huaweicloud_eg_connections`
  - `huaweicloud_eg_event_channels`
  - `huaweicloud_eg_event_sources`
  - `huaweicloud_eg_event_subscriptions`
  - `huaweicloud_eg_quotas`

关键字段：
- `channel_id`
- `source_name`
- `connection_id`
- `target`
- `rule`

### ESW
- 常见 Resource:
  - `huaweicloud_esw_instance`
  - `huaweicloud_esw_connection`
  - `huaweicloud_esw_connection_vport_bind`
- 常见 Data source:
  - `huaweicloud_esw_instances`
  - `huaweicloud_esw_connections`
  - `huaweicloud_esw_flavors`
  - `huaweicloud_esw_availability_zones`
  - `huaweicloud_esw_quotas`

关键字段：
- `instance_id`
- `connection_id`
- `vport_id`
- `flavor`
- `availability_zone`

### HSS
- 常见 Resource:
  - `huaweicloud_hss_host_protection`
  - `huaweicloud_hss_policy_group`
  - `huaweicloud_hss_webtamper_protection`
  - `huaweicloud_hss_quota`
  - `huaweicloud_hss_ransomware_protection_policy`
- 常见 Data source:
  - `huaweicloud_hss_hosts`
  - `huaweicloud_hss_policy_groups`
  - `huaweicloud_hss_quotas`
  - `huaweicloud_hss_vulnerabilities`
  - `huaweicloud_hss_webtamper_hosts`

关键字段：
- `host_id`
- `policy_group_id`
- `protection_mode`
- `quota`
- `alarm` / `notification`

### Identity Center
- 常见 Resource:
  - `huaweicloud_identitycenter_instance`
  - `huaweicloud_identitycenter_user`
  - `huaweicloud_identitycenter_group`
  - `huaweicloud_identitycenter_permission_set`
  - `huaweicloud_identitycenter_account_assignment`
- 常见 Data source:
  - `huaweicloud_identitycenter_instance`
  - `huaweicloud_identitycenter_users`
  - `huaweicloud_identitycenter_groups`
  - `huaweicloud_identitycenter_permission_sets`
  - `huaweicloud_identitycenter_account_assignments`

关键字段：
- `instance_id`
- `user_id`
- `group_id`
- `permission_set_id`
- `account_id`

### OMS
- 常见 Resource:
  - `huaweicloud_oms_migration_task`
  - `huaweicloud_oms_migration_sync_task`
  - `huaweicloud_oms_migration_task_group`
  - `huaweicloud_oms_sync_event`
- 常见 Data source:
  - `huaweicloud_oms_migration_tasks`
  - `huaweicloud_oms_migration_sync_tasks`
  - `huaweicloud_oms_migration_task_groups`
  - `huaweicloud_oms_sync_task_statistics`
  - `huaweicloud_oms_buckets`

关键字段：
- `task_name`
- `source_type`
- `destination_type`
- `bucket`
- `sync_mode`

### Organizations
- 常见 Resource:
  - `huaweicloud_organizations_organization`
  - `huaweicloud_organizations_account`
  - `huaweicloud_organizations_organizational_unit`
  - `huaweicloud_organizations_policy`
  - `huaweicloud_organizations_policy_attach`
- 常见 Data source:
  - `huaweicloud_organizations_organization`
  - `huaweicloud_organizations_accounts`
  - `huaweicloud_organizations_organizational_units`
  - `huaweicloud_organizations_policies`
  - `huaweicloud_organizations_effective_policies`

关键字段：
- `organization_id`
- `account_id`
- `organizational_unit_id`
- `policy_id`
- `service`

### RAM
- 常见 Resource:
  - `huaweicloud_ram_resource_share`
  - `huaweicloud_ram_resource_share_permission`
  - `huaweicloud_ram_resource_share_accepter`
  - `huaweicloud_ram_organization`
- 常见 Data source:
  - `huaweicloud_ram_resource_shares`
  - `huaweicloud_ram_shared_resources`
  - `huaweicloud_ram_shared_principals`
  - `huaweicloud_ram_resource_permissions`
  - `huaweicloud_ram_quotas`

关键字段：
- `resource_share_name`
- `principal`
- `resource_arn`
- `permission_name`

### RGC
- 常见 Resource:
  - `huaweicloud_rgc_landing_zone`
  - `huaweicloud_rgc_account`
  - `huaweicloud_rgc_control`
  - `huaweicloud_rgc_template`
  - `huaweicloud_rgc_organizational_unit`
- 常见 Data source:
  - `huaweicloud_rgc_accounts`
  - `huaweicloud_rgc_controls`
  - `huaweicloud_rgc_landing_zone_configuration`
  - `huaweicloud_rgc_enabled_controls`
  - `huaweicloud_rgc_home_region`

关键字段：
- `landing_zone`
- `account_id`
- `organizational_unit_id`
- `control_id`
- `home_region`

### RMS
- 常见 Resource:
  - `huaweicloud_rms_resource_recorder`
  - `huaweicloud_rms_resource_aggregator`
  - `huaweicloud_rms_policy_assignment`
  - `huaweicloud_rms_assignment_package`
  - `huaweicloud_rms_remediation_configuration`
- 常见 Data source:
  - `huaweicloud_rms_resources`
  - `huaweicloud_rms_policy_assignments`
  - `huaweicloud_rms_assignment_packages`
  - `huaweicloud_rms_resource_aggregators`
  - `huaweicloud_rms_policy_definitions`

关键字段：
- `resource_recorder`
- `aggregator_name`
- `policy_assignment_name`
- `policy_definition_id`
- `target_scope`

### SDRS
- 常见 Resource:
  - `huaweicloud_sdrs_protection_group`
  - `huaweicloud_sdrs_replication_pair`
  - `huaweicloud_sdrs_protected_instance`
  - `huaweicloud_sdrs_drill`
- 常见 Data source:
  - `huaweicloud_sdrs_protection_groups`
  - `huaweicloud_sdrs_replication_pairs`
  - `huaweicloud_sdrs_protected_instances`
  - `huaweicloud_sdrs_drills`
  - `huaweicloud_sdrs_quotas`

关键字段：
- `protection_group_id`
- `replication_pair_id`
- `server_id`
- `drill`
- `rpo`

### SecMaster
- 常见 Resource:
  - `huaweicloud_secmaster_alert`
  - `huaweicloud_secmaster_alert_rule`
  - `huaweicloud_secmaster_incident`
  - `huaweicloud_secmaster_playbook`
  - `huaweicloud_secmaster_workflow`
  - `huaweicloud_secmaster_module`
- 常见 Data source:
  - `huaweicloud_secmaster_alerts`
  - `huaweicloud_secmaster_alert_rules`
  - `huaweicloud_secmaster_incidents`
  - `huaweicloud_secmaster_playbooks`
  - `huaweicloud_secmaster_workflows`

关键字段：
- `workspace_id`
- `alert_rule_id`
- `incident_id`
- `playbook_id`
- `workflow_id`

### SFS Turbo
- 常见 Resource:
  - `huaweicloud_sfs_turbo`
  - `huaweicloud_sfs_turbo_dir`
  - `huaweicloud_sfs_turbo_perm_rule`
  - `huaweicloud_sfs_turbo_dir_quota`
  - `huaweicloud_sfs_turbo_obs_target`
- 常见 Data source:
  - `huaweicloud_sfs_turbos`
  - `huaweicloud_sfs_turbos_by_tags`
  - `huaweicloud_sfs_turbo_quotas`
  - `huaweicloud_sfs_turbo_share_types`
  - `huaweicloud_sfs_turbo_perm_rules`

关键字段：
- `share_name`
- `share_proto`
- `size`
- `vpc_id`
- `subnet_id`

### SMS
- 常见 Resource:
  - `huaweicloud_sms_migration_project`
  - `huaweicloud_sms_source_server`
  - `huaweicloud_sms_task`
  - `huaweicloud_sms_server_template`
- 常见 Data source:
  - `huaweicloud_sms_migration_projects`
  - `huaweicloud_sms_source_servers`
  - `huaweicloud_sms_tasks`
  - `huaweicloud_sms_server_templates`
  - `huaweicloud_sms_source_server_overview`

关键字段：
- `migration_project_id`
- `source_server_id`
- `template_id`
- `task_id`
- `target_region`

## 资源选择规则
- 如果目标是“创建基础设施”，优先 `resource`
- 如果目标是“复用或引用现网资源”，优先 `data source`
- 若用户没有给出现网资源 ID，但明确要复用，优先先联动 `hcloud` 查询，再决定是用 `data` 还是写成输入变量
