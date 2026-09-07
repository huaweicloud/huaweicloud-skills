output "resource_share_id" {
  description = "ID of the RAM resource share."
  value       = huaweicloud_ram_resource_share.this.id
}

output "resource_share_name" {
  description = "Name of the RAM resource share."
  value       = huaweicloud_ram_resource_share.this.name
}
