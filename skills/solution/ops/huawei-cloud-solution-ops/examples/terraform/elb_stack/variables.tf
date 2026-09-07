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
  description = "DNS servers of the subnet used by the ELB example."
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
  default     = "elb-bandwidth"
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

variable "tags" {
  description = "Common tags applied to supported resources."
  type        = map(string)
  default = {
    ManagedBy = "terraform"
  }
}
