terraform {
  required_version = ">= 1.5.0"
}

locals {
  run_fingerprint = sha1(jsonencode({
    source_region                   = var.source_region
    source_project_id               = var.source_project_id
    destination_region              = var.destination_region
    destination_region_name         = var.destination_region_name
    destination_project_id          = var.destination_project_id
    source_server_ids               = var.source_server_ids
    eip_bandwidth_mbps              = var.eip_bandwidth_mbps
    security_group_rule_description = var.security_group_rule_description
    target_image_id                 = var.target_image_id
    sms_endpoint                    = var.sms_endpoint
    preferred_migration_method      = var.preferred_migration_method
    enable_rsync_fallback           = var.enable_rsync_fallback
    source_private_ip               = var.source_private_ip
    source_network_cidr             = var.source_network_cidr
    extra_peer_ips                  = var.extra_peer_ips
    rsync_source_host               = var.rsync_source_host
    rsync_source_port               = var.rsync_source_port
    rsync_source_user               = var.rsync_source_user
    rsync_source_password           = var.rsync_source_password
    rsync_target_host               = var.rsync_target_host
    rsync_target_port               = var.rsync_target_port
    rsync_target_user               = var.rsync_target_user
    rsync_target_password           = var.rsync_target_password
    rsync_source_paths              = var.rsync_source_paths
    rsync_incremental_rounds        = var.rsync_incremental_rounds
    rsync_timeout_sec               = var.rsync_timeout_sec
    rsync_common_args               = var.rsync_common_args
    rsync_excludes                  = var.rsync_excludes
    rsync_cutover_stop_cmd          = var.rsync_cutover_stop_cmd
    rsync_cutover_start_cmd         = var.rsync_cutover_start_cmd
    rsync_target_finalize_cmd       = var.rsync_target_finalize_cmd
    enable_vpn_bridge               = var.enable_vpn_bridge
    local_vpc_id                    = var.local_vpc_id
    enable_target_vpn_client        = var.enable_target_vpn_client
    vpn_server_public_ip            = var.vpn_server_public_ip
    vpn_server_port                 = var.vpn_server_port
    vpn_client_common_name          = var.vpn_client_common_name
    vpn_client_static_ip            = var.vpn_client_static_ip
  }))
}

resource "terraform_data" "sms_existing_target_batch" {
  triggers_replace = [local.run_fingerprint]

  provisioner "local-exec" {
    command = "bash ${path.module}/scripts/run_migration.sh"
    environment = {
      SOURCE_ACCESS_KEY = var.source_access_key
      SOURCE_SECRET_KEY = var.source_secret_key
      SOURCE_REGION     = var.source_region
      SOURCE_PROJECT_ID = var.source_project_id

      DESTINATION_ACCESS_KEY  = var.destination_access_key
      DESTINATION_SECRET_KEY  = var.destination_secret_key
      DESTINATION_REGION      = var.destination_region
      DESTINATION_REGION_NAME = var.destination_region_name
      DESTINATION_PROJECT_ID  = var.destination_project_id

      SOURCE_SERVER_IDS          = join(",", var.source_server_ids)
      EIP_BANDWIDTH_MBPS         = tostring(var.eip_bandwidth_mbps)
      SG_RULE_DESCRIPTION        = var.security_group_rule_description
      TARGET_IMAGE_ID            = var.target_image_id
      SMS_ENDPOINT               = var.sms_endpoint
      PREFERRED_MIGRATION_METHOD = var.preferred_migration_method
      ENABLE_RSYNC_FALLBACK      = tostring(var.enable_rsync_fallback)
      SOURCE_PRIVATE_IP          = var.source_private_ip
      SOURCE_NETWORK_CIDR        = var.source_network_cidr
      EXTRA_PEER_IPS             = join(",", var.extra_peer_ips)
      RSYNC_SOURCE_HOST          = var.rsync_source_host
      RSYNC_SOURCE_PORT          = tostring(var.rsync_source_port)
      RSYNC_SOURCE_USER          = var.rsync_source_user
      RSYNC_SOURCE_PASSWORD      = var.rsync_source_password
      RSYNC_TARGET_HOST          = var.rsync_target_host
      RSYNC_TARGET_PORT          = tostring(var.rsync_target_port)
      RSYNC_TARGET_USER          = var.rsync_target_user
      RSYNC_TARGET_PASSWORD      = var.rsync_target_password
      RSYNC_SOURCE_PATHS         = join(",", var.rsync_source_paths)
      RSYNC_INCREMENTAL_ROUNDS   = tostring(var.rsync_incremental_rounds)
      RSYNC_TIMEOUT_SEC          = tostring(var.rsync_timeout_sec)
      RSYNC_COMMON_ARGS          = var.rsync_common_args
      RSYNC_EXCLUDES             = join(",", var.rsync_excludes)
      RSYNC_CUTOVER_STOP_CMD     = var.rsync_cutover_stop_cmd
      RSYNC_CUTOVER_START_CMD    = var.rsync_cutover_start_cmd
      RSYNC_TARGET_FINALIZE_CMD  = var.rsync_target_finalize_cmd
      ENABLE_VPN_BRIDGE          = tostring(var.enable_vpn_bridge)
      LOCAL_VPC_ID               = var.local_vpc_id
      ENABLE_TARGET_VPN_CLIENT   = tostring(var.enable_target_vpn_client)
      VPN_SERVER_PUBLIC_IP       = var.vpn_server_public_ip
      VPN_SERVER_PORT            = tostring(var.vpn_server_port)
      VPN_CLIENT_COMMON_NAME     = var.vpn_client_common_name
      VPN_CLIENT_STATIC_IP       = var.vpn_client_static_ip
      RESULT_PATH                = "${path.module}/out/migration_result.json"
    }
  }
}

output "migration_result_file" {
  value       = "${path.module}/out/migration_result.json"
  description = "Execution result json written by scripts/run_migration.sh workflow"
}
