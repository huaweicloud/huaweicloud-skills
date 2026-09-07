# Provider Resource Inventory

这份文档把参考仓库 `docs/resources` 中的资源家族完整搬运到 skill 内部，作为 provider 资源覆盖面的总索引。

来源快照：上游 `huaweicloud/terraform-provider-huaweicloud`，provider changelog 顶部版本 `1.93.0`，日期 `June 12, 2026`。
覆盖统计：1689 个条目，124 个家族。

阅读方式：
- 先按家族名查看 provider 是否覆盖某个方向。
- 再结合 `provider-capability-index.md` 判断是否值得进入主线。
- 再结合 `reference-example-inventory.md` 判断是否已经有成型 example。
- 这份文件是生成索引；维护时用 `scripts/hcloud_terraform_provider_inventory.py --provider-root <provider-source-root>` 从显式传入的 provider docs 重建。

## aad (9)
- `aad_black_white_list`
- `aad_change_specification`
- `aad_domain`
- `aad_domain_certificate`
- `aad_domain_security_protection`
- `aad_forward_rule`
- `aad_instance`
- `aad_policy_black_white_rule`
- `aad_unblock_ip`

## access (3)
- `access_analyzer`
- `access_analyzer_achive_rule`
- `access_analyzer_achive_rule_apply`

## antiddos (4)
- `antiddos_basic`
- `antiddos_default_protection_policy`
- `antiddos_lts_config`
- `antiddos_open_protection`

## aom (21)
- `aom_alarm_action_rule`
- `aom_alarm_group_rule`
- `aom_alarm_inhibit_rule`
- `aom_alarm_rule`
- `aom_alarm_rules_template`
- `aom_alarm_silence_rule`
- `aom_cloud_service_access`
- `aom_cmdb_application`
- `aom_cmdb_component`
- `aom_cmdb_environment`
- `aom_dashboard`
- `aom_dashboards_folder`
- `aom_event_alarm_rule`
- `aom_event_report`
- `aom_message_template`
- `aom_multi_account_aggregation_rule`
- `aom_prom_instance`
- `aom_recording_rule`
- `aom_service_discovery_rule`
- `aom_uniagent_batch_install`
- `aom_uniagent_batch_upgrade`

## aomv4 (1)
- `aomv4_alarm_rule`

## api (3)
- `api_gateway_api`
- `api_gateway_environment`
- `api_gateway_group`

## apig (45)
- `apig_acl_policy`
- `apig_acl_policy_associate`
- `apig_api`
- `apig_api_action`
- `apig_api_batch_action`
- `apig_api_batch_plugins_associate`
- `apig_api_check`
- `apig_api_debug`
- `apig_api_publishment`
- `apig_api_version_unpublish`
- `apig_appcode`
- `apig_application`
- `apig_application_acl`
- `apig_application_ai_api_key`
- `apig_application_authorization`
- `apig_application_quota`
- `apig_application_quota_associate`
- `apig_certificate`
- `apig_certificate_batch_domains_associate`
- `apig_channel`
- `apig_channel_member`
- `apig_channel_member_batch_action`
- `apig_channel_member_group`
- `apig_custom_authorizer`
- `apig_domain_certificate_associate`
- `apig_endpoint_connection_management`
- `apig_endpoint_whitelist`
- `apig_environment`
- `apig_environment_variable`
- `apig_global_certificate_batch_domains_associate`
- `apig_group`
- `apig_group_domain_associate`
- `apig_instance`
- `apig_instance_feature`
- `apig_instance_ingress_port`
- `apig_instance_routes`
- `apig_orchestration_rule`
- `apig_plugin`
- `apig_plugin_associate`
- `apig_response`
- `apig_signature`
- `apig_signature_associate`
- `apig_throttling_policy`
- `apig_throttling_policy_associate`
- `apig_vpc_channel`

## as (11)
- `as_bandwidth_policy`
- `as_configuration`
- `as_execute_policy`
- `as_group`
- `as_instance_attach`
- `as_lifecycle_hook`
- `as_lifecycle_hook_callback`
- `as_notification`
- `as_planned_task`
- `as_policy`
- `as_warm_pool`

## asm (1)
- `asm_mesh`

## bcs (1)
- `bcs_instance`

## blockstorage (1)
- `blockstorage_volume_v2`

## bms (6)
- `bms_instance`
- `bms_instance_password_delete`
- `bms_instance_password_reset`
- `bms_instance_restart`
- `bms_os_reinstall`
- `bms_volume_attach`

## cae (10)
- `cae_application`
- `cae_certificate`
- `cae_component`
- `cae_component_action`
- `cae_component_configurations`
- `cae_domain`
- `cae_environment`
- `cae_notification_rule`
- `cae_timer_rule`
- `cae_vpc_egress`

## cbc (1)
- `cbc_resources_unsubscribe`

## cbh (8)
- `cbh_asset_agency_authorization`
- `cbh_change_instance_type`
- `cbh_delete_fault_instance`
- `cbh_ha_instance`
- `cbh_instance`
- `cbh_reset_login_mode`
- `cbh_rollback_instance`
- `cbh_upgrade_instance`

## cbr (16)
- `cbr_backup_share`
- `cbr_backup_share_accepter`
- `cbr_batch_update_vault`
- `cbr_change_order`
- `cbr_checkpoint`
- `cbr_checkpoint_copy`
- `cbr_migrate`
- `cbr_organization_policy`
- `cbr_policy`
- `cbr_replicate_backup`
- `cbr_restore`
- `cbr_update_backup`
- `cbr_vault`
- `cbr_vault_change_charge_mode`
- `cbr_vault_migrate_resources`
- `cbr_vault_set_resource`

## cc (12)
- `cc_authorization`
- `cc_bandwidth_package`
- `cc_central_network`
- `cc_central_network_attachment`
- `cc_central_network_connection_bandwidth_associate`
- `cc_central_network_policy`
- `cc_central_network_policy_apply`
- `cc_connection`
- `cc_global_connection_bandwidth`
- `cc_global_connection_bandwidth_associate`
- `cc_inter_region_bandwidth`
- `cc_network_instance`

## cce (26)
- `cce_access_policy`
- `cce_addon`
- `cce_autopilot_addon`
- `cce_autopilot_chart`
- `cce_autopilot_cluster`
- `cce_autopilot_cluster_upgrade`
- `cce_autopilot_release`
- `cce_chart`
- `cce_cluster`
- `cce_cluster_certificate_revoke`
- `cce_cluster_log_config`
- `cce_cluster_pod_identity_association`
- `cce_cluster_upgrade`
- `cce_image_cache`
- `cce_namespace`
- `cce_node`
- `cce_node_attach`
- `cce_node_pool`
- `cce_node_pool_nodes_add`
- `cce_node_pool_scale`
- `cce_node_sync`
- `cce_nodes_certificate_rotatecredentials`
- `cce_nodes_remove`
- `cce_partition`
- `cce_pvc`
- `cce_release`

## cci (4)
- `cci_agency`
- `cci_namespace`
- `cci_network`
- `cci_pvc`

## ccm (13)
- `ccm_certificate`
- `ccm_certificate_apply`
- `ccm_certificate_cancel_request`
- `ccm_certificate_deploy`
- `ccm_certificate_import`
- `ccm_certificate_push`
- `ccm_csr`
- `ccm_private_ca`
- `ccm_private_ca_restore`
- `ccm_private_ca_revoke`
- `ccm_private_ca_switch_ocsp`
- `ccm_private_certificate`
- `ccm_private_certificate_revoke`

## cdm (4)
- `cdm_cluster`
- `cdm_cluster_action`
- `cdm_job`
- `cdm_link`

