variable "region_name" { type = string }
variable "vpc_name" { type = string }
variable "subnet_name" { type = string }
variable "security_group_name" { type = string }
variable "primary_name" { type = string }
variable "replica_name" { type = string }
variable "rds_password" {
  type      = string
  sensitive = true
}

variable "availability_zones" {
  type    = list(string)
  default = []
}

variable "vpc_cidr" {
  type    = string
  default = "192.168.0.0/16"
}

variable "subnet_cidr" {
  type    = string
  default = "192.168.1.0/24"
}

variable "subnet_gateway_ip" {
  type    = string
  default = "192.168.1.1"
}

variable "db_version" {
  type    = string
  default = "8.0"
}

variable "primary_flavor" {
  type    = string
  default = ""
}

variable "replica_flavor" {
  type    = string
  default = ""
}

variable "rds_flavor_group_type" {
  type    = string
  default = "general"
}

variable "rds_flavor_vcpus" {
  type    = number
  default = 2
}

variable "rds_flavor_memory" {
  type    = number
  default = 4
}

variable "ha_replication_mode" {
  type    = string
  default = "async"
}

variable "volume_type" {
  type    = string
  default = "CLOUDSSD"
}

variable "volume_size" {
  type    = number
  default = 40
}

variable "replica_volume_type" {
  type    = string
  default = "CLOUDSSD"
}

variable "replica_volume_size" {
  type    = number
  default = 40
}
