output "bucket_id" {
  description = "Created OBS bucket ID."
  value       = huaweicloud_obs_bucket.this.id
}

output "bucket_name" {
  description = "Created OBS bucket name."
  value       = huaweicloud_obs_bucket.this.bucket
}

output "bucket_region" {
  description = "Region used by the OBS bucket."
  value       = var.region_name
}

output "bucket_versioning_enabled" {
  description = "Whether versioning is enabled on the bucket."
  value       = huaweicloud_obs_bucket.this.versioning
}