## cdn (13)
- `cdn_billing_option`
- `cdn_cache_preheat`
- `cdn_cache_refresh`
- `cdn_cache_sharing_group`
- `cdn_certificate_associate_domains`
- `cdn_domain`
- `cdn_domain_batch_copy`
- `cdn_domain_owner_verify`
- `cdn_domain_template`
- `cdn_domain_template_apply`
- `cdn_rule_engine_rule`
- `cdn_statistic_configuration`
- `cdn_statistic_subscription_task`

## ces (14)
- `ces_agent_maintenance_task`
- `ces_alarm_template`
- `ces_alarmrule`
- `ces_dashboard`
- `ces_dashboard_widget`
- `ces_event_report`
- `ces_metric_data_add`
- `ces_notification_mask`
- `ces_one_click_alarm`
- `ces_one_click_alarm_reset`
- `ces_one_click_alarm_rule_action`
- `ces_one_click_alarm_rule_policy_action`
- `ces_resource_group`
- `ces_resource_group_alarm_template_async_associate`

## cfw (38)
- `cfw_acl_rule`
- `cfw_add_dns_server`
- `cfw_address_group`
- `cfw_address_group_member`
- `cfw_advanced_ips_rule`
- `cfw_alarm_config`
- `cfw_anti_virus`
- `cfw_batch_delete_acl_rules`
- `cfw_batch_delete_address_group_members`
- `cfw_batch_delete_address_groups`
- `cfw_batch_delete_domain_sets`
- `cfw_batch_delete_service_group_members`
- `cfw_batch_update_acl_rules_action`
- `cfw_batch_update_ips_custom_rules`
- `cfw_black_white_list`
- `cfw_capture_task`
- `cfw_delete_ip_blacklist`
- `cfw_dns_resolution`
- `cfw_domain_name_group`
- `cfw_eip_alarm_whitelist`
- `cfw_eip_all_protection_switch`
- `cfw_eip_auto_protection`
- `cfw_eip_protection`
- `cfw_export_acl_rule`
- `cfw_export_ip_blacklist`
- `cfw_export_logs`
- `cfw_firewall`
- `cfw_import_ip_blacklist`
- `cfw_ip_blacklist_retry`
- `cfw_ip_blacklist_switch`
- `cfw_ips_custom_rule`
- `cfw_ips_rule_mode_change`
- `cfw_lts_log`
- `cfw_protection_rule`
- `cfw_report_profile`
- `cfw_schedule`
- `cfw_service_group`
- `cfw_service_group_member`

## cloudtable (1)
- `cloudtable_cluster`

## cnad (9)
- `cnad_advanced_alarm_notification`
- `cnad_advanced_black_white_list`
- `cnad_advanced_policy`
- `cnad_advanced_policy_associate`
- `cnad_advanced_policy_ip_binding`
- `cnad_advanced_policy_ip_unbinding`
- `cnad_advanced_protected_ip_tag`
- `cnad_advanced_protected_object`
- `cnad_advanced_update_package_name`

## coc (35)
- `coc_alarm_action`
- `coc_alarm_clear`
- `coc_alarm_linked_incident`
- `coc_application`
- `coc_change_delete`
- `coc_change_update`
- `coc_cloud_vendor_account`
- `coc_cloud_vendor_user_resources_sync`
- `coc_component`
- `coc_custom_event_report`
- `coc_diagnosis_task`
- `coc_diagnosis_task_cancel`
- `coc_diagnosis_task_retry`
- `coc_document`
- `coc_document_execute`
- `coc_document_execution_operation`
- `coc_enterprise_project_collection`
- `coc_group`
- `coc_group_resource_relation`
- `coc_group_sync`
- `coc_incident`
- `coc_incident_action`
- `coc_incident_handle`
- `coc_issue`
- `coc_other_resource_uniagent_sync`
- `coc_public_script_execute`
- `coc_resource_uniagent_sync`
- `coc_scheduled_task`
- `coc_script`
- `coc_script_approval`
- `coc_script_execute`
- `coc_script_order_operation`
- `coc_ticket_action`
- `coc_ticket_add`
- `coc_war_room`

## codearts (37)
- `codearts_build_log_download`
- `codearts_build_task`
- `codearts_build_task_action`
- `codearts_build_template`
- `codearts_deploy_application`
- `codearts_deploy_application_copy`
- `codearts_deploy_application_deploy`
- `codearts_deploy_application_group`
- `codearts_deploy_application_group_move`
- `codearts_deploy_application_permission`
- `codearts_deploy_environment`
- `codearts_deploy_environment_permission`
- `codearts_deploy_group`
- `codearts_deploy_group_permission`
- `codearts_deploy_host`
- `codearts_deploy_hosts_copy`
- `codearts_inspector_host`
- `codearts_inspector_host_group`
- `codearts_inspector_website`
- `codearts_inspector_website_scan`
- `codearts_pipeline`
- `codearts_pipeline_action`
- `codearts_pipeline_basic_plugin`
- `codearts_pipeline_by_template`
- `codearts_pipeline_group`
- `codearts_pipeline_group_swap`
- `codearts_pipeline_micro_service`
- `codearts_pipeline_parameter_group`
- `codearts_pipeline_permission`
- `codearts_pipeline_plugin_version`
- `codearts_pipeline_publisher`
- `codearts_pipeline_rule`
- `codearts_pipeline_service_endpoint`
- `codearts_pipeline_tag`
- `codearts_pipeline_template`
- `codearts_project`
- `codearts_repository`

## compute (19)
- `compute_auto_launch_group`
- `compute_eip_associate`
- `compute_floatingip`
- `compute_instance`
- `compute_instance_redeploy`
- `compute_interface_attach`
- `compute_kernel_dump_trigger`
- `compute_keypair`
- `compute_os_change`
- `compute_os_reinstall`
- `compute_password_delete`
- `compute_recycle_bin_server_delete`
- `compute_recycle_bin_server_recover`
- `compute_recycle_policy`
- `compute_scheduled_event_accept`
- `compute_scheduled_event_update`
- `compute_servergroup`
- `compute_template`
- `compute_volume_attach`

## cpcs (6)
- `cpcs_app`
- `cpcs_app_access_key`
- `cpcs_app_cluster_association`
- `cpcs_app_download_access_key`
- `cpcs_cluster_authorize_access_key`
- `cpcs_instance_status_action`

## cph (8)
- `cph_adb_command`
- `cph_phone_property`
- `cph_phone_reset`
- `cph_phone_restart`
- `cph_phone_stop`
- `cph_server`
- `cph_server_restart`
- `cph_share_app`

## cpts (2)
- `cpts_project`
- `cpts_task`

## cs (3)
- `cs_cluster`
- `cs_peering_connect`
- `cs_route`

## csbs (2)
- `csbs_backup`
- `csbs_backup_policy`

## cse (5)
- `cse_microservice`
- `cse_microservice_engine`
- `cse_microservice_engine_configuration`
- `cse_microservice_instance`
- `cse_nacos_namespace`

## csms (8)
- `csms_agency`
- `csms_download_secret_backup`
- `csms_event`
- `csms_restore_secret`
- `csms_scheduled_delete_secret_task`
- `csms_secret`
- `csms_secret_rotate`
- `csms_secret_version_state`

## css (25)
- `css_agency`
- `css_agency_permission`
- `css_ai_ops_setting`
- `css_cluster`
- `css_cluster_az_migrate`
- `css_cluster_node_replace`
- `css_cluster_restart`
- `css_configuration`
- `css_es_core_upgrade`
- `css_es_loadbalancer_config`
- `css_log_setting`
- `css_logstash_cluster`
- `css_logstash_cluster_restart`
- `css_logstash_configuration`
- `css_logstash_connectivity`
- `css_logstash_custom_certificate`
- `css_logstash_custom_template`
- `css_logstash_pipeline`
- `css_manual_log_backup`
- `css_scan_task`
- `css_snapshot`
- `css_snapshot_restore`
- `css_snapshot_setting`
- `css_thesaurus`
- `css_vpcep_connections_update`

