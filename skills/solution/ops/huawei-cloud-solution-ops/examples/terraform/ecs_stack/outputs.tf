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

output "instance_id" {
  description = "Created ECS instance ID."
  value       = huaweicloud_compute_instance.this.id
}
