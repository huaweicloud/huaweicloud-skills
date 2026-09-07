output "vpc_id" {
  description = "Created VPC ID."
  value       = huaweicloud_vpc.this.id
}

output "subnet_id" {
  description = "Created subnet ID."
  value       = huaweicloud_vpc_subnet.this.id
}

output "security_group_id" {
  description = "Created security group ID."
  value       = huaweicloud_networking_secgroup.this.id
}

output "rds_instance_id" {
  description = "Created RDS instance ID."
  value       = huaweicloud_rds_instance.this.id
}

output "rds_flavor" {
  description = "Flavor selected for the RDS instance."
  value       = local.selected_rds_flavor
}

output "rds_private_ips" {
  description = "Private IP addresses of the RDS instance."
  value       = huaweicloud_rds_instance.this.private_ips
}