## cts (4)
- `cts_configuration`
- `cts_data_tracker`
- `cts_notification`
- `cts_tracker`

## das (19)
- `das_batch_set_sql_switch`
- `das_binlog_parse_task`
- `das_binlog_parse_task_export`
- `das_database_instance_connection`
- `das_database_user`
- `das_dead_lock_switch`
- `das_email_template`
- `das_email_templates_batch_action`
- `das_emails_batch_send`
- `das_full_dead_lock_switch`
- `das_history_transaction_export_task`
- `das_history_transaction_switch`
- `das_instance_group`
- `das_instance_group_assign`
- `das_lock_blocking_switch`
- `das_search_path_switch`
- `das_shared_connection`
- `das_slow_log_export_task`
- `das_sql_limiting_switch`

## dataarts (48)
- `dataarts_architecture_aggregation_logic_table`
- `dataarts_architecture_approvals_batch_action`
- `dataarts_architecture_batch_publish`
- `dataarts_architecture_batch_publishment`
- `dataarts_architecture_batch_unpublish`
- `dataarts_architecture_business_metric`
- `dataarts_architecture_code_table`
- `dataarts_architecture_code_table_values`
- `dataarts_architecture_data_standard`
- `dataarts_architecture_data_standard_template`
- `dataarts_architecture_directory`
- `dataarts_architecture_model`
- `dataarts_architecture_process`
- `dataarts_architecture_reviewer`
- `dataarts_architecture_subject`
- `dataarts_architecture_table_model`
- `dataarts_catalog_metadata_task`
- `dataarts_catalog_metadata_task_action`
- `dataarts_dataservice_api`
- `dataarts_dataservice_api_action`
- `dataarts_dataservice_api_auth`
- `dataarts_dataservice_api_auth_action`
- `dataarts_dataservice_api_debug`
- `dataarts_dataservice_api_publish`
- `dataarts_dataservice_api_publishment`
- `dataarts_dataservice_app`
- `dataarts_dataservice_catalog`
- `dataarts_dataservice_instance_log_dump`
- `dataarts_dataservice_message_approve`
- `dataarts_factory_job`
- `dataarts_factory_job_action`
- `dataarts_factory_job_export`
- `dataarts_factory_job_import`
- `dataarts_factory_resource`
- `dataarts_factory_script`
- `dataarts_factory_script_execute`
- `dataarts_security_data_recognition_rule`
- `dataarts_security_data_recognition_rule_group`
- `dataarts_security_data_secrecy_level`
- `dataarts_security_dynamic_masking_policy`
- `dataarts_security_permission_set`
- `dataarts_security_permission_set_member`
- `dataarts_security_permission_set_privilege`
- `dataarts_security_resource_permission_policy`
- `dataarts_security_workspace_queue_associate`
- `dataarts_studio_data_connection`
- `dataarts_studio_instance`
- `dataarts_studio_workspace_user`

## dbss (4)
- `dbss_audit_risk_rule_action`
- `dbss_ecs_database`
- `dbss_instance`
- `dbss_rds_database`

## dc (11)
- `dc_connect_gateway`
- `dc_connect_gateway_geip_associate`
- `dc_global_gateway`
- `dc_global_gateway_peer_link`
- `dc_global_gateway_route_table`
- `dc_hosted_connect`
- `dc_vif_peer_detection`
- `dc_virtual_gateway`
- `dc_virtual_interface`
- `dc_virtual_interface_accepter`
- `dc_virtual_interface_switchover`

## dcs (36)
- `dcs_account`
- `dcs_all_sessions_kill`
- `dcs_background_task_delete`
- `dcs_background_task_detail`
- `dcs_backup`
- `dcs_backup_import_task`
- `dcs_bigkey_analysis`
- `dcs_center_task_delete`
- `dcs_cluster_replica_switch`
- `dcs_custom_template`
- `dcs_diagnosis_task`
- `dcs_hotkey_analysis`
- `dcs_instance`
- `dcs_instance_bandwidth_modify`
- `dcs_instance_expired_key_scan`
- `dcs_instance_expired_key_scan_task`
- `dcs_instance_migration_task_stop`
- `dcs_instance_minor_version_upgrade`
- `dcs_instance_node_ip_remove`
- `dcs_instance_public_access`
- `dcs_instance_restore`
- `dcs_instance_shard_bandwidth`
- `dcs_login_web_cli`
- `dcs_logout_web_cli`
- `dcs_master_standby_switch`
- `dcs_migration_task_exchange_ip`
- `dcs_migration_task_rollback_ip`
- `dcs_node_priority_config`
- `dcs_node_status_change`
- `dcs_offline_key_analysis`
- `dcs_online_data__migration_task_restart`
- `dcs_online_data_migration_task`
- `dcs_redis_run_log_collect`
- `dcs_sessions_kill`
- `dcs_sessions_query`
- `dcs_web_cli_command_execute`

## ddm (10)
- `ddm_account`
- `ddm_instance`
- `ddm_instance_group`
- `ddm_instance_read_strategy`
- `ddm_instance_restart`
- `ddm_instance_rollback`
- `ddm_instance_upgrade`
- `ddm_logical_sessions_kill`
- `ddm_physical_sessions_kill`
- `ddm_schema`

## dds (30)
- `dds_audit_log_delete`
- `dds_audit_log_policy`
- `dds_backup`
- `dds_backup_download_policy`
- `dds_backup_stop`
- `dds_bind_gateway`
- `dds_collection_restore`
- `dds_database_role`
- `dds_database_user`
- `dds_instance`
- `dds_instance_eip_associate`
- `dds_instance_flavor_update`
- `dds_instance_internal_ip_modify`
- `dds_instance_node_num_update`
- `dds_instance_parameters_modify`
- `dds_instance_restart`
- `dds_instance_restore`
- `dds_instance_storage_space_update`
- `dds_ip_address`
- `dds_lts_log`
- `dds_node_session_kill`
- `dds_parameter_template`
- `dds_parameter_template_apply`
- `dds_parameter_template_compare`
- `dds_parameter_template_copy`
- `dds_parameter_template_reset`
- `dds_primary_standby_switch`
- `dds_readonly_node`
- `dds_recycle_policy`
- `dds_scheduled_task_cancel`

## deh (1)
- `deh_instance`

## dis (1)
- `dis_stream`

## dli (25)
- `dli_agency`
- `dli_database`
- `dli_database_privilege`
- `dli_datasource_auth`
- `dli_datasource_connection`
- `dli_datasource_connection_associate`
- `dli_datasource_connection_privilege`
- `dli_elastic_resource_pool`
- `dli_flink_job_export`
- `dli_flink_job_import`
- `dli_flink_template`
- `dli_flinkjar_job`
- `dli_flinksql_job`
- `dli_flinksql_job_savepoint`
- `dli_flinksql_job_savepoint_import`
- `dli_global_variable`
- `dli_package`
- `dli_permission`
- `dli_queue`
- `dli_spark_job`
- `dli_spark_template`
- `dli_sql_job`
- `dli_sql_job_result_export`
- `dli_sql_template`
- `dli_table`

