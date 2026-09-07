variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "organization_name" {
  description = "Name of the SWR organization to create."
  type        = string
}

variable "repository_name" {
  description = "Name of the SWR repository to create."
  type        = string
}

variable "repository_category" {
  description = "Repository category."
  type        = string
  default     = "linux"
}
