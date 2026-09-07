variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "cluster_id" {
  description = "Existing CCE cluster ID. Prefer this after hcloud discovery."
  type        = string
  default     = ""
}

variable "cluster_name" {
  description = "Existing CCE cluster name used only when cluster_id is empty."
  type        = string
  default     = ""
}

variable "availability_zone" {
  description = "Availability zone for the node pool. Defaults to the first region AZ."
  type        = string
  default     = ""
}

variable "node_pool_name" {
  description = "Name of the node pool to create."
  type        = string
}

variable "node_pool_type" {
  description = "Node pool type."
  type        = string
  default     = "vm"
}

variable "node_pool_os_type" {
  description = "Node pool OS type."
  type        = string
  default     = "EulerOS 2.9"
}

variable "node_key_pair_name" {
  description = "Existing key pair name used by nodes."
  type        = string
}

variable "node_flavor_id" {
  description = "Explicit node flavor ID. Leave empty to discover one by filters."
  type        = string
  default     = ""
}

variable "node_performance_type" {
  description = "Node flavor performance type used for discovery."
  type        = string
  default     = "normal"
}

variable "node_cpu_core_count" {
  description = "Node CPU core count used for flavor discovery."
  type        = number
  default     = 2
}

variable "node_memory_size" {
  description = "Node memory size in GB used for flavor discovery."
  type        = number
  default     = 4
}

variable "node_pool_initial_node_count" {
  description = "Initial node count."
  type        = number
  default     = 1
}

variable "node_pool_min_node_count" {
  description = "Minimum autoscaling node count."
  type        = number
  default     = 1
}

variable "node_pool_max_node_count" {
  description = "Maximum autoscaling node count."
  type        = number
  default     = 3
}

variable "node_pool_scale_down_cooldown_time" {
  description = "Scale-down cooldown time in minutes."
  type        = number
  default     = 10
}

variable "node_pool_priority" {
  description = "Node pool priority."
  type        = number
  default     = 0
}

variable "root_volume_type" {
  description = "Root volume type."
  type        = string
  default     = "SAS"
}

variable "root_volume_size" {
  description = "Root volume size in GB."
  type        = number
  default     = 40
}

variable "data_volume_type" {
  description = "Data volume type."
  type        = string
  default     = "SAS"
}

variable "data_volume_size" {
  description = "Data volume size in GB."
  type        = number
  default     = 100
}

variable "tags" {
  description = "Tags applied to the node pool."
  type        = map(string)
  default = {
    ManagedBy = "terraform"
  }
}