## dms (54)
- `dms_group`
- `dms_instance`
- `dms_kafka_background_task_delete`
- `dms_kafka_consumer_group`
- `dms_kafka_consumer_group_topic_batch_delete`
- `dms_kafka_instance`
- `dms_kafka_instance_batch_action`
- `dms_kafka_instance_log`
- `dms_kafka_instance_public_access_switch`
- `dms_kafka_instance_rebalance_log`
- `dms_kafka_instance_restart`
- `dms_kafka_instance_upgrade`
- `dms_kafka_message_diagnosis_task`
- `dms_kafka_message_offset_reset`
- `dms_kafka_message_produce`
- `dms_kafka_partition_reassign`
- `dms_kafka_permissions`
- `dms_kafka_recycle_instance_restore`
- `dms_kafka_smart_connect`
- `dms_kafka_smart_connect_task`
- `dms_kafka_smart_connect_task_action`
- `dms_kafka_smart_connector_validate`
- `dms_kafka_topic`
- `dms_kafka_topic_message_batch_delete`
- `dms_kafka_topic_quota`
- `dms_kafka_user`
- `dms_kafka_user_client_quota`
- `dms_kafka_user_password_reset`
- `dms_kafka_volume_auto_expand_configuration`
- `dms_kafkav2_smart_connect_task`
- `dms_queue`
- `dms_rabbitmq_background_task_delete`
- `dms_rabbitmq_exchange`
- `dms_rabbitmq_exchange_associate`
- `dms_rabbitmq_instance`
- `dms_rabbitmq_plugin`
- `dms_rabbitmq_queue`
- `dms_rabbitmq_queue_message_clear`
- `dms_rabbitmq_recycle_instance_restore`
- `dms_rabbitmq_user`
- `dms_rabbitmq_vhost`
- `dms_rabbitmq_volume_auto_expand_configuration`
- `dms_rocketmq_consumer_group`
- `dms_rocketmq_consumption_verify`
- `dms_rocketmq_dead_letter_resend`
- `dms_rocketmq_instance`
- `dms_rocketmq_instance_diagnosis`
- `dms_rocketmq_message_offset_reset`
- `dms_rocketmq_message_send`
- `dms_rocketmq_migration_task`
- `dms_rocketmq_node_batch_restart`
- `dms_rocketmq_topic`
- `dms_rocketmq_user`
- `dms_rocketmq_volume_auto_expand_configuration`

## dns (15)
- `dns_custom_line`
- `dns_endpoint`
- `dns_endpoint_assignment`
- `dns_line_group`
- `dns_private_zone_associate`
- `dns_ptrrecord`
- `dns_recordset`
- `dns_resolver_access_log`
- `dns_resolver_rule`
- `dns_resolver_rule_associate`
- `dns_zone`
- `dns_zone_authorization`
- `dns_zone_authorization_verify`
- `dns_zone_retrieval`
- `dns_zone_retrieval_verify`

## dnsv21 (1)
- `dnsv21_ptrrecord`

## drs (23)
- `drs_backup_migration`
- `drs_batch_delete_jobs`
- `drs_batch_pause_task`
- `drs_batch_retry_task`
- `drs_batch_set_definer`
- `drs_check_data_filter`
- `drs_compare_job_cancel`
- `drs_compare_policy`
- `drs_connection`
- `drs_download_batch_create_template`
- `drs_driver_delete`
- `drs_job`
- `drs_job_clone`
- `drs_job_configuration_update`
- `drs_job_primary_standby_switch`
- `drs_job_v5`
- `drs_jobs_batch_stop`
- `drs_lts_config`
- `drs_object_compare`
- `drs_pwd_batch_modify`
- `drs_smn_batch_set`
- `drs_stop_job`
- `drs_update_data_progress_rules`

## dsc (3)
- `dsc_alarm_notification`
- `dsc_asset_obs`
- `dsc_instance`

## dws (28)
- `dws_alarm_subscription`
- `dws_cluster`
- `dws_cluster_action`
- `dws_cluster_eip_associate`
- `dws_cluster_elb_associate`
- `dws_cluster_exception_rule`
- `dws_cluster_public_domain_associate`
- `dws_cluster_restart`
- `dws_cluster_user`
- `dws_database_schema_adjust_action`
- `dws_disaster_recovery_task`
- `dws_event_subscription`
- `dws_ext_data_source`
- `dws_logical_cluster`
- `dws_logical_cluster_plan`
- `dws_logical_cluster_restart`
- `dws_om_account_action`
- `dws_parameter_configurations`
- `dws_snapshot`
- `dws_snapshot_copy`
- `dws_snapshot_policy`
- `dws_workload_configuration`
- `dws_workload_plan`
- `dws_workload_plan_execution`
- `dws_workload_plan_stage`
- `dws_workload_queue`
- `dws_workload_queue_update_action`
- `dws_workload_queue_user_associate`

## eg (10)
- `eg_connection`
- `eg_custom_event_channel`
- `eg_custom_event_source`
- `eg_endpoint`
- `eg_event_batch_action`
- `eg_event_stream`
- `eg_event_subscription`
- `eg_event_subscription_batch_action`
- `eg_event_subscription_target`
- `eg_eventrouter_cluster`

## eip (1)
- `eip_bandwidth_associate`

## elb (21)
- `elb_active_standby_pool`
- `elb_certificate`
- `elb_certificate_private_key_echo`
- `elb_domain_address`
- `elb_domain_resolution`
- `elb_ipgroup`
- `elb_l7policy`
- `elb_l7rule`
- `elb_listener`
- `elb_listener_copy`
- `elb_loadbalancer`
- `elb_loadbalancer_copy`
- `elb_logtank`
- `elb_member`
- `elb_member_check_task`
- `elb_monitor`
- `elb_pool`
- `elb_recycle_bin`
- `elb_recycle_bin_loadbalancer_delete`
- `elb_recycle_bin_loadbalancer_recover`
- `elb_security_policy`

## enterprise (3)
- `enterprise_project`
- `enterprise_project_action`
- `enterprise_project_authority`

## er (8)
- `er_association`
- `er_attachment_accepter`
- `er_flow_log`
- `er_instance`
- `er_propagation`
- `er_route_table`
- `er_static_route`
- `er_vpc_attachment`

## esw (3)
- `esw_connection`
- `esw_connection_vport_bind`
- `esw_instance`

## evs (14)
- `evs_recycle_bin_policy`
- `evs_recycle_bin_volume_delete`
- `evs_recycle_bin_volume_revert`
- `evs_snapshot`
- `evs_snapshot_group`
- `evs_snapshot_metadata`
- `evs_snapshot_rollback`
- `evs_unsubscribe_prepaid_volume`
- `evs_volume`
- `evs_volume_metadata`
- `evs_volume_retype`
- `evs_volume_transfer`
- `evs_volume_transfer_accepter`
- `evs_volumes_batch_expand`

## evsv3 (4)
- `evsv3_snapshot`
- `evsv3_volume`
- `evsv3_volume_transfer`
- `evsv3_volume_transfer_accepter`

## evsv5 (2)
- `evsv5_snapshot`
- `evsv5_snapshot_rollback`

## fgs (14)
- `fgs_application`
- `fgs_async_invoke_configuration`
- `fgs_async_log_configuration`
- `fgs_dependency`
- `fgs_dependency_version`
- `fgs_function`
- `fgs_function_event`
- `fgs_function_topping`
- `fgs_function_tracing_configuration`
- `fgs_function_trigger`
- `fgs_function_trigger_status`
- `fgs_lts_log_enable`
- `fgs_trigger`
- `fgs_vpc_endpoint`

## fw (3)
- `fw_firewall_group_v2`
- `fw_policy_v2`
- `fw_rule_v2`

## ga (7)
- `ga_accelerator`
- `ga_access_log`
- `ga_address_group`
- `ga_endpoint`
- `ga_endpoint_group`
- `ga_health_check`
- `ga_listener`

