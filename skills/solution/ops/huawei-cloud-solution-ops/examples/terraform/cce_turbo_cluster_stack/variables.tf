variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "vpc_name" {
  description = "Name of the VPC."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC."
  type        = string
  default     = "192.168.0.0/16"
}

variable "cluster_subnet_name" {
  description = "Name of the cluster subnet."
  type        = string
}

variable "cluster_subnet_cidr" {
  description = "CIDR block of the cluster subnet."
  type        = string
  default     = "192.168.1.0/24"
}

variable "cluster_subnet_gateway_ip" {
  description = "Gateway IP of the cluster subnet."
  type        = string
  default     = "192.168.1.1"
}

variable "eni_subnet_name" {
  description = "Name of the ENI subnet used by CCE Turbo."
  type        = string
}

variable "eni_subnet_cidr" {
  description = "CIDR block of the ENI subnet."
  type        = string
  default     = "192.168.2.0/24"
}

variable "eni_subnet_gateway_ip" {
  description = "Gateway IP of the ENI subnet."
  type        = string
  default     = "192.168.2.1"
}

variable "cluster_name" {
  description = "Name of the CCE Turbo cluster."
  type        = string
}

variable "cluster_flavor_id" {
  description = "CCE cluster flavor ID."
  type        = string
  default     = "cce.s1.small"
}

variable "cluster_version" {
  description = "CCE cluster version. Null lets provider choose a supported default."
  type        = string
  default     = null
}

variable "cluster_description" {
  description = "Cluster description."
  type        = string
  default     = "CCE Turbo cluster managed by Terraform"
}

variable "create_eip" {
  description = "Whether to create an EIP for the cluster."
  type        = bool
  default     = true
}

variable "eip_address" {
  description = "Existing EIP address used when create_eip is false."
  type        = string
  default     = ""
}

variable "bandwidth_name" {
  description = "Bandwidth name used when create_eip is true."
  type        = string
  default     = "cce-turbo-bandwidth"
}

variable "bandwidth_size" {
  description = "Bandwidth size in Mbit/s."
  type        = number
  default     = 5
}

variable "enable_distribute_management" {
  description = "Whether to enable distributed management for the cluster."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Common tags applied to supported resources."
  type        = map(string)
  default = {
    ManagedBy = "terraform"
  }
}
