variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "bucket_name" {
  description = "Globally unique OBS bucket name for the static website."
  type        = string
}

variable "bucket_storage_class" {
  description = "OBS storage class."
  type        = string
  default     = "STANDARD"
}

variable "bucket_force_destroy" {
  description = "Whether to force destroy bucket objects with the bucket. Keep false for production."
  type        = bool
  default     = false
}

variable "index_document" {
  description = "Website index document key."
  type        = string
  default     = "index.html"
}

variable "error_document" {
  description = "Website error document key."
  type        = string
  default     = "error.html"
}

variable "index_html" {
  description = "Small demo index HTML content. For production, use a release pipeline instead of inline content."
  type        = string
  default     = "<html><body><h1>Huawei Cloud static site</h1></body></html>"
}

variable "error_html" {
  description = "Small demo error HTML content."
  type        = string
  default     = "<html><body><h1>Not found</h1></body></html>"
}

variable "origin_server" {
  description = "Optional explicit OBS website origin domain. Leave empty to use the standard OBS website domain pattern."
  type        = string
  default     = ""
}

variable "cdn_domain_name" {
  description = "CDN acceleration domain name."
  type        = string
}

variable "service_area" {
  description = "CDN service area."
  type        = string
  default     = "mainland_china"
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
      ttl                 = 3600
      ttl_type            = "s"
      priority            = 1
      url_parameter_type  = "full_url"
      url_parameter_value = null
    }
  ]
}

variable "create_dns_zone" {
  description = "Whether to create a public DNS zone."
  type        = bool
  default     = false
}

variable "zone_id" {
  description = "Existing public DNS zone ID. Required when create_dns_zone is false and create_dns_record is true."
  type        = string
  default     = ""
}

variable "zone_name" {
  description = "DNS zone name used when create_dns_zone is true."
  type        = string
  default     = ""
}

variable "zone_email" {
  description = "Administrator email used when creating a DNS zone."
  type        = string
  default     = ""
}

variable "zone_description" {
  description = "DNS zone description."
  type        = string
  default     = "Static website zone managed by Terraform"
}

variable "zone_ttl" {
  description = "DNS zone TTL."
  type        = number
  default     = 300
}

variable "create_dns_record" {
  description = "Whether to create a CNAME record for the CDN domain."
  type        = bool
  default     = false
}

variable "cdn_cname_target" {
  description = "CDN-assigned CNAME target confirmed from CDN readback."
  type        = string
  default     = ""
}

variable "record_ttl" {
  description = "DNS record TTL."
  type        = number
  default     = 300
}

variable "tags" {
  description = "Common tags applied to supported resources."
  type        = map(string)
  default = {
    ManagedBy = "terraform"
  }
}
