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
  default     = "192.168.0.0/16"
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

variable "security_group_name" {
  description = "Name of the security group to create."
  type        = string
}

variable "availability_zone" {
  description = "Availability zone used by ECS and CBR. Leave null to auto-discover."
  type        = string
  default     = null
}

variable "instance_name" {
  description = "Name of the ECS instance to back up."
  type        = string
}

variable "image_name" {
  description = "Public image name used for the ECS instance."
  type        = string
  default     = "Ubuntu 22.04 server 64bit"
}

variable "flavor_performance_type" {
  description = "Performance type used when auto-discovering the ECS flavor."
  type        = string
  default     = "normal"
}

variable "flavor_cpu_core_count" {
  description = "CPU core count used when auto-discovering the ECS flavor."
  type        = number
  default     = 2
}

variable "flavor_memory_size" {
  description = "Memory size in GB used when auto-discovering the ECS flavor."
  type        = number
  default     = 4
}

variable "key_pair_name" {
  description = "Existing key pair used to log in to the ECS instance."
  type        = string
}

variable "system_disk_type" {
  description = "System disk type of the ECS instance."
  type        = string
  default     = "SAS"
}

variable "system_disk_size" {
  description = "System disk size of the ECS instance in GB."
  type        = number
  default     = 40
}

variable "vault_name" {
  description = "Name of the CBR vault."
  type        = string
}

variable "vault_size" {
  description = "Vault size in GB."
  type        = number
  default     = 200
}

variable "enterprise_project_id" {
  description = "Enterprise project ID. Use 0 for the default project."
  type        = string
  default     = "0"
}
