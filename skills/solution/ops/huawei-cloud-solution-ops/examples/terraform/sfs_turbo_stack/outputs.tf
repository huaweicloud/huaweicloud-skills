output "turbo_id" {
  description = "ID of the created SFS Turbo file system."
  value       = huaweicloud_sfs_turbo.this.id
}

output "turbo_name" {
  description = "Name of the created SFS Turbo file system."
  value       = huaweicloud_sfs_turbo.this.name
}
