variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "resource_spec_code" {
  description = "Resource spec code of the WAF cloud instance."
  type        = string
}

variable "charging_mode" {
  description = "Charging mode of the WAF cloud instance."
  type        = string
}

variable "period_unit" {
  description = "Period unit of the WAF cloud instance."
  type        = string
}

variable "period" {
  description = "Subscription period of the WAF cloud instance."
  type        = number
}

variable "auto_renew" {
  description = "Whether to auto renew the WAF cloud instance."
  type        = string
  default     = "false"
}

variable "domain_name" {
  description = "Domain protected by WAF."
  type        = string
}

variable "certificate_id" {
  description = "Certificate ID of the protected domain."
  type        = string
  default     = ""
}

variable "certificate_name" {
  description = "Certificate name of the protected domain."
  type        = string
  default     = ""
}

variable "proxy_enabled" {
  description = "Whether proxy is enabled for the WAF domain."
  type        = bool
  default     = false
}

variable "origin_servers" {
  description = "Origin server list behind the WAF domain."
  type = list(object({
    client_protocol = string
    server_protocol = string
    address         = string
    port            = number
    type            = string
    weight          = number
  }))
}
