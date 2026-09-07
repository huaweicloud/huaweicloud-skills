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

resource "huaweicloud_nat_gateway" "this" {
  name        = var.nat_gateway_name
  description = var.nat_gateway_description
  spec        = var.nat_gateway_spec
  vpc_id      = huaweicloud_vpc.this.id
  subnet_id   = huaweicloud_vpc_subnet.this.id

  tags = var.tags
}

resource "huaweicloud_vpc_eip" "this" {
  publicip {
    type = "5_bgp"
  }

  bandwidth {
    name        = var.bandwidth_name
    size        = var.bandwidth_size
    share_type  = var.bandwidth_share_type
    charge_mode = var.bandwidth_charge_mode
  }

  tags = var.tags
}

resource "huaweicloud_nat_snat_rule" "this" {
  nat_gateway_id = huaweicloud_nat_gateway.this.id
  floating_ip_id = huaweicloud_vpc_eip.this.id
  source_type    = var.snat_source_type
  subnet_id      = var.snat_source_type == 0 ? huaweicloud_vpc_subnet.this.id : null
  cidr           = var.snat_source_type == 1 ? var.snat_cidr : null
  description    = var.snat_description

  lifecycle {
    precondition {
      condition     = var.snat_source_type == 0 || (var.snat_cidr != null && trimspace(var.snat_cidr) != "")
      error_message = "snat_cidr must be provided when snat_source_type is 1."
    }
  }
}
