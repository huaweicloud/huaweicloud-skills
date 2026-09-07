variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "cluster_id" {
  description = "Existing CCE cluster ID. Prefer this after hcloud discovery."
  type        = string
  default     = ""
}

variable "cluster_name" {
  description = "Existing CCE cluster name used only when cluster_id is empty."
  type        = string
  default     = ""
}

variable "addon_version" {
  description = "CoreDNS addon version matching the target cluster version."
  type        = string
}

variable "custom_overrides" {
  description = "Optional CoreDNS custom_json overrides merged into the addon template custom parameters."
  type        = map(any)
  default     = {}
}
