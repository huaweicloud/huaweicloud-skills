variable "source_access_key" {
  type        = string
  sensitive   = true
  description = "Source account AK (read-only usage in this workflow)."
}

variable "source_secret_key" {
  type        = string
  sensitive   = true
  description = "Source account SK (read-only usage in this workflow)."
}

variable "source_region" {
  type        = string
  default     = "ap-southeast-3"
  description = "Preferred source region hint. Script will auto-discover when IDs are not in this region."
}

variable "source_project_id" {
  type        = string
  default     = ""
  description = "Preferred source project ID hint. Script will auto-discover when IDs are not in this project."
}

variable "destination_access_key" {
  type        = string
  sensitive   = true
  description = "Destination account AK."
}

variable "destination_secret_key" {
  type        = string
  sensitive   = true
  description = "Destination account SK."
}

variable "destination_region" {
  type        = string
  default     = "ap-southeast-3"
  description = "Preferred destination region hint. Script will auto-discover target ECS by fixed IP if needed."
}

variable "destination_region_name" {
  type        = string
  default     = ""
  description = "Optional destination region display name for SMS migproject. Empty means auto-resolve."
}

variable "destination_project_id" {
  type        = string
  default     = ""
  description = "Preferred destination project ID hint. Script will auto-discover target ECS by fixed IP if needed."
}

variable "source_server_ids" {
  type        = list(string)
  default     = []
  description = "Source ECS IDs to migrate via SMS. Must be provided in terraform.tfvars."
}

variable "eip_bandwidth_mbps" {
  type        = number
  default     = 100
  description = "Destination EIP bandwidth size in Mbps."
}

variable "security_group_rule_description" {
  type        = string
  default     = "虚拟机迁移"
  description = "Description used when adding destination security group rules."
}

variable "target_image_id" {
  type        = string
  default     = "def7f676-e1e3-43c3-9098-e41f3324d566"
  description = "Target ECS image ID used for external-source single-instance migration."
}

variable "sms_endpoint" {
  type        = string
  default     = "https://sms.ap-southeast-3.myhuaweicloud.com"
  description = "SMS endpoint."
}

variable "preferred_migration_method" {
  type        = string
  default     = "sms"
  description = "Preferred migration method for external source migration (sms/rsync/auto)."

  validation {
    condition     = contains(["sms", "rsync", "auto"], lower(var.preferred_migration_method))
    error_message = "preferred_migration_method must be one of: sms, rsync, auto."
  }
}

variable "enable_rsync_fallback" {
  type        = bool
  default     = true
  description = "When true, automatically fallback to rsync if SMS is incompatible or runtime fails."
}

variable "source_private_ip" {
  type        = string
  default     = ""
  description = "Optional source private IPv4/CIDR used for security group and route preparation."
}

variable "source_network_cidr" {
  type        = string
  default     = ""
  description = "Source private network CIDR used by VPN bridge route setup. Required when enable_vpn_bridge=true and source_private_ip is empty."
}

variable "extra_peer_ips" {
  type        = list(string)
  default     = []
  description = "Additional peer IP/CIDR entries to allow in target security groups."
}

variable "rsync_source_host" {
  type        = string
  default     = ""
  description = "SSH host of source machine used by rsync fallback."
}

variable "rsync_source_port" {
  type        = number
  default     = 2222
  description = "SSH port of source machine used by rsync fallback."
}

variable "rsync_source_user" {
  type        = string
  default     = "root"
  description = "SSH username of source machine used by rsync fallback."
}

variable "rsync_source_password" {
  type        = string
  sensitive   = true
  default     = ""
  description = "SSH password of source machine used by rsync fallback."
}

variable "rsync_target_host" {
  type        = string
  default     = ""
  description = "Optional explicit target SSH host. Empty means auto-detect from target ECS."
}

variable "rsync_target_port" {
  type        = number
  default     = 22
  description = "SSH port of target machine used by rsync fallback."
}

variable "rsync_target_user" {
  type        = string
  default     = "root"
  description = "SSH username of target machine used by rsync fallback."
}

variable "rsync_target_password" {
  type        = string
  sensitive   = true
  default     = ""
  description = "SSH password of target machine used by rsync fallback. Empty means TARGET_ADMIN_PASSWORD."
}

variable "rsync_source_paths" {
  type        = list(string)
  default     = ["/"]
  description = "Comma-joined source paths to be synced by rsync fallback."
}

variable "rsync_incremental_rounds" {
  type        = number
  default     = 1
  description = "Number of incremental sync rounds before cutover sync."
}

variable "rsync_timeout_sec" {
  type        = number
  default     = 7200
  description = "Timeout (seconds) for rsync/ssh operations."
}

variable "rsync_common_args" {
  type        = string
  default     = "--numeric-ids --info=stats2,progress2 --partial"
  description = "Extra args appended to rsync command."
}

variable "rsync_excludes" {
  type = list(string)
  default = [
    "/dev/*",
    "/proc/*",
    "/sys/*",
    "/tmp/*",
    "/run/*",
    "/mnt/*",
    "/media/*",
    "/lost+found",
    "/swapfile",
    "/var/tmp/*",
    "/var/run/*",
    "/boot/efi/*",
    "/etc/fstab",
  ]
  description = "Exclude patterns for rsync."
}

variable "rsync_cutover_stop_cmd" {
  type        = string
  default     = ""
  description = "Optional command executed on source host before cutover sync."
}

variable "rsync_cutover_start_cmd" {
  type        = string
  default     = ""
  description = "Optional command executed on source host after cutover sync."
}

variable "rsync_target_finalize_cmd" {
  type        = string
  default     = ""
  description = "Optional command executed on target host after cutover sync."
}

variable "enable_vpn_bridge" {
  type        = bool
  default     = false
  description = "Enable OpenVPN/VPC peering bridge automation for source-to-target connectivity."
}

variable "local_vpc_id" {
  type        = string
  default     = ""
  description = "VPC ID of the bridge host itself, required when enable_vpn_bridge=true. Must be set explicitly (no longer auto-detected via the cloud metadata endpoint)."
}

variable "enable_target_vpn_client" {
  type        = bool
  default     = false
  description = "Enable cloud-init bootstrap of target OpenVPN client."
}

variable "vpn_server_public_ip" {
  type        = string
  default     = ""
  description = "OpenVPN server public IPv4 used by target client profile."
}

variable "vpn_server_port" {
  type        = number
  default     = 1194
  description = "OpenVPN server UDP port."
}

variable "vpn_client_common_name" {
  type        = string
  default     = "site-mx2-target"
  description = "OpenVPN client certificate common-name for target ECS."
}

variable "vpn_client_static_ip" {
  type        = string
  default     = "10.8.0.10"
  description = "OpenVPN client static IPv4 assigned to target ECS."
}
