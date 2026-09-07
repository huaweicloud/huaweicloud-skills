data "huaweicloud_availability_zones" "current" {}

data "huaweicloud_rds_flavors" "this" {
  count = var.rds_flavor == "" ? 1 : 0

  db_type           = "MySQL"
  db_version        = var.db_version
  instance_mode     = "single"
  group_type        = var.rds_flavor_group_type
  vcpus             = var.rds_flavor_vcpus
  memory            = var.rds_flavor_memory
  availability_zone = data.huaweicloud_availability_zones.current.names[0]
}

locals {
  selected_rds_flavor = var.rds_flavor != "" ? var.rds_flavor : try(data.huaweicloud_rds_flavors.this[0].flavors[0].name, null)
}

resource "huaweicloud_vpc" "this" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}

resource "huaweicloud_vpc_subnet" "this" {
  vpc_id            = huaweicloud_vpc.this.id
  name              = var.subnet_name
  cidr              = var.subnet_cidr
  gateway_ip        = var.subnet_gateway_ip
  availability_zone = data.huaweicloud_availability_zones.current.names[0]
}

resource "huaweicloud_networking_secgroup" "this" {
  name                 = var.security_group_name
  delete_default_rules = true
}

resource "huaweicloud_networking_secgroup_rule" "mysql_ingress" {
  security_group_id = huaweicloud_networking_secgroup.this.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  ports             = "3306"
  remote_ip_prefix  = var.vpc_cidr
}

resource "huaweicloud_rds_instance" "this" {
  name              = var.rds_name
  flavor            = local.selected_rds_flavor
  vpc_id            = huaweicloud_vpc.this.id
  subnet_id         = huaweicloud_vpc_subnet.this.id
  security_group_id = huaweicloud_networking_secgroup.this.id
  availability_zone = [data.huaweicloud_availability_zones.current.names[0]]

  db {
    type     = "MySQL"
    version  = var.db_version
    port     = 3306
    password = var.rds_password
  }

  volume {
    type = var.volume_type
    size = var.volume_size
  }

  backup_strategy {
    start_time = var.backup_start_time
    keep_days  = var.backup_keep_days
  }

  lifecycle {
    precondition {
      condition     = local.selected_rds_flavor != null
      error_message = "No MySQL RDS flavor matched the requested filters."
    }
  }
}
