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

output "backend_instance_id" {
  description = "Created ECS instance ID used by the endpoint service."
  value       = huaweicloud_compute_instance.this.id
}

output "vpcep_service_id" {
  description = "Created VPCEP service ID."
  value       = huaweicloud_vpcep_service.this.id
}

output "vpcep_endpoint_id" {
  description = "Created VPCEP endpoint ID."
  value       = huaweicloud_vpcep_endpoint.this.id
}
