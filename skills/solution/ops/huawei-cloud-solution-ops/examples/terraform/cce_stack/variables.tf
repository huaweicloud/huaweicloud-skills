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

variable "cluster_description" {
  description = "Description of the CCE cluster."
  type        = string
  default     = "Managed by huaweicloud-skill."
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
  default     = "cce-bandwidth"
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

variable "tags" {
  description = "Common tags applied to supported resources."
  type        = map(string)
  default = {
    ManagedBy = "terraform"
  }
}
