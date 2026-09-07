output "subnet_id" {
  description = "Reused subnet ID."
  value       = data.huaweicloud_vpc_subnet.selected.id
}

output "vpc_id" {
  description = "VPC ID inferred from the reused subnet."
  value       = data.huaweicloud_vpc_subnet.selected.vpc_id
}

output "security_group_id" {
  description = "Reused security group ID."
  value       = data.huaweicloud_networking_secgroup.selected.id
}

output "availability_zone" {
  description = "Availability zone chosen for the ECS instance."
  value       = data.huaweicloud_availability_zones.current.names[0]
}

output "flavor_id" {
  description = "Flavor ID selected for the ECS instance."
  value       = local.selected_flavor_id
}

output "image_id" {
  description = "Image ID selected for the ECS instance."
  value       = data.huaweicloud_images_image.ecs.id
}

output "instance_id" {
  description = "Created ECS instance ID."
  value       = huaweicloud_compute_instance.this.id
}
