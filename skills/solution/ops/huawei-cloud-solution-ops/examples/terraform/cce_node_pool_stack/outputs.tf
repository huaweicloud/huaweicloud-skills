output "availability_zone" {
  description = "Availability zone selected for the subnet and node pool."
  value       = data.huaweicloud_availability_zones.current.names[0]
}

output "cluster_id" {
  description = "Created CCE cluster ID."
  value       = huaweicloud_cce_cluster.this.id
}

output "cluster_flavor_id" {
  description = "Flavor selected for the CCE cluster."
  value       = local.selected_cluster_flavor
}

output "node_pool_id" {
  description = "Created CCE node pool ID."
  value       = huaweicloud_cce_node_pool.this.id
}

output "node_flavor_id" {
  description = "Flavor selected for the CCE node pool."
  value       = local.selected_node_flavor
}

output "cluster_eip" {
  description = "CCE cluster API EIP."
  value       = var.create_eip ? huaweicloud_vpc_eip.this[0].address : var.eip_address
}
