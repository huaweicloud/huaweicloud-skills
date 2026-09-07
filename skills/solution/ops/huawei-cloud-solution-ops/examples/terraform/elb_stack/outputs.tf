output "loadbalancer_id" {
  description = "Created ELB load balancer ID."
  value       = huaweicloud_lb_loadbalancer.this.id
}

output "loadbalancer_public_ip" {
  description = "Associated public IP of the ELB."
  value       = huaweicloud_lb_loadbalancer.this.public_ip
}

output "listener_id" {
  description = "Created ELB listener ID."
  value       = huaweicloud_lb_listener.this.id
}

output "pool_id" {
  description = "Created ELB backend pool ID."
  value       = huaweicloud_lb_pool.this.id
}
