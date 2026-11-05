variable "access_key" {
  type        = string
  sensitive   = true
  description = "Huawei Cloud account AK used for both source and destination region API calls."
}

variable "secret_key" {
  type        = string
  sensitive   = true
  description = "Huawei Cloud account SK used for both source and destination region API calls."
}

variable "domain_name" {
  type        = string
  default     = ""
  description = "Optional Huawei Cloud account domain name, forwarded as HC_DOMAIN_NAME."
}

variable "source_server_id" {
  type        = string
  description = "Source ECS ID to migrate across regions."
}

variable "source_region" {
  type        = string
  default     = "la-north-2"
  description = "Source region ID."
}

variable "target_region" {
  type        = string
  default     = "la-south-2"
  description = "Target region ID."
}

variable "target_region_name" {
  type        = string
  default     = "LA-Santiago"
  description = "Target region display name used for SMS migproject."
}

variable "target_vpc_name" {
  type        = string
  default     = "vpc-migration"
  description = "Target VPC name; auto-created/reused if missing."
}

variable "target_vpc_cidr" {
  type        = string
  default     = "10.250.0.0/16"
  description = "Target VPC CIDR."
}

variable "target_subnet_cidr" {
  type        = string
  default     = "10.250.1.0/24"
  description = "Target subnet CIDR."
}

variable "target_image_id" {
  type        = string
  description = "Target ECS image ID. Required - no default, must match an image available in target_region."
}

variable "target_server_name" {
  type        = string
  default     = "mx2-to-santiago-migrated"
  description = "Target ECS server name prefix; a timestamp suffix is appended at creation."
}

variable "target_flavor_id" {
  type        = string
  default     = ""
  description = "Optional explicit target ECS flavor ID. Empty means auto-select nearest match to source CPU/RAM."
}

variable "target_admin_password" {
  type        = string
  sensitive   = true
  description = "Admin/root password set on the target ECS. Required - no default; must be a strong password."
}

variable "eip_bandwidth_mbps" {
  type        = number
  default     = 5
  description = "Target EIP bandwidth size in Mbps."
}

variable "root_volume_type" {
  type        = string
  default     = "SSD"
  description = "Target root volume type."
}

variable "data_volume_type" {
  type        = string
  default     = "SSD"
  description = "Target data volume type."
}

variable "sms_endpoint" {
  type        = string
  default     = "https://sms.ap-southeast-3.myhuaweicloud.com"
  description = "SMS endpoint."
}

variable "preferred_migration_method" {
  type        = string
  default     = "sms"
  description = "Preferred migration method (sms/rsync/auto)."

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

variable "extra_peer_ips" {
  type        = list(string)
  default     = []
  description = "Additional peer IP/CIDR entries to allow in target security groups."
}

variable "rsync_source_host" {
  type        = string
  default     = "10.8.0.2"
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

variable "target_rsync_ssh_key" {
  type        = string
  default     = ""
  description = "Path on the source host to an operator-provisioned SSH private key whose public half is already trusted by the target. Required for rsync fallback; the rsync target-auth path never writes authorized_keys or changes sshd_config."
}

variable "rsync_source_paths" {
  type        = list(string)
  default     = ["/"]
  description = "Source paths to be synced by rsync fallback."
}

variable "rsync_staging_dir" {
  type        = string
  default     = "/tmp/mgc-rsync-stage"
  description = "Local staging directory used during rsync fallback."
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
  default     = true
  description = "Enable OpenVPN/VPC peering bridge automation for source-to-target connectivity."
}

variable "local_vpc_id" {
  type        = string
  default     = ""
  description = "VPC ID of the bridge host itself, required when enable_vpn_bridge=true. Must be set explicitly (no longer auto-detected via the cloud metadata endpoint)."
}

variable "enable_target_vpn_client" {
  type        = bool
  default     = true
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
