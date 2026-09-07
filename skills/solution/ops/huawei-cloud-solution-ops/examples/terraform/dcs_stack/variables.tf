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

variable "availability_zone" {
  description = "Availability zone of the DCS instance. Leave null to auto-discover."
  type        = string
  default     = null
}

variable "instance_name" {
  description = "Name of the DCS instance."
  type        = string
}

variable "instance_capacity" {
  description = "Capacity of the DCS instance in GB."
  type        = number
  default     = 1
}

variable "instance_engine_version" {
  description = "Engine version of the DCS instance."
  type        = string
  default     = "7.0"
}

variable "instance_flavor_id" {
  description = "Explicit flavor of the DCS instance. Leave null to auto-discover."
  type        = string
  default     = null
}

variable "instance_password" {
  description = "Password of the DCS instance."
  type        = string
  sensitive   = true
}
