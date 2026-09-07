output "vpc_id" {
  description = "Created VPC ID."
  value       = huaweicloud_vpc.this.id
}

output "subnet_id" {
  description = "Created subnet ID."
  value       = huaweicloud_vpc_subnet.this.id
}

output "apig_instance_id" {
  description = "Created APIG instance ID."
  value       = huaweicloud_apig_instance.this.id
}

output "apig_plugin_id" {
  description = "Created APIG plugin ID."
  value       = huaweicloud_apig_plugin.this.id
}
