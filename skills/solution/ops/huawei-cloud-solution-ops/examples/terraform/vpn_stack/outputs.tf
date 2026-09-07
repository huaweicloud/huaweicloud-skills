output "vpn_gateway_id" {
  description = "ID of the created VPN gateway."
  value       = huaweicloud_vpn_gateway.this.id
}

output "vpn_gateway_name" {
  description = "Name of the created VPN gateway."
  value       = huaweicloud_vpn_gateway.this.name
}
