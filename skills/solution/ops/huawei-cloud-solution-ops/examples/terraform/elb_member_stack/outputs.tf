output "loadbalancer_id" {
  description = "Created ELB load balancer ID."
  value       = huaweicloud_lb_loadbalancer.this.id
}

output "loadbalancer_public_ip" {
  description = "Associated public IP of the ELB."
  value       = huaweicloud_lb_loadbalancer.this.public_ip
}

output "backend_member_id" {
  description = "Created backend member ID."
  value       = huaweicloud_lb_member.this.id
}

output "monitor_id" {
  description = "Created ELB health monitor ID."
  value       = huaweicloud_lb_monitor.this.id
}
