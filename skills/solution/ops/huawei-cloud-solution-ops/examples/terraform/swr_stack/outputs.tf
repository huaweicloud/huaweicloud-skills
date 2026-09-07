output "organization_name" {
  description = "Created SWR organization name."
  value       = huaweicloud_swr_organization.this.name
}

output "repository_id" {
  description = "Created SWR repository ID."
  value       = huaweicloud_swr_repository.this.id
}
