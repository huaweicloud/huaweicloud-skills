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
  dns_list   = var.subnet_dns_list
}

resource "huaweicloud_lb_loadbalancer" "this" {
  name          = var.loadbalancer_name
  vip_subnet_id = huaweicloud_vpc_subnet.this.ipv4_subnet_id

  tags = var.tags
}

resource "huaweicloud_vpc_eip" "this" {
  count = var.create_eip ? 1 : 0

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

resource "huaweicloud_vpc_eipv3_associate" "this" {
  count = var.create_eip || var.eip_address != null ? 1 : 0

  publicip_id             = var.create_eip ? huaweicloud_vpc_eip.this[0].id : var.eip_address
  associate_instance_type = "ELB"
  associate_instance_id   = huaweicloud_lb_loadbalancer.this.id
}

resource "huaweicloud_lb_listener" "this" {
  loadbalancer_id = huaweicloud_lb_loadbalancer.this.id
  name            = var.listener_name
  protocol        = var.listener_protocol
  protocol_port   = var.listener_port
}

resource "huaweicloud_lb_pool" "this" {
  listener_id = huaweicloud_lb_listener.this.id
  name        = var.pool_name
  protocol    = var.pool_protocol
  lb_method   = var.pool_method
}
