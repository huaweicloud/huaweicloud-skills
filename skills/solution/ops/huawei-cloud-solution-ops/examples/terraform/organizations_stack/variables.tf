variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "name" {
  description = "Name of the organization account."
  type        = string
}

variable "email" {
  description = "Unique email address used by the organization account."
  type        = string
}

variable "phone" {
  description = "Optional phone number of the organization account."
  type        = string
  default     = null
}

variable "agency_name" {
  description = "Optional agency name bound to the organization account."
  type        = string
  default     = null
}

variable "description" {
  description = "Description of the organization account."
  type        = string
  default     = ""
}

variable "parent_id" {
  description = "Parent OU or root ID. Leave null to use the organization root."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags applied to the organization account."
  type        = map(string)
  default = {
    terraform = "true"
  }
}
