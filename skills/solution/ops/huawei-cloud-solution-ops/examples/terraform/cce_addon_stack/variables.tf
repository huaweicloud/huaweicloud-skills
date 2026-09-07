# Variable definitions for authentication
variable "region_name" {
  description = "The region where the CCE addon is located"
  type        = string
}

# Variable definitions for resources/data sources
variable "cluster_id" {
  description = "The ID of the CCE cluster"
  type        = string
  default     = ""

  validation {
    condition     = var.cluster_id != "" || var.cluster_name != ""
    error_message = "One of cluster_id or cluster_name is required"
  }
}

variable "cluster_name" {
  description = "The name of the CCE cluster"
  type        = string
  default     = ""
}

variable "addon_template_name" {
  description = "The name of the CCE addon template"
  type        = string
  default     = "autoscaler"
}

variable "addon_version" {
  description = "The version of the CCE addon template"
  type        = string
}

variable "project_id" {
  description = "The ID of the project"
  type        = string
  default     = ""
  nullable    = false
}
