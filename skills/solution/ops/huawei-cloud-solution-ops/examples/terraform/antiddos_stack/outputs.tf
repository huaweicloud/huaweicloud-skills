output "antiddos_id" {
  description = "ID of the Anti-DDoS basic configuration."
  value       = huaweicloud_antiddos_basic.this.id
}

output "eip_id" {
  description = "ID of the protected EIP."
  value       = huaweicloud_vpc_eip.this.id
}
