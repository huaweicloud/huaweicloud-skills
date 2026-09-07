variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "nat_gateway_id" {
  description = "Existing NAT gateway ID discovered with hcloud."
  type        = string
}

variable "enable_snat" {
  description = "Whether to create an SNAT rule on the existing NAT gateway."
  type        = bool
  default     = true
}

variable "snat_floating_ip_id" {
  description = "Existing EIP ID used by the SNAT rule."
  type        = string
}

variable "snat_source_type" {
  description = "SNAT source type: 0 for subnet, 1 for CIDR."
  type        = number
  default     = 0
}

variable "snat_subnet_id" {
  description = "Existing subnet ID used when snat_source_type is 0."
  type        = string
  default     = ""
}

variable "snat_cidr" {
  description = "CIDR used when snat_source_type is 1."
  type        = string
  default     = ""
}

variable "snat_description" {
  description = "SNAT rule description."
  type        = string
  default     = "Managed by huaweicloud-skill Terraform example"
}

variable "enable_dnat" {
  description = "Whether to create a DNAT rule on the existing NAT gateway."
  type        = bool
  default     = false
}

variable "dnat_floating_ip_id" {
  description = "Existing EIP ID used by DNAT. Defaults to snat_floating_ip_id when empty."
  type        = string
  default     = ""
}

variable "dnat_port_id" {
  description = "Existing backend port ID used by DNAT."
  type        = string
  default     = ""
}

variable "dnat_protocol" {
  description = "DNAT protocol."
  type        = string
  default     = "tcp"
}

variable "dnat_internal_service_port" {
  description = "Internal service port."
  type        = number
  default     = 80
}

variable "dnat_external_service_port" {
  description = "External service port."
  type        = number
  default     = 8080
}
