output "eip_id" {
  description = "Created EIP ID."
  value       = huaweicloud_vpc_eip.this.id
}

output "eip_address" {
  description = "Created EIP address."
  value       = huaweicloud_vpc_eip.this.address
}

output "eip_status" {
  description = "Current status of the EIP."
  value       = huaweicloud_vpc_eip.this.status
}