## gaussdb (42)
- `gaussdb_asp_collect`
- `gaussdb_backup`
- `gaussdb_backup_stop`
- `gaussdb_cassandra_instance`
- `gaussdb_client_auth_config`
- `gaussdb_client_auth_config_restore`
- `gaussdb_database`
- `gaussdb_dr_configuration_reset`
- `gaussdb_dr_drill`
- `gaussdb_dr_instance_primary_role_switch`
- `gaussdb_dr_instance_to_primary`
- `gaussdb_dr_log_cache`
- `gaussdb_dr_record_delete`
- `gaussdb_dr_relationship`
- `gaussdb_dr_relationship_reestablish`
- `gaussdb_eip_associate`
- `gaussdb_influx_instance`
- `gaussdb_instance`
- `gaussdb_instance_node_startup`
- `gaussdb_instance_node_stop`
- `gaussdb_instance_password_reset`
- `gaussdb_instance_plugin_license_config`
- `gaussdb_instance_restart`
- `gaussdb_instance_upgrade`
- `gaussdb_mongo_instance`
- `gaussdb_parameter_template`
- `gaussdb_parameter_template_apply`
- `gaussdb_parameter_template_compare`
- `gaussdb_parameter_template_reset`
- `gaussdb_primary_standby_switch`
- `gaussdb_quota`
- `gaussdb_read_replica`
- `gaussdb_recycling_policy`
- `gaussdb_redis_eip_associate`
- `gaussdb_redis_instance`
- `gaussdb_restore`
- `gaussdb_schema`
- `gaussdb_sql_throttling_task`
- `gaussdb_sync_sql_throttling_task`
- `gaussdb_task_delete`
- `gaussdb_wdr_snapshot`
- `gaussdb_wdr_snapshot_collect`

## geminidb (20)
- `geminidb_account`
- `geminidb_backup`
- `geminidb_backup_stop`
- `geminidb_command_disable`
- `geminidb_database_operation`
- `geminidb_dr_switchover_configuration`
- `geminidb_eip_bind`
- `geminidb_instance`
- `geminidb_instance_restart`
- `geminidb_memory_mapping`
- `geminidb_memory_rule`
- `geminidb_node_session_kill`
- `geminidb_parameter_template`
- `geminidb_parameter_template_compare`
- `geminidb_parameter_template_copy`
- `geminidb_parameter_template_reset`
- `geminidb_primary_standby_switch`
- `geminidb_recycling_policy`
- `geminidb_scheduled_task_cancel`
- `geminidb_sessions_close`

## ges (3)
- `ges_backup`
- `ges_graph`
- `ges_metadata`

## global (6)
- `global_eip`
- `global_eip_associate`
- `global_eip_internet_bandwidth_associate`
- `global_eip_segment`
- `global_eip_segment_bandwidth_associate`
- `global_internet_bandwidth`

## hss (50)
- `hss_antivirus_create_pay_per_scan_task`
- `hss_antivirus_create_virus_scan_task`
- `hss_antivirus_pay_per_scan_switch_status`
- `hss_app_whitelist_policy_process`
- `hss_asset_assign_task`
- `hss_asset_manual_collect`
- `hss_associated_asset_importance`
- `hss_change_host_ignore_status`
- `hss_cicd_configuration`
- `hss_close_honeypot_port_policy`
- `hss_cluster_protect_switch_mode`
- `hss_container_export_task`
- `hss_container_kubernetes_cluster_daemonset`
- `hss_container_kubernetes_cluster_protection_enable`
- `hss_container_kubernetes_sync_mccs`
- `hss_container_network_cluster_sync`
- `hss_container_network_policy_sync`
- `hss_container_sync_cluster_information`
- `hss_custom_rule`
- `hss_event_alarm_white_list_delete`
- `hss_event_login_white_list`
- `hss_event_system_user_white_list`
- `hss_event_unblock_ip`
- `hss_file_download`
- `hss_honeypot_port_policy`
- `hss_host_batch_config`
- `hss_host_group`
- `hss_host_manual_detection`
- `hss_host_protection`
- `hss_ignore_failed_pcc`
- `hss_image_baseline_change_ewp`
- `hss_image_batch_scan`
- `hss_login_common_location`
- `hss_login_white_ip`
- `hss_modify_webtamper_protection_policy`
- `hss_modify_webtamper_rasp_path`
- `hss_policy_group`
- `hss_policy_group_deploy`
- `hss_policy_switch_status`
- `hss_quota`
- `hss_ransomware_protection_policy`
- `hss_rasp_protection_policy`
- `hss_setting_two_factor_login_config`
- `hss_switch_honeypot_port_policy`
- `hss_vulnerability_history_export_task`
- `hss_vulnerability_information_export`
- `hss_vulnerability_scan_policy`
- `hss_vulnerability_scan_task`
- `hss_vulnerability_task_user_trace`
- `hss_webtamper_protection`

## identity (25)
- `identity_access_key`
- `identity_acl`
- `identity_agency`
- `identity_group`
- `identity_group_membership`
- `identity_group_role_assignment`
- `identity_login_policy`
- `identity_password_policy`
- `identity_project`
- `identity_protection_policy`
- `identity_provider`
- `identity_provider_conversion`
- `identity_provider_mapping`
- `identity_provider_protocol`
- `identity_role`
- `identity_temporary_access_key`
- `identity_token_with_id_token`
- `identity_unscoped_token_saml`
- `identity_unscoped_token_with_id_token`
- `identity_user`
- `identity_user_info`
- `identity_user_password`
- `identity_user_role_assignment`
- `identity_user_token`
- `identity_virtual_mfa_device`

## identitycenter (29)
- `identitycenter_access_control_attribute_configuration`
- `identitycenter_account_assignment`
- `identitycenter_application_assignment`
- `identitycenter_application_certificate`
- `identitycenter_application_instance`
- `identitycenter_application_instance_profile_delete`
- `identitycenter_bearer_token`
- `identitycenter_custom_policy_attachment`
- `identitycenter_custom_role_attachment`
- `identitycenter_email_verify`
- `identitycenter_group`
- `identitycenter_group_membership`
- `identitycenter_identity_provider`
- `identitycenter_identity_provider_certificate`
- `identitycenter_instance`
- `identitycenter_mfa_management_setting`
- `identitycenter_password_policy`
- `identitycenter_password_reset`
- `identitycenter_permission_set`
- `identitycenter_profile_disassociate`
- `identitycenter_provision_permission_set`
- `identitycenter_registered_region`
- `identitycenter_service_provider_certificate`
- `identitycenter_sso_configuration`
- `identitycenter_system_identity_policy_attachment`
- `identitycenter_system_policy_attachment`
- `identitycenter_tenant`
- `identitycenter_user`
- `identitycenter_user_session_delete`

## identityv5 (16)
- `identityv5_access_key`
- `identityv5_asymmetric_signature_switch`
- `identityv5_group`
- `identityv5_group_membership`
- `identityv5_login_policy`
- `identityv5_login_profile`
- `identityv5_password_policy`
- `identityv5_policy`
- `identityv5_policy_default_version`
- `identityv5_policy_group_attach`
- `identityv5_policy_user_attach`
- `identityv5_resource_tag`
- `identityv5_service_linked_agency`
- `identityv5_user`
- `identityv5_user_password`
- `identityv5_virtual_mfa_device`

## iec (10)
- `iec_eip`
- `iec_keypair`
- `iec_network_acl`
- `iec_network_acl_rule`
- `iec_security_group`
- `iec_security_group_rule`
- `iec_server`
- `iec_vip`
- `iec_vpc`
- `iec_vpc_subnet`

## images (5)
- `images_image`
- `images_image_copy`
- `images_image_share`
- `images_image_share_accepter`
- `images_image_v2`

## ims (13)
- `ims_cbr_whole_image`
- `ims_ecs_system_image`
- `ims_ecs_whole_image`
- `ims_evs_data_image`
- `ims_evs_system_image`
- `ims_image_export`
- `ims_image_metadata`
- `ims_image_registration`
- `ims_obs_data_image`
- `ims_obs_iso_image`
- `ims_obs_system_image`
- `ims_quickimport_data_image`
- `ims_quickimport_system_image`

## imsv21 (1)
- `imsv21_image_export`

