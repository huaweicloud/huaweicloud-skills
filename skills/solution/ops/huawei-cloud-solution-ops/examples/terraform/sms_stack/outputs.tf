output "migration_project_id" {
  description = "ID of the SMS migration project."
  value       = huaweicloud_sms_migration_project.this.id
}

output "migration_project_name" {
  description = "Name of the SMS migration project."
  value       = huaweicloud_sms_migration_project.this.name
}
