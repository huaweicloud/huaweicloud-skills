variable "region_name" { type = string }
variable "vpc_name" { type = string }
variable "subnet_name" { type = string }
variable "security_group_name" { type = string }
variable "rds_name" { type = string }
variable "rds_password" {
  type      = string
  sensitive = true
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

variable "mysql_ingress_cidr" {
  type    = string
  default = "203.0.113.10/32"
}

variable "db_version" {
  type    = string
  default = "8.0"
}

variable "rds_flavor" {
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

variable "volume_type" {
  type    = string
  default = "CLOUDSSD"
}

variable "volume_size" {
  type    = number
  default = 40
}

variable "create_eip" {
  type    = bool
  default = true
}

variable "existing_public_ip" {
  type    = string
  default = ""
}

variable "existing_public_ip_id" {
  type    = string
  default = ""
}

variable "bandwidth_name" {
  type    = string
  default = "rds-mysql-eip-bandwidth"
}

variable "bandwidth_size" {
  type    = number
  default = 5
}
