data "huaweicloud_availability_zones" "current" {}

locals {
  selected_availability_zone = coalesce(var.availability_zone, try(data.huaweicloud_availability_zones.current.names[0], null))
}

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

resource "huaweicloud_networking_secgroup" "this" {
  name                 = var.security_group_name
  delete_default_rules = true
}

resource "huaweicloud_sfs_turbo" "this" {
  vpc_id            = huaweicloud_vpc.this.id
  subnet_id         = huaweicloud_vpc_subnet.this.id
  security_group_id = huaweicloud_networking_secgroup.this.id
  availability_zone = local.selected_availability_zone
  name              = var.turbo_name
  size              = var.turbo_size
  share_proto       = var.share_proto
  share_type        = var.share_type
  hpc_bandwidth     = var.hpc_bandwidth
  charging_mode     = var.charging_mode
  period_unit       = var.period_unit
  period            = var.period

  lifecycle {
    precondition {
      condition     = var.share_type != "HPC" || var.hpc_bandwidth != null
      error_message = "hpc_bandwidth must be provided when share_type is HPC."
    }

    precondition {
      condition     = var.charging_mode != "prePaid" || (var.period_unit != null && var.period != null)
      error_message = "period_unit and period must be provided when charging_mode is prePaid."
    }
  }
}
