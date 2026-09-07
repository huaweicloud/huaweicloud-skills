variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "resource_share_name" {
  description = "Name of the RAM resource share."
  type        = string
}

variable "description" {
  description = "Description of the RAM resource share."
  type        = string
  default     = ""
}

variable "principals" {
  description = "Account IDs or organization IDs that can access the shared resources."
  type        = list(string)
}

variable "resource_urns" {
  description = "List of resource URNs to share."
  type        = list(string)
}

variable "permission_ids" {
  description = "Optional RAM permission IDs associated with the share."
  type        = list(string)
  default     = []
}

variable "allow_external_principals" {
  description = "Whether to allow principals outside the organization."
  type        = bool
  default     = false
}
