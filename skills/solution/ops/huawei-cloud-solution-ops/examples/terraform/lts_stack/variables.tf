variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "group_name" {
  description = "Name of the LTS log group."
  type        = string
}

variable "group_log_expiration_days" {
  description = "Retention days of the LTS log group."
  type        = number
  default     = 14
}

variable "stream_name" {
  description = "Name of the LTS log stream."
  type        = string
}

variable "stream_log_expiration_days" {
  description = "Retention days of the LTS log stream. Use null to inherit from the group."
  type        = number
  default     = null
}
