output "zone_id" {
  description = "Created DNS zone ID."
  value       = huaweicloud_dns_zone.this.id
}

output "zone_name" {
  description = "Created DNS zone name."
  value       = huaweicloud_dns_zone.this.name
}
