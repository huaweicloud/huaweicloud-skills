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

variable "rds_name" {
  description = "Name of the RDS instance."
  type        = string
}

variable "rds_flavor" {
  description = "Optional explicit flavor code of the RDS instance. Leave null to discover a matching flavor."
  type        = string
  default     = null
}

variable "availability_zone" {
  description = "Availability zone used by the RDS instance."
  type        = string
}

variable "rds_password" {
  description = "Administrator password of the PostgreSQL instance."
  type        = string
  sensitive   = true
}

variable "db_version" {
  description = "PostgreSQL engine version."
  type        = string
  default     = "12"
}

variable "rds_instance_mode" {
  description = "RDS instance mode used during flavor discovery."
  type        = string
  default     = "single"
}

variable "rds_flavor_group_type" {
  description = "RDS flavor group type used during flavor discovery."
  type        = string
  default     = "general"
}

variable "rds_flavor_vcpus" {
  description = "RDS vCPU count used during flavor discovery."
  type        = number
  default     = 2
}

variable "rds_flavor_memory" {
  description = "RDS memory size in GB used during flavor discovery."
  type        = number
  default     = 4
}

variable "volume_type" {
  description = "Volume type of the RDS instance."
  type        = string
  default     = "ULTRAHIGH"
}

variable "volume_size" {
  description = "Volume size in GB."
  type        = number
  default     = 100
}

variable "backup_start_time" {
  description = "Backup window start time range."
  type        = string
  default     = "08:00-09:00"
}

variable "backup_keep_days" {
  description = "Backup retention days."
  type        = number
  default     = 1
}

variable "tags" {
  description = "Common tags applied to supported resources."
  type        = map(string)
  default = {
    ManagedBy = "terraform"
  }
}
