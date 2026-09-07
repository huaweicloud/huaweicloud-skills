output "nat_gateway_id" {
  description = "Created NAT gateway ID."
  value       = huaweicloud_nat_gateway.this.id
}

output "dnat_rule_id" {
  description = "Created DNAT rule ID."
  value       = huaweicloud_nat_dnat_rule.this.id
}

output "public_eip_address" {
  description = "Public EIP address used by the DNAT rule."
  value       = huaweicloud_vpc_eip.this.address
}

output "backend_private_ip" {
  description = "Private IP address of the backend ECS."
  value       = huaweicloud_compute_instance.this.access_ip_v4
}
