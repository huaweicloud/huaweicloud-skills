data "huaweicloud_vpn_gateway_availability_zones" "current" {
  flavor          = var.vpn_gateway_flavor
  attachment_type = var.vpn_gateway_attachment_type
}

locals {
  selected_availability_zones = slice(data.huaweicloud_vpn_gateway_availability_zones.current.names, 0, 2)
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

resource "huaweicloud_vpc_eip" "this" {
  count = 2

  publicip {
    type = var.eip_type
  }

  bandwidth {
    name        = "${var.bandwidth_name}-${count.index + 1}"
    size        = var.bandwidth_size
    share_type  = var.bandwidth_share_type
    charge_mode = var.bandwidth_charge_mode
  }
}

resource "huaweicloud_vpn_gateway" "this" {
  name               = var.vpn_gateway_name
  vpc_id             = huaweicloud_vpc.this.id
  local_subnets      = [huaweicloud_vpc_subnet.this.cidr]
  connect_subnet     = huaweicloud_vpc_subnet.this.id
  availability_zones = local.selected_availability_zones

  eip1 {
    id = huaweicloud_vpc_eip.this[0].id
  }

  eip2 {
    id = huaweicloud_vpc_eip.this[1].id
  }

  delete_eip_on_termination = var.delete_eip_on_termination

  lifecycle {
    precondition {
      condition     = length(local.selected_availability_zones) == 2
      error_message = "The selected VPN gateway flavor and attachment type did not return two availability zones."
    }
  }
}
