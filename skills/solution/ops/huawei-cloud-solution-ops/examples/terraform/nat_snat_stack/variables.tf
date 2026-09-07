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

variable "nat_gateway_name" {
  description = "Name of the NAT gateway."
  type        = string
}

variable "nat_gateway_description" {
  description = "Description of the NAT gateway."
  type        = string
  default     = ""
}

variable "nat_gateway_spec" {
  description = "Specification of the NAT gateway."
  type        = string
  default     = "1"
}

variable "snat_source_type" {
  description = "Source type of the SNAT rule. 0 means subnet-based, 1 means CIDR-based."
  type        = number
  default     = 0
}

variable "snat_cidr" {
  description = "CIDR used when snat_source_type is 1."
  type        = string
  default     = null
}

variable "snat_description" {
  description = "Description of the SNAT rule."
  type        = string
  default     = ""
}

variable "bandwidth_name" {
  description = "Bandwidth name of the NAT EIP."
  type        = string
  default     = "nat-snat-bandwidth"
}

variable "bandwidth_size" {
  description = "Bandwidth size in Mbit/s of the NAT EIP."
  type        = number
  default     = 5
}

variable "bandwidth_share_type" {
  description = "Bandwidth share type of the NAT EIP."
  type        = string
  default     = "PER"
}

variable "bandwidth_charge_mode" {
  description = "Bandwidth charge mode of the NAT EIP."
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
