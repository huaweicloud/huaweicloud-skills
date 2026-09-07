output "availability_zone" {
  description = "Availability zone selected for the subnet."
  value       = data.huaweicloud_availability_zones.current.names[0]
}

output "cluster_flavor_id" {
  description = "Flavor selected for the CCE cluster."
  value       = local.selected_cluster_flavor
}

output "vpc_id" {
  description = "Created VPC ID."
  value       = huaweicloud_vpc.this.id
}

output "subnet_id" {
  description = "Created subnet ID."
  value       = huaweicloud_vpc_subnet.this.id
}

output "cluster_id" {
  description = "Created CCE cluster ID."
  value       = huaweicloud_cce_cluster.this.id
}

output "cluster_status" {
  description = "CCE cluster status."
  value       = huaweicloud_cce_cluster.this.status
}

output "cluster_eip" {
  description = "CCE cluster API EIP."
  value       = var.create_eip ? huaweicloud_vpc_eip.this[0].address : var.eip_address
}
