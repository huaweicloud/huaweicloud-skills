variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "loadbalancer_id" {
  description = "Existing ELB load balancer ID discovered with hcloud."
  type        = string
}

variable "listener_name" {
  description = "Name of the listener to add to the existing ELB."
  type        = string
  default     = "reuse-listener"
}

variable "listener_protocol" {
  description = "Listener protocol."
  type        = string
  default     = "HTTP"
}

variable "listener_port" {
  description = "Listener port."
  type        = number
  default     = 80
}

variable "pool_name" {
  description = "Name of the backend pool."
  type        = string
  default     = "reuse-pool"
}

variable "pool_protocol" {
  description = "Backend pool protocol."
  type        = string
  default     = "HTTP"
}

variable "pool_method" {
  description = "Load balancing method."
  type        = string
  default     = "ROUND_ROBIN"
}

variable "backend_address" {
  description = "Backend ECS private IP or supported backend address confirmed with hcloud."
  type        = string
}

variable "backend_subnet_id" {
  description = "Backend subnet IPv4 subnet ID confirmed to match the backend address."
  type        = string
}

variable "backend_protocol_port" {
  description = "Backend service port."
  type        = number
  default     = 8080
}

variable "backend_member_weight" {
  description = "Backend member weight."
  type        = number
  default     = 1
}

variable "monitor_type" {
  description = "Health monitor type."
  type        = string
  default     = "HTTP"
}

variable "monitor_delay" {
  description = "Health monitor delay in seconds."
  type        = number
  default     = 5
}

variable "monitor_timeout" {
  description = "Health monitor timeout in seconds."
  type        = number
  default     = 3
}

variable "monitor_max_retries" {
  description = "Health monitor max retries."
  type        = number
  default     = 3
}

variable "monitor_url_path" {
  description = "Health monitor URL path for HTTP checks."
  type        = string
  default     = "/"
}

variable "monitor_expected_codes" {
  description = "Expected HTTP status codes for HTTP health checks."
  type        = string
  default     = "200-399"
}
