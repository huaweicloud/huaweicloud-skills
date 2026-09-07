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

variable "nat_gateway_name" {
  description = "Name of the NAT gateway."
  type        = string
}

variable "nat_gateway_description" {
  description = "Description of the NAT gateway."
  type        = string
  default     = ""
}

variable "nat_gateway_spec" {
  description = "Specification of the NAT gateway."
  type        = string
  default     = "1"
}

variable "eip_bandwidth_name" {
  description = "Bandwidth name of the NAT EIP."
  type        = string
  default     = "nat-dnat-bandwidth"
}

variable "eip_bandwidth_size" {
  description = "Bandwidth size in Mbit/s of the NAT EIP."
  type        = number
  default     = 5
}

variable "eip_bandwidth_share_type" {
  description = "Bandwidth share type of the NAT EIP."
  type        = string
  default     = "PER"
}

variable "eip_bandwidth_charge_mode" {
  description = "Bandwidth charge mode of the NAT EIP."
  type        = string
  default     = "traffic"
}

variable "frontend_protocol" {
  description = "Protocol exposed by the DNAT rule."
  type        = string
  default     = "tcp"
}

variable "frontend_port" {
  description = "External service port exposed by the DNAT rule."
  type        = number
  default     = 8080
}

variable "backend_protocol" {
  description = "Protocol allowed by the backend security group rule."
  type        = string
  default     = "tcp"
}

variable "backend_port" {
  description = "Internal service port exposed by the backend ECS."
  type        = number
  default     = 80
}

variable "ingress_cidr" {
  description = "CIDR allowed to access the backend port. Avoid 0.0.0.0/0 in production."
  type        = string
}

variable "instance_name" {
  description = "Name of the ECS instance."
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

variable "admin_password" {
  description = "Administrator password used by the ECS instance."
  type        = string
  sensitive   = true
}

variable "system_disk_type" {
  description = "System disk type of the ECS instance."
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
