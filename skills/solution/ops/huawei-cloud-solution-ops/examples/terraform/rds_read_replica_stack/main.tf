data "huaweicloud_availability_zones" "current" {}

data "huaweicloud_rds_flavors" "primary" {
  count = var.primary_flavor == "" ? 1 : 0

  db_type           = "MySQL"
  db_version        = var.db_version
  instance_mode     = "ha"
  group_type        = var.rds_flavor_group_type
  vcpus             = var.rds_flavor_vcpus
  memory            = var.rds_flavor_memory
  availability_zone = data.huaweicloud_availability_zones.current.names[0]
}

data "huaweicloud_rds_flavors" "replica" {
  count = var.replica_flavor == "" ? 1 : 0

  db_type           = "MySQL"
  db_version        = var.db_version
  instance_mode     = "replica"
  group_type        = var.rds_flavor_group_type
  vcpus             = var.rds_flavor_vcpus
  memory            = var.rds_flavor_memory
  availability_zone = data.huaweicloud_availability_zones.current.names[0]
}

locals {
  selected_primary_flavor = var.primary_flavor != "" ? var.primary_flavor : try(data.huaweicloud_rds_flavors.primary[0].flavors[0].name, null)
  selected_replica_flavor = var.replica_flavor != "" ? var.replica_flavor : try(data.huaweicloud_rds_flavors.replica[0].flavors[0].name, null)
  selected_zones          = length(var.availability_zones) > 0 ? var.availability_zones : slice(data.huaweicloud_availability_zones.current.names, 0, 2)
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
  availability_zone = local.selected_zones[0]
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

resource "huaweicloud_rds_instance" "primary" {
  name                = var.primary_name
  flavor              = local.selected_primary_flavor
  vpc_id              = huaweicloud_vpc.this.id
  subnet_id           = huaweicloud_vpc_subnet.this.id
  security_group_id   = huaweicloud_networking_secgroup.this.id
  availability_zone   = local.selected_zones
  ha_replication_mode = var.ha_replication_mode

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
}

resource "huaweicloud_rds_read_replica_instance" "replica" {
  primary_instance_id = huaweicloud_rds_instance.primary.id
  name                = var.replica_name
  flavor              = local.selected_replica_flavor
  availability_zone   = local.selected_zones[0]
  security_group_id   = huaweicloud_networking_secgroup.this.id

  db {
    port = 3306
  }

  volume {
    type = var.replica_volume_type
    size = var.replica_volume_size
  }
}
