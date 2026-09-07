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

variable "security_group_name" {
  description = "Name of the security group to create."
  type        = string
}

variable "instance_name" {
  description = "Name of the ECS instance that backs the endpoint service."
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
  description = "Flavor performance type used for flavor discovery."
  type        = string
  default     = "normal"
}

variable "instance_flavor_cpu_core_count" {
  description = "Target CPU core count used for flavor discovery."
  type        = number
  default     = 2
}

variable "instance_flavor_memory_size" {
  description = "Target memory size in GB used for flavor discovery."
  type        = number
  default     = 4
}

variable "key_pair_name" {
  description = "Existing key pair name used to log in to the ECS instance."
  type        = string
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

variable "endpoint_service_name" {
  description = "Name of the VPCEP service to create."
  type        = string
}

variable "endpoint_service_type" {
  description = "Server type of the VPCEP service."
  type        = string
  default     = "VM"
}

variable "endpoint_service_port_mapping" {
  description = "Port mapping exposed by the VPCEP service."
  type = list(object({
    service_port  = number
    terminal_port = number
  }))
  default = [
    {
      service_port  = 8080
      terminal_port = 8080
    }
  ]
}

variable "endpoint_name" {
  description = "Name tag used for the VPCEP endpoint."
  type        = string
}

variable "tags" {
  description = "Common tags applied to supported resources."
  type        = map(string)
  default = {
    ManagedBy = "terraform"
  }
}