## iotda (19)
- `iotda_access_credential`
- `iotda_amqp`
- `iotda_batchtask`
- `iotda_batchtask_file`
- `iotda_custom_authentication`
- `iotda_data_backlog_policy`
- `iotda_data_flow_control_policy`
- `iotda_dataforwarding_rule`
- `iotda_device`
- `iotda_device_async_command`
- `iotda_device_certificate`
- `iotda_device_group`
- `iotda_device_linkage_rule`
- `iotda_device_message`
- `iotda_device_policy`
- `iotda_device_proxy`
- `iotda_product`
- `iotda_space`
- `iotda_upgrade_package`

## kms (20)
- `kms_alias`
- `kms_alias_associate`
- `kms_cancel_key_deletion`
- `kms_data_encrypt_decrypt`
- `kms_datakey_without_plaintext`
- `kms_decrypt_datakey`
- `kms_dedicated_keystore`
- `kms_ec_datakey_pair`
- `kms_encrypt_datakey`
- `kms_generate_mac`
- `kms_grant`
- `kms_key`
- `kms_key_material`
- `kms_key_replicate`
- `kms_key_update_primary_region`
- `kms_retire_grant`
- `kms_rsa_datakey_pair`
- `kms_sign`
- `kms_verify_mac`
- `kms_verify_sign`

## kps (8)
- `kps_batch_export_private_key`
- `kps_batch_import_keypair`
- `kps_export_private_key`
- `kps_failed_task_delete`
- `kps_failed_tasks_delete`
- `kps_keypair`
- `kps_keypair_associate`
- `kps_keypair_disassociate`

## lakeformation (3)
- `lakeformation_instance`
- `lakeformation_instance_default_update`
- `lakeformation_instance_recover`

## lb (9)
- `lb_certificate`
- `lb_l7policy`
- `lb_l7rule`
- `lb_listener`
- `lb_loadbalancer`
- `lb_member`
- `lb_monitor`
- `lb_pool`
- `lb_whitelist`

## live (17)
- `live_bucket_authorization`
- `live_channel`
- `live_disable_push_stream`
- `live_domain`
- `live_geo_blocking`
- `live_hls_configuration`
- `live_ip_acl`
- `live_notification_configuration`
- `live_origin_pull_configuration`
- `live_record_callback`
- `live_recording`
- `live_referer_validation`
- `live_snapshot`
- `live_stream_delay`
- `live_transcoding`
- `live_url_authentication`
- `live_url_validation`

## lts (22)
- `lts_aom_access`
- `lts_cce_access`
- `lts_cross_account_access`
- `lts_group`
- `lts_host_access`
- `lts_host_group`
- `lts_keywords_alarm_rule`
- `lts_log_collection_switch`
- `lts_log_converge`
- `lts_log_converge_switch`
- `lts_metric_rule`
- `lts_notification_template`
- `lts_register_kafka_instance`
- `lts_search_criteria`
- `lts_sql_alarm_rule`
- `lts_stream`
- `lts_stream_index_configuration`
- `lts_struct_template`
- `lts_structing_template`
- `lts_structuring_custom_configuration`
- `lts_transfer`
- `lts_waf_access`

## mapreduce (9)
- `mapreduce_cluster`
- `mapreduce_cluster_component_batch_add`
- `mapreduce_cluster_default_tags_switch`
- `mapreduce_cluster_node_batch_expand`
- `mapreduce_cluster_node_batch_shrink`
- `mapreduce_data_connection`
- `mapreduce_job`
- `mapreduce_scaling_policy`
- `mapreduce_scaling_policy_v2`

## meeting (3)
- `meeting_admin_assignment`
- `meeting_conference`
- `meeting_user`

## metastudio (1)
- `metastudio_instance`

## modelarts (18)
- `modelarts_algorithm`
- `modelarts_authorization`
- `modelarts_dataset`
- `modelarts_dataset_version`
- `modelarts_devserver`
- `modelarts_devserver_action`
- `modelarts_model`
- `modelarts_network`
- `modelarts_notebook`
- `modelarts_notebook_image_store`
- `modelarts_notebook_mount_storage`
- `modelarts_resource_pool`
- `modelarts_resource_pool_node_batch_resize`
- `modelarts_service`
- `modelarts_training_experiment`
- `modelarts_training_image_store`
- `modelarts_training_job`
- `modelarts_workspace`

## modelartsv2 (14)
- `modelartsv2_node_batch_delete`
- `modelartsv2_node_batch_lock`
- `modelartsv2_node_batch_migrate`
- `modelartsv2_node_batch_reboot`
- `modelartsv2_node_batch_reset`
- `modelartsv2_node_batch_unlock`
- `modelartsv2_node_batch_unsubscribe`
- `modelartsv2_service`
- `modelartsv2_service_action`
- `modelartsv2_workflow`
- `modelartsv2_workflow_execution`
- `modelartsv2_workflow_execution_action`
- `modelartsv2_workflow_schedule`
- `modelartsv2_workflow_subscription`

## mpc (2)
- `mpc_transcoding_template`
- `mpc_transcoding_template_group`

## mrs (2)
- `mrs_cluster`
- `mrs_job`

## nat (7)
- `nat_dnat_rule`
- `nat_gateway`
- `nat_private_dnat_rule`
- `nat_private_gateway`
- `nat_private_snat_rule`
- `nat_private_transit_ip`
- `nat_snat_rule`

## natv3 (1)
- `natv3_gateway`

## network (2)
- `network_acl`
- `network_acl_rule`

## networking (11)
- `networking_floatingip_v2`
- `networking_network_v2`
- `networking_port_v2`
- `networking_router_interface_v2`
- `networking_router_route_v2`
- `networking_router_v2`
- `networking_secgroup`
- `networking_secgroup_rule`
- `networking_subnet_v2`
- `networking_vip`
- `networking_vip_associate`

## obs (8)
- `obs_bucket`
- `obs_bucket_acl`
- `obs_bucket_bpa`
- `obs_bucket_object`
- `obs_bucket_object_acl`
- `obs_bucket_object_restore`
- `obs_bucket_policy`
- `obs_bucket_replication`

## oms (4)
- `oms_migration_sync_task`
- `oms_migration_task`
- `oms_migration_task_group`
- `oms_sync_event`

## organizations (14)
- `organizations_account`
- `organizations_account_associate`
- `organizations_account_invite`
- `organizations_account_invite_accepter`
- `organizations_account_invite_decliner`
- `organizations_delegated_administrator`
- `organizations_dry_run_policy`
- `organizations_dry_run_policy_entity_attach`
- `organizations_organization`
- `organizations_organizational_unit`
- `organizations_policy`
- `organizations_policy_attach`
- `organizations_policy_dry_run_configuration`
- `organizations_trusted_service`

## ram (4)
- `ram_organization`
- `ram_resource_share`
- `ram_resource_share_accepter`
- `ram_resource_share_permission`

