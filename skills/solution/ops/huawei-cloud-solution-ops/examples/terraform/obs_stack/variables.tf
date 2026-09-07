variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "bucket_name" {
  description = "Globally unique OBS bucket name."
  type        = string
}

variable "environment" {
  description = "Environment label applied to bucket tags."
  type        = string
  default     = "dev"
}

variable "storage_class" {
  description = "OBS storage class."
  type        = string
  default     = "STANDARD"
}

variable "acl" {
  description = "OBS bucket ACL. Keep private unless there is a clear reason to change it."
  type        = string
  default     = "private"
}

variable "enable_versioning" {
  description = "Whether to enable versioning on the bucket."
  type        = bool
  default     = true
}

variable "enable_encryption" {
  description = "Whether to enable default server-side encryption."
  type        = bool
  default     = true
}

variable "sse_algorithm" {
  description = "Bucket default encryption algorithm. Valid examples include kms and AES256."
  type        = string
  default     = "kms"

  validation {
    condition     = contains(["kms", "AES256"], var.sse_algorithm)
    error_message = "sse_algorithm must be either kms or AES256."
  }
}

variable "kms_key_id" {
  description = "Optional KMS key ID used when sse_algorithm is kms."
  type        = string
  default     = null
}

variable "tags" {
  description = "Additional tags applied to the bucket."
  type        = map(string)
  default = {
    ManagedBy = "terraform"
  }
}
