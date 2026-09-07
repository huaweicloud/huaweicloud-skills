resource "huaweicloud_vpc" "this" {
  name = var.vpc_name
  cidr = var.vpc_cidr

  tags = var.tags
}

resource "huaweicloud_vpc_subnet" "this" {
  vpc_id     = huaweicloud_vpc.this.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip
}

resource "huaweicloud_networking_secgroup" "this" {
  name = var.security_group_name
}

resource "huaweicloud_networking_secgroup_rule" "postgres_ingress" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 5432
  port_range_max    = 5432
  remote_ip_prefix  = var.vpc_cidr
  security_group_id = huaweicloud_networking_secgroup.this.id
}

data "huaweicloud_rds_flavors" "this" {
  count = var.rds_flavor == null ? 1 : 0

  db_type           = "PostgreSQL"
  db_version        = var.db_version
  instance_mode     = var.rds_instance_mode
  group_type        = var.rds_flavor_group_type
  vcpus             = var.rds_flavor_vcpus
  memory            = var.rds_flavor_memory
  availability_zone = var.availability_zone
}

locals {
  selected_rds_flavor = var.rds_flavor != null ? var.rds_flavor : try(data.huaweicloud_rds_flavors.this[0].flavors[0].name, null)
}

resource "huaweicloud_rds_instance" "this" {
  name              = var.rds_name
  flavor            = local.selected_rds_flavor
  vpc_id            = huaweicloud_vpc.this.id
  subnet_id         = huaweicloud_vpc_subnet.this.id
  security_group_id = huaweicloud_networking_secgroup.this.id
  availability_zone = [var.availability_zone]

  db {
    type     = "PostgreSQL"
    version  = var.db_version
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
      error_message = "No RDS flavor matched the requested engine version, instance mode, group type, vCPU, memory, and AZ filters. Set rds_flavor explicitly or adjust the discovery inputs."
    }
  }
}