## rds (66)
- `rds_agent_job_modify`
- `rds_agent_job_restart`
- `rds_agent_job_switch`
- `rds_backup`
- `rds_backup_stop`
- `rds_cross_region_backup_strategy`
- `rds_database_logs_shrinking`
- `rds_database_statistics_update`
- `rds_distribution`
- `rds_dr_instance_dr_capability`
- `rds_dr_instance_to_primary`
- `rds_event_operate`
- `rds_extend_log_link`
- `rds_instance`
- `rds_instance_eip_associate`
- `rds_instance_minor_version_upgrade`
- `rds_instance_restart`
- `rds_instant_task_delete`
- `rds_intelligent_session_kill`
- `rds_lts_config`
- `rds_mysql_account`
- `rds_mysql_binlog`
- `rds_mysql_database`
- `rds_mysql_database_privilege`
- `rds_mysql_database_table_restore`
- `rds_mysql_proxy`
- `rds_mysql_proxy_restart`
- `rds_notify_replace_node`
- `rds_parametergroup`
- `rds_parametergroup_apply`
- `rds_parametergroup_compare`
- `rds_parametergroup_copy`
- `rds_parametergroup_reset`
- `rds_pg_account`
- `rds_pg_account_privileges`
- `rds_pg_account_roles`
- `rds_pg_database`
- `rds_pg_database_privilege`
- `rds_pg_database_restore`
- `rds_pg_hba`
- `rds_pg_plugin`
- `rds_pg_plugin_parameter`
- `rds_pg_plugin_update`
- `rds_pg_schema`
- `rds_pg_sql_limit`
- `rds_pg_table_restore`
- `rds_primary_instance_dr_capability`
- `rds_primary_standby_switch`
- `rds_pub_and_sub_metadata_sync`
- `rds_publication`
- `rds_publication_snapshot_regenerate`
- `rds_read_replica_instance`
- `rds_recycling_policy`
- `rds_restore`
- `rds_restore_read_replica_database`
- `rds_sql_audit`
- `rds_sql_statistics_view_reset`
- `rds_sqlserver_account`
- `rds_sqlserver_database`
- `rds_sqlserver_database_copy`
- `rds_sqlserver_database_privilege`
- `rds_standby_instance_rebuild`
- `rds_subscription`
- `rds_subscription_regenerate`
- `rds_unlock_node_readonly_status`
- `rds_wal_log_replay_switch`

## rfs (16)
- `rfs_apply_execution_plan`
- `rfs_continue_deploy_stack`
- `rfs_execution_plan`
- `rfs_execution_plan_v2`
- `rfs_private_hook`
- `rfs_private_module`
- `rfs_private_module_version`
- `rfs_private_provider`
- `rfs_private_provider_version`
- `rfs_stack`
- `rfs_stack_rollback`
- `rfs_stack_set`
- `rfs_stack_set_deployment`
- `rfs_template`
- `rfs_template_analysis_variables`
- `rfs_template_version`

## rgc (8)
- `rgc_account`
- `rgc_account_enroll`
- `rgc_best_practice`
- `rgc_control`
- `rgc_landing_zone`
- `rgc_organizational_unit`
- `rgc_organizational_unit_register`
- `rgc_template`

## rms (14)
- `rms_advanced_query`
- `rms_assignment_package`
- `rms_organizational_assignment_package`
- `rms_organizational_policy_assignment`
- `rms_policy_assignment`
- `rms_policy_assignment_evaluate`
- `rms_policy_assignment_evaluate_result_update`
- `rms_remediation_configuration`
- `rms_remediation_exception`
- `rms_remediation_execution`
- `rms_resource_aggregation_authorization`
- `rms_resource_aggregation_pending_request_delete`
- `rms_resource_aggregator`
- `rms_resource_recorder`

## scm (1)
- `scm_certificate`

## sdrs (12)
- `sdrs_delete_all_group_failure_jobs`
- `sdrs_delete_failure_job`
- `sdrs_delete_specified_group_failure_jobs`
- `sdrs_drill`
- `sdrs_protected_instance`
- `sdrs_protected_instance_add_nic`
- `sdrs_protected_instance_delete_nic`
- `sdrs_protected_instance_resize`
- `sdrs_protection_group`
- `sdrs_replication_attach`
- `sdrs_replication_pair`
- `sdrs_resize_replication`

## secmaster (44)
- `secmaster_alert`
- `secmaster_alert_convert_incident`
- `secmaster_alert_rule`
- `secmaster_alert_rule_simulation`
- `secmaster_asset`
- `secmaster_catalogue`
- `secmaster_clone_playbook_version`
- `secmaster_cloud_log_resource`
- `secmaster_collect_config`
- `secmaster_collector_channel_group`
- `secmaster_collector_channel_operation`
- `secmaster_collector_parser`
- `secmaster_component_template`
- `secmaster_configuration_dictionary`
- `secmaster_data_object_relations`
- `secmaster_dataspace`
- `secmaster_delete_nodes`
- `secmaster_delete_policies`
- `secmaster_incident`
- `secmaster_indicator`
- `secmaster_layout_field`
- `secmaster_module`
- `secmaster_node_expansion`
- `secmaster_operation_connection`
- `secmaster_pipe_consumption`
- `secmaster_playbook`
- `secmaster_playbook_action`
- `secmaster_playbook_approval`
- `secmaster_playbook_enable`
- `secmaster_playbook_instance_operation`
- `secmaster_playbook_rule`
- `secmaster_playbook_version`
- `secmaster_playbook_version_action`
- `secmaster_post_paid_order`
- `secmaster_search_condition`
- `secmaster_soc_mapping_clone`
- `secmaster_soc_mapping_delete`
- `secmaster_soc_mapping_status`
- `secmaster_update_workflow_instance`
- `secmaster_workflow`
- `secmaster_workflow_action`
- `secmaster_workflow_version`
- `secmaster_workflow_version_approval`
- `secmaster_workflow_version_validation`

## servicestage (6)
- `servicestage_application`
- `servicestage_component`
- `servicestage_component_instance`
- `servicestage_environment`
- `servicestage_repo_password_authorization`
- `servicestage_repo_token_authorization`

## servicestagev3 (11)
- `servicestagev3_application`
- `servicestagev3_application_configuration`
- `servicestagev3_component`
- `servicestagev3_component_action`
- `servicestagev3_component_refresh`
- `servicestagev3_configuration`
- `servicestagev3_configuration_group`
- `servicestagev3_environment`
- `servicestagev3_environment_associate`
- `servicestagev3_runtime_stack`
- `servicestagev3_runtime_stack_batch_release`

## sfs (12)
- `sfs_access_rule`
- `sfs_file_system`
- `sfs_turbo`
- `sfs_turbo_ad_domain`
- `sfs_turbo_change_charge_mode`
- `sfs_turbo_cold_data_eviction`
- `sfs_turbo_data_task`
- `sfs_turbo_dir`
- `sfs_turbo_dir_quota`
- `sfs_turbo_du_task`
- `sfs_turbo_obs_target`
- `sfs_turbo_perm_rule`

## smn (12)
- `smn_logtank`
- `smn_message_detection`
- `smn_message_publish`
- `smn_message_template`
- `smn_notify_policy`
- `smn_subscription`
- `smn_subscription_filter_policy`
- `smn_topic`
- `smn_topic_attributes`
- `smn_topic_subscriber`
- `smn_topic_subscription`
- `smn_topic_unsubscription`

## sms (10)
- `sms_migration_project`
- `sms_migration_project_default`
- `sms_server_template`
- `sms_source_server`
- `sms_source_server_command_result_report`
- `sms_task`
- `sms_task_consistency_result_report`
- `sms_task_log_upload`
- `sms_task_network_check_info_report`
- `sms_task_progress_report`

## swr (34)
- `swr_agency`
- `swr_enterprise_domain_name`
- `swr_enterprise_image_signature_policy`
- `swr_enterprise_image_signature_policy_execute`
- `swr_enterprise_immutable_tag_rule`
- `swr_enterprise_instance`
- `swr_enterprise_instance_artifact_delete`
- `swr_enterprise_instance_artifact_manual_scan`
- `swr_enterprise_instance_artifact_tag_delete`
- `swr_enterprise_instance_registry`
- `swr_enterprise_job_delete`
- `swr_enterprise_long_term_credential`
- `swr_enterprise_namespace`
- `swr_enterprise_private_network_access_control`
- `swr_enterprise_replication_policy`
- `swr_enterprise_replication_policy_execute`
- `swr_enterprise_replication_policy_execution_stop`
- `swr_enterprise_repository_delete`
- `swr_enterprise_repository_update`
- `swr_enterprise_retention_policy`
- `swr_enterprise_retention_policy_execute`
- `swr_enterprise_temporary_credential`
- `swr_enterprise_trigger`
- `swr_image_auto_sync`
- `swr_image_manual_sync`
- `swr_image_permissions`
- `swr_image_retention_policy`
- `swr_image_trigger`
- `swr_organization`
- `swr_organization_permissions`
- `swr_repository`
- `swr_repository_sharing`
- `swr_repository_tag`
- `swr_temporary_login_command`

