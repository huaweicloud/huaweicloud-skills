variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "domain_name" {
  description = "Accelerated CDN domain name."
  type        = string
}

variable "origin_server" {
  description = "Origin server address, either an IP or a domain name."
  type        = string
}

variable "domain_type" {
  description = "Business type of the CDN domain."
  type        = string
  default     = "web"
}

variable "service_area" {
  description = "Acceleration service area."
  type        = string
  default     = "mainland_china"
}

variable "origin_type" {
  description = "Origin server type."
  type        = string
  default     = "ipaddr"
}

variable "origin_protocol" {
  description = "Protocol used by CDN to retrieve origin data."
  type        = string
  default     = "http"
}

variable "http_port" {
  description = "HTTP port of the origin server."
  type        = number
  default     = 80
}

variable "https_port" {
  description = "HTTPS port of the origin server."
  type        = number
  default     = 443
}

variable "cache_rules" {
  description = "Cache rules applied to the CDN domain."
  type = list(object({
    rule_type           = string
    content             = string
    ttl                 = number
    ttl_type            = string
    priority            = number
    url_parameter_type  = optional(string)
    url_parameter_value = optional(string)
  }))
  default = [
    {
      rule_type           = "all"
      content             = ""
      ttl                 = 2592000
      ttl_type            = "s"
      priority            = 1
      url_parameter_type  = "full_url"
      url_parameter_value = null
    }
  ]
}
