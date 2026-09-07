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
  description = "Availability zone of the SFS Turbo file system. Leave null to auto-discover."
  type        = string
  default     = null
}

variable "turbo_name" {
  description = "Name of the SFS Turbo file system."
  type        = string
}

variable "turbo_size" {
  description = "Capacity of the SFS Turbo file system in GB."
  type        = number
  default     = 1200
}

variable "share_proto" {
  description = "Share protocol of the SFS Turbo file system."
  type        = string
  default     = "NFS"
}

variable "share_type" {
  description = "Share type of the SFS Turbo file system."
  type        = string
  default     = "STANDARD"
}

variable "hpc_bandwidth" {
  description = "HPC bandwidth spec. Required only when share_type is HPC."
  type        = string
  default     = null
}

variable "charging_mode" {
  description = "Charging mode of the SFS Turbo file system."
  type        = string
  default     = "postPaid"
}

variable "period_unit" {
  description = "Period unit used when charging_mode is prePaid."
  type        = string
  default     = null
}

variable "period" {
  description = "Period used when charging_mode is prePaid."
  type        = number
  default     = null
}
