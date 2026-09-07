variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "zone_name" {
  description = "DNS zone name."
  type        = string
}

variable "zone_email" {
  description = "Administrator email of the zone."
  type        = string
  default     = ""
}

variable "zone_type" {
  description = "DNS zone type."
  type        = string
  default     = "public"
}

variable "zone_description" {
  description = "Description of the zone."
  type        = string
  default     = ""
}

variable "zone_ttl" {
  description = "TTL of the zone."
  type        = number
  default     = 300
}

variable "zone_status" {
  description = "Status of the zone."
  type        = string
  default     = "ENABLE"
}

variable "zone_dnssec" {
  description = "Whether to enable DNSSEC for public zone."
  type        = string
  default     = "DISABLE"
}

variable "routers" {
  description = "Routers used when the zone is private."
  type = list(object({
    router_id     = string
    router_region = string
  }))
  default = []
}
