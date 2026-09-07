resource "huaweicloud_vpc" "this" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}

resource "huaweicloud_vpc_subnet" "this" {
  vpc_id     = huaweicloud_vpc.this.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip
}

data "huaweicloud_availability_zones" "current" {
  count = var.availability_zone == null ? 1 : 0
}

data "huaweicloud_dcs_flavors" "current" {
  count = var.instance_flavor_id == null ? 1 : 0

  cache_mode     = "single"
  capacity       = var.instance_capacity
  engine_version = var.instance_engine_version
}

locals {
  selected_availability_zone = var.availability_zone != null ? var.availability_zone : try(data.huaweicloud_availability_zones.current[0].names[0], null)
  selected_flavor_id         = var.instance_flavor_id != null ? var.instance_flavor_id : try(data.huaweicloud_dcs_flavors.current[0].flavors[0].name, null)
}

resource "huaweicloud_dcs_instance" "this" {
  name               = var.instance_name
  engine             = "Redis"
  engine_version     = var.instance_engine_version
  capacity           = var.instance_capacity
  flavor             = local.selected_flavor_id
  availability_zones = [local.selected_availability_zone]
  vpc_id             = huaweicloud_vpc.this.id
  subnet_id          = huaweicloud_vpc_subnet.this.id
  password           = var.instance_password

  lifecycle {
    ignore_changes = [
      flavor,
      availability_zones,
    ]

    precondition {
      condition     = local.selected_flavor_id != null
      error_message = "No DCS flavor matched the requested capacity and engine version. Set instance_flavor_id explicitly or adjust the discovery filters."
    }

    precondition {
      condition     = local.selected_availability_zone != null
      error_message = "No availability zone could be selected for the DCS instance. Set availability_zone explicitly or confirm the region."
    }
  }
}
