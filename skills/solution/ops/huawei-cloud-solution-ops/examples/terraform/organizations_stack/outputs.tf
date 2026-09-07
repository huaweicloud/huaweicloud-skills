output "organization_account_id" {
  description = "ID of the created organization account."
  value       = huaweicloud_organizations_account.this.id
}

output "organization_account_name" {
  description = "Name of the created organization account."
  value       = huaweicloud_organizations_account.this.name
}
