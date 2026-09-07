variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "vpc_name" {
  description = "Name of the VPC to create."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC."
  type        = string
}

variable "subnet_name" {
  description = "Name of the subnet to create."
  type        = string
}

variable "subnet_cidr" {
  description = "CIDR block of the subnet."
  type        = string
}

variable "subnet_gateway_ip" {
  description = "Gateway IP address of the subnet."
  type        = string
}

variable "subnet_primary_dns" {
  description = "Primary DNS server of the subnet. CCE node installation depends on subnet DNS being configured."
  type        = string
  default     = "100.125.1.250"
}

variable "subnet_secondary_dns" {
  description = "Secondary DNS server of the subnet. CCE node installation depends on subnet DNS being configured."
  type        = string
  default     = "100.125.21.250"
}

variable "cluster_name" {
  description = "Name of the CCE cluster."
  type        = string
}

variable "cluster_flavor_id" {
  description = "Optional explicit flavor ID of the CCE cluster. Leave null to auto-select a sellable flavor."
  type        = string
  default     = null
}

variable "cluster_type" {
  description = "CCE cluster type used for flavor discovery."
  type        = string
  default     = "VirtualMachine"
}

variable "cluster_version" {
  description = "Optional Kubernetes version of the CCE cluster. Leave null to use the provider default."
  type        = string
  default     = null
}

variable "container_network_type" {
  description = "Container network type of the CCE cluster."
  type        = string
  default     = "overlay_l2"
}

variable "authentication_mode" {
  description = "Authentication mode of the CCE cluster."
  type        = string
  default     = "rbac"
}

variable "create_eip" {
  description = "Whether to create and bind an EIP for the cluster API endpoint."
  type        = bool
  default     = true
}

variable "eip_address" {
  description = "Optional existing EIP address for the cluster. If set, create_eip must be false."
  type        = string
  default     = null
}

variable "eip_type" {
  description = "EIP type used when create_eip is true."
  type        = string
  default     = "5_bgp"
}

variable "bandwidth_name" {
  description = "Bandwidth name used when create_eip is true."
  type        = string
  default     = "cce-node-pool-bandwidth"
}

variable "bandwidth_size" {
  description = "Bandwidth size in Mbit/s used when create_eip is true."
  type        = number
  default     = 5
}

variable "bandwidth_share_type" {
  description = "Bandwidth share type used when create_eip is true."
  type        = string
  default     = "PER"
}

variable "bandwidth_charge_mode" {
  description = "Bandwidth charge mode used when create_eip is true."
  type        = string
  default     = "traffic"
}

variable "node_pool_name" {
  description = "Name of the CCE node pool."
  type        = string
}

variable "node_pool_type" {
  description = "Type of the node pool."
  type        = string
  default     = "vm"
}

variable "node_pool_os_type" {
  description = "OS image used by the node pool."
  type        = string
  default     = "EulerOS 2.9"
}

variable "node_pool_initial_node_count" {
  description = "Initial node count of the node pool."
  type        = number
  default     = 2
}

variable "node_pool_min_node_count" {
  description = "Minimum node count of the node pool."
  type        = number
  default     = 1
}

variable "node_pool_max_node_count" {
  description = "Maximum node count of the node pool."
  type        = number
  default     = 5
}

variable "node_pool_scale_down_cooldown_time" {
  description = "Scale down cooldown time of the node pool in minutes."
  type        = number
  default     = 10
}

variable "node_pool_priority" {
  description = "Priority of the node pool."
  type        = number
  default     = 1
}

variable "node_key_pair_name" {
  description = "Existing key pair name used by the CCE node pool."
  type        = string
}

variable "node_performance_type" {
  description = "Flavor performance type used for node flavor discovery."
  type        = string
  default     = "general"
}

variable "node_cpu_core_count" {
  description = "Target CPU core count used for node flavor discovery."
  type        = number
  default     = 4
}

variable "node_memory_size" {
  description = "Target memory size in GB used for node flavor discovery."
  type        = number
  default     = 8
}

variable "root_volume_type" {
  description = "Root volume type used by CCE nodes."
  type        = string
  default     = "SAS"
}

variable "root_volume_size" {
  description = "Root volume size in GB used by CCE nodes."
  type        = number
  default     = 40
}

variable "data_volume_type" {
  description = "Data volume type used by CCE nodes."
  type        = string
  default     = "SSD"
}

variable "data_volume_size" {
  description = "Data volume size in GB used by CCE nodes."
  type        = number
  default     = 100
}

variable "tags" {
  description = "Common tags applied to supported resources."
  type        = map(string)
  default = {
    ManagedBy = "terraform"
  }
}
