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

variable "bandwidth_name" {
  description = "Prefix of the EIP bandwidth names."
  type        = string
}

variable "vpn_gateway_name" {
  description = "Name of the VPN gateway."
  type        = string
}

variable "vpn_gateway_flavor" {
  description = "Flavor of the VPN gateway."
  type        = string
  default     = "Professional1"
}

variable "vpn_gateway_attachment_type" {
  description = "Attachment type of the VPN gateway."
  type        = string
  default     = "vpc"
}

variable "eip_type" {
  description = "Public IP type of the VPN gateway EIPs."
  type        = string
  default     = "5_bgp"
}

variable "bandwidth_size" {
  description = "Bandwidth size of each VPN EIP."
  type        = number
  default     = 8
}

variable "bandwidth_share_type" {
  description = "Bandwidth share type."
  type        = string
  default     = "PER"
}

variable "bandwidth_charge_mode" {
  description = "Bandwidth charge mode."
  type        = string
  default     = "traffic"
}

variable "delete_eip_on_termination" {
  description = "Whether to delete both EIPs when the VPN gateway is destroyed."
  type        = bool
  default     = false
}
