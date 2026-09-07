output "vpc_id" {
  description = "Created VPC ID."
  value       = huaweicloud_vpc.this.id
}

output "subnet_id" {
  description = "Created subnet ID."
  value       = huaweicloud_vpc_subnet.this.id
}

output "dcs_instance_id" {
  description = "Created DCS instance ID."
  value       = huaweicloud_dcs_instance.this.id
}

output "dcs_flavor" {
  description = "Flavor selected for the DCS instance."
  value       = local.selected_flavor_id
}
