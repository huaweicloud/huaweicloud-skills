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

variable "instance_name" {
  description = "Name of the APIG instance."
  type        = string
}

variable "instance_edition" {
  description = "Edition of the APIG instance."
  type        = string
  default     = "BASIC"
}

variable "availability_zones_count" {
  description = "Number of availability zones to assign to the APIG instance."
  type        = number
  default     = 1
}

variable "plugin_name" {
  description = "Name of the APIG plugin."
  type        = string
}

variable "plugin_description" {
  description = "Description of the APIG plugin."
  type        = string
  default     = null
}
