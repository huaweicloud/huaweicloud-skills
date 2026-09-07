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

variable "er_instance_name" {
  description = "Name of the ER instance."
  type        = string
}

variable "er_instance_asn" {
  description = "ASN of the ER instance."
  type        = number
  default     = 64512
}

variable "er_vpc_attachment_name" {
  description = "Name of the ER VPC attachment."
  type        = string
}

variable "auto_create_vpc_routes" {
  description = "Whether ER should auto-create VPC routes for the attachment."
  type        = bool
  default     = true
}
