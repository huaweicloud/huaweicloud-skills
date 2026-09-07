resource "huaweicloud_vpc_eip" "this" {
  name = var.eip_name

  publicip {
    type = var.eip_type
  }

  bandwidth {
    name        = var.bandwidth_name
    size        = var.bandwidth_size
    share_type  = var.bandwidth_share_type
    charge_mode = var.bandwidth_charge_mode
  }

  tags = var.tags
}
