variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "publicip_type" {
  description = "Public IP type of the EIP."
  type        = string
  default     = "5_bgp"
}

variable "bandwidth_share_type" {
  description = "Bandwidth share type."
  type        = string
  default     = "PER"
}

variable "bandwidth_name" {
  description = "Bandwidth name used when share_type is PER."
  type        = string
  default     = null
}

variable "bandwidth_size" {
  description = "Bandwidth size used when share_type is PER."
  type        = number
  default     = null
}

variable "bandwidth_charge_mode" {
  description = "Bandwidth charge mode."
  type        = string
  default     = "traffic"
}

variable "topic_name" {
  description = "Name of the SMN topic."
  type        = string
}

variable "subscription_endpoint" {
  description = "Endpoint of the SMN subscription."
  type        = string
}

variable "subscription_protocol" {
  description = "Protocol of the SMN subscription."
  type        = string
}

variable "traffic_threshold" {
  description = "Anti-DDoS traffic cleaning threshold in Mbps."
  type        = number
}
