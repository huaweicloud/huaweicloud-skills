output "cdn_domain_id" {
  description = "ID of the created CDN domain."
  value       = huaweicloud_cdn_domain.this.id
}

output "cdn_domain_name" {
  description = "Name of the created CDN domain."
  value       = huaweicloud_cdn_domain.this.name
}
