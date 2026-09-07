variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "volume_name" {
  description = "Name of the EVS volume."
  type        = string
}

variable "availability_zone" {
  description = "Availability zone of the EVS volume. Leave null to auto-discover."
  type        = string
  default     = null
}

variable "volume_type" {
  description = "Volume type of the EVS volume."
  type        = string
  default     = "SSD"
}

variable "volume_size" {
  description = "Size of the EVS volume in GB."
  type        = number
  default     = 40
}

variable "volume_description" {
  description = "Description of the EVS volume."
  type        = string
  default     = ""
}

variable "volume_multiattach" {
  description = "Whether the EVS volume is multi-attach."
  type        = bool
  default     = false
}

variable "volume_iops" {
  description = "Provisioned IOPS for supported volume types."
  type        = number
  default     = null
}

variable "volume_throughput" {
  description = "Provisioned throughput for supported volume types."
  type        = number
  default     = null
}

variable "device_type" {
  description = "Device type of the EVS volume."
  type        = string
  default     = "VBD"
}

variable "tags" {
  description = "Common tags applied to the EVS volume."
  type        = map(string)
  default = {
    ManagedBy = "terraform"
  }
}
