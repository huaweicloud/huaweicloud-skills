variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "cluster_id" {
  description = "Existing CCE cluster ID."
  type        = string
}

variable "availability_zone" {
  description = "Availability zone for the node pool. Defaults to the first region AZ."
  type        = string
  default     = ""
}

variable "partition_name" {
  description = "CCE partition name."
  type        = string
}

variable "partition_category" {
  description = "CCE partition category."
  type        = string
  default     = "IES"
}

variable "partition_public_border_group" {
  description = "Public border group of the partition."
  type        = string
}

variable "partition_subnet_id" {
  description = "Partition subnet ID."
  type        = string
}

variable "container_subnet_ids" {
  description = "Container subnet IPv4 subnet IDs used by the partition."
  type        = list(string)
}

variable "node_pool_name" {
  description = "Name of the node pool assigned to the partition."
  type        = string
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

variable "root_volume_type" {
  description = "Root volume type."
  type        = string
  default     = "SSD"
}

variable "root_volume_size" {
  description = "Root volume size in GB."
  type        = number
  default     = 40
}

variable "data_volume_type" {
  description = "Data volume type."
  type        = string
  default     = "SSD"
}

variable "data_volume_size" {
  description = "Data volume size in GB."
  type        = number
  default     = 100
}
