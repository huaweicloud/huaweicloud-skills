terraform {
  required_version = ">= 1.5.0"
}

locals {
  run_fingerprint = sha1(jsonencode({
    source_server_id   = var.source_server_id
    source_region      = var.source_region
    target_region      = var.target_region
    target_region_name = var.target_region_name
    target_vpc_name    = var.target_vpc_name
    target_vpc_cidr    = var.target_vpc_cidr
    target_subnet_cidr = var.target_subnet_cidr
    target_image_id    = var.target_image_id
    target_server_name = var.target_server_name
    eip_bandwidth_mbps = var.eip_bandwidth_mbps
    root_volume_type   = var.root_volume_type
    data_volume_type   = var.data_volume_type
    sms_endpoint       = var.sms_endpoint
    enable_vpn_bridge  = var.enable_vpn_bridge
    local_vpc_id       = var.local_vpc_id
  }))
}

resource "terraform_data" "mgc_region_migration" {
  triggers_replace = [local.run_fingerprint]

  provisioner "local-exec" {
    command = "bash ${path.module}/scripts/run_migration.sh"
    environment = {
      HC_AK          = var.access_key
      HC_SK          = var.secret_key
      HC_DOMAIN_NAME = var.domain_name

      SOURCE_SERVER_ID   = var.source_server_id
      SOURCE_REGION      = var.source_region
      TARGET_REGION      = var.target_region
      TARGET_REGION_NAME = var.target_region_name

      TARGET_VPC_NAME    = var.target_vpc_name
      TARGET_VPC_CIDR    = var.target_vpc_cidr
      TARGET_SUBNET_CIDR = var.target_subnet_cidr
      TARGET_IMAGE_ID    = var.target_image_id
      TARGET_SERVER_NAME = var.target_server_name
      TARGET_FLAVOR_ID   = var.target_flavor_id

      EIP_BANDWIDTH_MBPS = tostring(var.eip_bandwidth_mbps)
      ROOT_VOLUME_TYPE   = var.root_volume_type
      DATA_VOLUME_TYPE   = var.data_volume_type

      TARGET_ADMIN_PASSWORD      = var.target_admin_password
      PREFERRED_MIGRATION_METHOD = var.preferred_migration_method
      ENABLE_RSYNC_FALLBACK      = tostring(var.enable_rsync_fallback)
      SOURCE_PRIVATE_IP          = var.source_private_ip
      EXTRA_PEER_IPS             = join(",", var.extra_peer_ips)

      RSYNC_SOURCE_HOST         = var.rsync_source_host
      RSYNC_SOURCE_PORT         = tostring(var.rsync_source_port)
      RSYNC_SOURCE_USER         = var.rsync_source_user
      RSYNC_SOURCE_PASSWORD     = var.rsync_source_password
      RSYNC_TARGET_HOST         = var.rsync_target_host
      RSYNC_TARGET_PORT         = tostring(var.rsync_target_port)
      RSYNC_TARGET_USER         = var.rsync_target_user
      TARGET_RSYNC_SSH_KEY      = var.target_rsync_ssh_key
      RSYNC_SOURCE_PATHS        = join(",", var.rsync_source_paths)
      RSYNC_STAGING_DIR         = var.rsync_staging_dir
      RSYNC_INCREMENTAL_ROUNDS  = tostring(var.rsync_incremental_rounds)
      RSYNC_TIMEOUT_SEC         = tostring(var.rsync_timeout_sec)
      RSYNC_COMMON_ARGS         = var.rsync_common_args
      RSYNC_EXCLUDES            = join(",", var.rsync_excludes)
      RSYNC_CUTOVER_STOP_CMD    = var.rsync_cutover_stop_cmd
      RSYNC_CUTOVER_START_CMD   = var.rsync_cutover_start_cmd
      RSYNC_TARGET_FINALIZE_CMD = var.rsync_target_finalize_cmd

      ENABLE_VPN_BRIDGE        = tostring(var.enable_vpn_bridge)
      LOCAL_VPC_ID             = var.local_vpc_id
      ENABLE_TARGET_VPN_CLIENT = tostring(var.enable_target_vpn_client)
      VPN_SERVER_PUBLIC_IP     = var.vpn_server_public_ip
      VPN_SERVER_PORT          = tostring(var.vpn_server_port)
      VPN_CLIENT_COMMON_NAME   = var.vpn_client_common_name
      VPN_CLIENT_STATIC_IP     = var.vpn_client_static_ip

      SMS_ENDPOINT = var.sms_endpoint
      RESULT_PATH  = "${path.module}/out/migration_result.json"
    }
  }
}

output "migration_result_file" {
  value       = "${path.module}/out/migration_result.json"
  description = "Execution result json written by scripts/mgc_migrate.py"
}
