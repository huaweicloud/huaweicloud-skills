locals {
  common_tags = merge(
    {
      Environment = var.environment
    },
    var.tags,
  )
}

resource "huaweicloud_obs_bucket" "this" {
  bucket        = var.bucket_name
  storage_class = var.storage_class
  acl           = var.acl
  versioning    = var.enable_versioning
  encryption    = var.enable_encryption
  sse_algorithm = var.sse_algorithm
  kms_key_id    = var.kms_key_id

  tags = local.common_tags

  lifecycle {
    precondition {
      condition     = !var.enable_encryption || lower(var.sse_algorithm) != "kms" || (var.kms_key_id != null && trimspace(var.kms_key_id) != "")
      error_message = "kms_key_id must be set when encryption is enabled and sse_algorithm is kms."
    }
  }
}
