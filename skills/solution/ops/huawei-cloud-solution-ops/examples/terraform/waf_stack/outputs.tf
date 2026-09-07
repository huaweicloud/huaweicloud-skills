output "waf_cloud_instance_id" {
  description = "Created WAF cloud instance ID."
  value       = huaweicloud_waf_cloud_instance.this.id
}

output "waf_domain_id" {
  description = "Created WAF domain ID."
  value       = huaweicloud_waf_domain.this.id
}
