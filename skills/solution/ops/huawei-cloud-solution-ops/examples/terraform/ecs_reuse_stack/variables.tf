variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "subnet_id" {
  description = "Existing subnet ID discovered from Huawei Cloud."
  type        = string
}

variable "security_group_id" {
  description = "Existing security group ID discovered from Huawei Cloud."
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
