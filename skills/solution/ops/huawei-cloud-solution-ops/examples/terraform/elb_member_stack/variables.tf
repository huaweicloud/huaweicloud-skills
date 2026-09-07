variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "vpc_name" {
  description = "Name of the VPC to create."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC."
  type        = string
}

variable "subnet_name" {
  description = "Name of the subnet to create."
  type        = string
}

variable "subnet_cidr" {
  description = "CIDR block of the subnet."
  type        = string
}

variable "subnet_gateway_ip" {
  description = "Gateway IP address of the subnet."
  type        = string
}

variable "subnet_dns_list" {
  description = "DNS servers of the subnet used by the ELB member example."
  type        = list(string)
  default     = ["100.125.1.250", "100.125.21.250"]
}

variable "loadbalancer_name" {
  description = "Name of the ELB load balancer."
  type        = string
}

variable "listener_name" {
  description = "Name of the ELB listener."
  type        = string
  default     = "terraform-listener"
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
  description = "Name of the ELB backend pool."
  type        = string
  default     = "terraform-pool"
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

variable "create_eip" {
  description = "Whether to create and associate an EIP for the ELB."
  type        = bool
  default     = true
}

variable "eip_address" {
  description = "Optional existing public EIP ID used for ELB association when create_eip is false."
  type        = string
  default     = null
}

variable "bandwidth_name" {
  description = "Bandwidth name used when create_eip is true."
  type        = string
  default     = "elb-member-bandwidth"
}

variable "bandwidth_size" {
  description = "Bandwidth size in Mbit/s used when create_eip is true."
  type        = number
  default     = 5
}

variable "bandwidth_share_type" {
  description = "Bandwidth share type used when create_eip is true."
  type        = string
  default     = "PER"
}

variable "bandwidth_charge_mode" {
  description = "Bandwidth charge mode used when create_eip is true."
  type        = string
  default     = "traffic"
}

variable "instance_name" {
  description = "Name of the backend ECS instance."
  type        = string
}

variable "image_name" {
  description = "Public image name used to discover the ECS image."
  type        = string
  default     = "Ubuntu 20.04 server 64bit"
}

variable "image_visibility" {
  description = "Image visibility used when searching for the image."
  type        = string
  default     = "public"
}

variable "instance_flavor_performance_type" {
  description = "Flavor performance type used for ECS flavor discovery."
  type        = string
  default     = "normal"
}

variable "instance_flavor_cpu_core_count" {
  description = "Target CPU core count used for ECS flavor discovery."
  type        = number
  default     = 2
}

variable "instance_flavor_memory_size" {
  description = "Target memory size in GB used for ECS flavor discovery."
  type        = number
  default     = 4
}

variable "backend_protocol_port" {
  description = "Backend member port."
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

variable "security_group_ingress_cidr" {
  description = "CIDR allowed to reach the backend member port. Avoid 0.0.0.0/0 in production."
  type        = string
}

variable "admin_password" {
  description = "Administrator password used by the backend ECS instance."
  type        = string
  sensitive   = true
}

variable "system_disk_type" {
  description = "System disk type of the backend ECS instance."
  type        = string
  default     = "SAS"
}

variable "system_disk_size" {
  description = "System disk size in GB."
  type        = number
  default     = 40
}

variable "tags" {
  description = "Common tags applied to supported resources."
  type        = map(string)
  default = {
    ManagedBy = "terraform"
  }
}