## taurusdb (31)
- `taurusdb_account`
- `taurusdb_account_privilege`
- `taurusdb_backup`
- `taurusdb_backups_batch_delete`
- `taurusdb_database`
- `taurusdb_eip_associate`
- `taurusdb_htap_sessions_kill`
- `taurusdb_htap_starrocks_instance_restart`
- `taurusdb_htap_starrocks_instance_upgrade`
- `taurusdb_htap_starrocks_node_restart`
- `taurusdb_instance`
- `taurusdb_instance_node_config`
- `taurusdb_instance_restart`
- `taurusdb_instance_upgrade`
- `taurusdb_instant_task_delete`
- `taurusdb_lts_log`
- `taurusdb_node_sessions_kill`
- `taurusdb_parameter_template`
- `taurusdb_parameter_template_apply`
- `taurusdb_parameter_template_compare`
- `taurusdb_primary_standby_switch`
- `taurusdb_proxy`
- `taurusdb_proxy_restart`
- `taurusdb_quota`
- `taurusdb_recycling_policy`
- `taurusdb_restore`
- `taurusdb_scheduled_task_cancel`
- `taurusdb_scheduled_task_delete`
- `taurusdb_sql_auto_throttling`
- `taurusdb_sql_control_rule`
- `taurusdb_table_restore`

## tms (2)
- `tms_resource_tags`
- `tms_tags`

## ucs (3)
- `ucs_cluster`
- `ucs_fleet`
- `ucs_policy`

## vbs (2)
- `vbs_backup`
- `vbs_backup_policy`

## vod (4)
- `vod_media_asset`
- `vod_media_category`
- `vod_transcoding_template_group`
- `vod_watermark_template`

## vpc (24)
- `vpc`
- `vpc_address_group`
- `vpc_bandwidth`
- `vpc_bandwidth_associate`
- `vpc_eip`
- `vpc_eip_associate`
- `vpc_eip_bandwidth_rule`
- `vpc_eip_update_publicip_pool`
- `vpc_eipv3_associate`
- `vpc_flow_log`
- `vpc_internet_gateway`
- `vpc_network_acl`
- `vpc_network_interface`
- `vpc_peering_connection`
- `vpc_peering_connection_accepter`
- `vpc_route`
- `vpc_route_table`
- `vpc_sub_network_interface`
- `vpc_subnet`
- `vpc_subnet_cidr_reservation`
- `vpc_subnet_private_ip`
- `vpc_traffic_mirror_filter`
- `vpc_traffic_mirror_filter_rule`
- `vpc_traffic_mirror_session`

## vpcep (7)
- `vpcep_approval`
- `vpcep_endpoint`
- `vpcep_endpoint_upgrade`
- `vpcep_service`
- `vpcep_service_add_servers`
- `vpcep_service_connection_update`
- `vpcep_service_upgrade`

## vpn (15)
- `vpn_access_policy`
- `vpn_client_ca_certificate`
- `vpn_connection`
- `vpn_connection_health_check`
- `vpn_connection_reset`
- `vpn_customer_gateway`
- `vpn_gateway`
- `vpn_gateway_job_delete`
- `vpn_gateway_upgrade`
- `vpn_p2c_gateway_connection_disconnect`
- `vpn_p2c_gateway_job_delete`
- `vpn_p2c_gateway_upgrade`
- `vpn_server`
- `vpn_user`
- `vpn_user_group`

## vpnaas (5)
- `vpnaas_endpoint_group_v2`
- `vpnaas_ike_policy_v2`
- `vpnaas_ipsec_policy_v2`
- `vpnaas_service_v2`
- `vpnaas_site_connection_v2`

## waf (42)
- `waf_address_group`
- `waf_alarm_notification`
- `waf_batch_create_antileakage_rules`
- `waf_batch_create_antitamper_rules`
- `waf_batch_create_cc_rules`
- `waf_batch_create_custom_rules`
- `waf_batch_create_geoip_rules`
- `waf_batch_create_ignore_rules`
- `waf_batch_create_ip_reputation_rules`
- `waf_batch_create_privacy_rules`
- `waf_batch_create_whiteblackip_rules`
- `waf_batch_delete_alarm_notifications`
- `waf_batch_update_whiteblackip_rules`
- `waf_cc_protection_rule_batch_delete`
- `waf_certificate`
- `waf_cloud_instance`
- `waf_dedicated_agency`
- `waf_dedicated_domain`
- `waf_dedicated_instance`
- `waf_dedicated_instance_action`
- `waf_domain`
- `waf_domain_associate_certificate`
- `waf_domain_route_update`
- `waf_geo_ip_rule_batch_update`
- `waf_ip_intelligence_rule`
- `waf_migrate_domain`
- `waf_modify_alarm_notification`
- `waf_policies_batch_delete`
- `waf_policy`
- `waf_policy_copy`
- `waf_reference_table`
- `waf_rule_anti_crawler`
- `waf_rule_blacklist`
- `waf_rule_cc_protection`
- `waf_rule_data_masking`
- `waf_rule_geolocation_access_control`
- `waf_rule_global_protection_whitelist`
- `waf_rule_information_leakage_prevention`
- `waf_rule_known_attack_source`
- `waf_rule_precise_protection`
- `waf_rule_web_tamper_protection`
- `waf_rule_web_tamper_protection_refresh`

## workspace (62)
- `workspace_access_policy`
- `workspace_app_application_batch_action`
- `workspace_app_application_batch_attach`
- `workspace_app_application_batch_publish`
- `workspace_app_application_batch_unpublish`
- `workspace_app_application_publishment`
- `workspace_app_bucket_authorize`
- `workspace_app_group`
- `workspace_app_group_authorization`
- `workspace_app_group_authorization_notification_resend`
- `workspace_app_hda_batch_upgrade`
- `workspace_app_image`
- `workspace_app_image_server`
- `workspace_app_nas_storage`
- `workspace_app_personal_folders`
- `workspace_app_policy_group`
- `workspace_app_policy_template`
- `workspace_app_schedule_task`
- `workspace_app_server`
- `workspace_app_server_action`
- `workspace_app_server_batch_action`
- `workspace_app_server_batch_migrate`
- `workspace_app_server_group`
- `workspace_app_server_group_batch_disassociate`
- `workspace_app_server_group_scaling_policy`
- `workspace_app_service_action`
- `workspace_app_shared_folder`
- `workspace_app_shared_folder_assign`
- `workspace_app_storage_policy`
- `workspace_app_warehouse_application`
- `workspace_app_warehouse_bucket_authorize`
- `workspace_application`
- `workspace_application_batch_authorize`
- `workspace_application_batch_auto_install`
- `workspace_application_rule`
- `workspace_application_rule_restriction`
- `workspace_application_rule_restriction_setting`
- `workspace_application_rule_restriction_switch`
- `workspace_application_visibility_batch_action`
- `workspace_assist_auth_configuration_object_management`
- `workspace_bucket_authorize`
- `workspace_desktop`
- `workspace_desktop_maintenance_batch_manage`
- `workspace_desktop_name_rule`
- `workspace_desktop_notification`
- `workspace_desktop_pool`
- `workspace_desktop_pool_action`
- `workspace_desktop_pool_expand`
- `workspace_desktop_pool_notification`
- `workspace_desktop_user_batch_attach`
- `workspace_desktop_user_batch_detach`
- `workspace_desktop_volume_batch_delete`
- `workspace_eip_associate`
- `workspace_log_configuration`
- `workspace_notification_rule`
- `workspace_ou`
- `workspace_policy_group`
- `workspace_service`
- `workspace_terminal_binding`
- `workspace_user`
- `workspace_user_action`
- `workspace_user_group`
