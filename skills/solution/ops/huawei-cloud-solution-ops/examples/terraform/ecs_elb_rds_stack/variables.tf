variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "vpc_name" {
  description = "Name of the VPC."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC."
  type        = string
  default     = "192.168.0.0/16"
}

variable "subnet_name" {
  description = "Name of the subnet."
  type        = string
}

variable "subnet_cidr" {
  description = "CIDR block of the subnet."
  type        = string
  default     = "192.168.1.0/24"
}

variable "subnet_gateway_ip" {
  description = "Gateway IP address of the subnet."
  type        = string
  default     = "192.168.1.1"
}

variable "subnet_dns_list" {
  description = "DNS servers for the subnet."
  type        = list(string)
  default     = ["100.125.1.250", "100.125.21.250"]
}

variable "web_security_group_name" {
  description = "Name of the web security group."
  type        = string
}

variable "db_security_group_name" {
  description = "Name of the database security group."
  type        = string
}

variable "web_ingress_cidr" {
  description = "CIDR allowed to access the web listener. Avoid 0.0.0.0/0 for sensitive ports."
  type        = string
}

variable "web_port" {
  description = "Web service port on the ECS instance."
  type        = number
  default     = 8080
}

variable "instance_name" {
  description = "Name of the web ECS instance."
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
  description = "ECS flavor performance type."
  type        = string
  default     = "normal"
}

variable "instance_flavor_cpu_core_count" {
  description = "ECS CPU core count."
  type        = number
  default     = 2
}

variable "instance_flavor_memory_size" {
  description = "ECS memory size in GB."
  type        = number
  default     = 4
}

variable "admin_password" {
  description = "Administrator password for the ECS instance."
  type        = string
  sensitive   = true
}

variable "user_data" {
  description = "Optional cloud-init user data. Do not put secrets here."
  type        = string
  default     = ""
}

variable "system_disk_type" {
  description = "System disk type."
  type        = string
  default     = "SAS"
}

variable "system_disk_size" {
  description = "System disk size in GB."
  type        = number
  default     = 40
}

variable "rds_name" {
  description = "Name of the RDS instance."
  type        = string
}

variable "rds_db_type" {
  description = "RDS engine type."
  type        = string
  default     = "PostgreSQL"
}

variable "rds_db_version" {
  description = "RDS engine version."
  type        = string
  default     = "12"
}

variable "rds_port" {
  description = "RDS service port."
  type        = number
  default     = 5432
}

variable "rds_password" {
  description = "RDS root password. Provide through a local tfvars file or environment-specific secret handling."
  type        = string
  sensitive   = true
}

variable "rds_flavor" {
  description = "Explicit RDS flavor. Leave empty to discover one by filters."
  type        = string
  default     = ""
}

variable "rds_instance_mode" {
  description = "RDS instance mode."
  type        = string
  default     = "single"
}

variable "rds_flavor_group_type" {
  description = "RDS flavor group type."
  type        = string
  default     = "general"
}

variable "rds_flavor_vcpus" {
  description = "RDS flavor vCPU filter."
  type        = number
  default     = 2
}

variable "rds_flavor_memory" {
  description = "RDS flavor memory filter in GB."
  type        = number
  default     = 4
}

variable "rds_volume_type" {
  description = "RDS volume type."
  type        = string
  default     = "CLOUDSSD"
}

variable "rds_volume_size" {
  description = "RDS volume size in GB."
  type        = number
  default     = 40
}

variable "rds_backup_start_time" {
  description = "RDS backup start time."
  type        = string
  default     = "03:00-04:00"
}

variable "rds_backup_keep_days" {
  description = "RDS backup keep days."
  type        = number
  default     = 7
}

variable "loadbalancer_name" {
  description = "Name of the ELB load balancer."
  type        = string
}

variable "create_eip" {
  description = "Whether to create and bind an EIP to the ELB."
  type        = bool
  default     = true
}

variable "bandwidth_name" {
  description = "Bandwidth name used when create_eip is true."
  type        = string
  default     = "ecs-elb-rds-bandwidth"
}

variable "bandwidth_size" {
  description = "Bandwidth size in Mbit/s."
  type        = number
  default     = 5
}

variable "listener_name" {
  description = "Name of the HTTP listener."
  type        = string
  default     = "web-listener"
}

variable "listener_port" {
  description = "HTTP listener port."
  type        = number
  default     = 80
}

variable "pool_name" {
  description = "Name of the backend pool."
  type        = string
  default     = "web-pool"
}

variable "monitor_url_path" {
  description = "HTTP health monitor path."
  type        = string
  default     = "/"
}

variable "tags" {
  description = "Common tags applied to supported resources."
  type        = map(string)
  default = {
    ManagedBy = "terraform"
  }
}
