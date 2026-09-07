output "nat_gateway_id" {
  description = "Created NAT gateway ID."
  value       = huaweicloud_nat_gateway.this.id
}

output "nat_gateway_status" {
  description = "Current NAT gateway status."
  value       = huaweicloud_nat_gateway.this.status
}

output "snat_rule_id" {
  description = "Created SNAT rule ID."
  value       = huaweicloud_nat_snat_rule.this.id
}

output "nat_eip_address" {
  description = "Created EIP address used by the NAT gateway."
  value       = huaweicloud_vpc_eip.this.address
}
