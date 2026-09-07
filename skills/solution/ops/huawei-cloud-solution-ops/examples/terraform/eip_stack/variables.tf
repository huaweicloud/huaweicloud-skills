variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "eip_name" {
  description = "Name of the EIP resource."
  type        = string
}

variable "eip_type" {
  description = "EIP type."
  type        = string
  default     = "5_bgp"
}

variable "bandwidth_name" {
  description = "Bandwidth name of the EIP."
  type        = string
  default     = "terraform-eip-bandwidth"
}

variable "bandwidth_size" {
  description = "Bandwidth size in Mbit/s."
  type        = number
  default     = 5
}

variable "bandwidth_share_type" {
  description = "Bandwidth share type of the EIP."
  type        = string
  default     = "PER"
}

variable "bandwidth_charge_mode" {
  description = "Bandwidth charge mode of the EIP."
  type        = string
  default     = "traffic"
}

variable "tags" {
  description = "Common tags applied to the EIP."
  type        = map(string)
  default = {
    ManagedBy = "terraform"
  }
}
