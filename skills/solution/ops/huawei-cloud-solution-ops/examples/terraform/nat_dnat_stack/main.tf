data "huaweicloud_availability_zones" "current" {}

data "huaweicloud_compute_flavors" "ecs" {
  availability_zone = data.huaweicloud_availability_zones.current.names[0]
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}

locals {
  selected_flavor_id = try(data.huaweicloud_compute_flavors.ecs.flavors[0].id, null)
}

data "huaweicloud_images_image" "ecs" {
  name        = var.image_name
  visibility  = var.image_visibility
  most_recent = true
}

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
    name        = var.eip_bandwidth_name
    size        = var.eip_bandwidth_size
    share_type  = var.eip_bandwidth_share_type
    charge_mode = var.eip_bandwidth_charge_mode
  }

  tags = var.tags
}

resource "huaweicloud_networking_secgroup" "this" {
  name = "${var.instance_name}-sg"
}

resource "huaweicloud_networking_secgroup_rule" "ingress" {
  security_group_id = huaweicloud_networking_secgroup.this.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = var.backend_protocol
  port_range_min    = var.backend_port
  port_range_max    = var.backend_port
  remote_ip_prefix  = var.ingress_cidr
}

resource "huaweicloud_networking_secgroup_rule" "egress" {
  security_group_id = huaweicloud_networking_secgroup.this.id
  direction         = "egress"
  ethertype         = "IPv4"
  remote_ip_prefix  = "0.0.0.0/0"
}

resource "huaweicloud_compute_instance" "this" {
  name               = var.instance_name
  availability_zone  = data.huaweicloud_availability_zones.current.names[0]
  flavor_id          = local.selected_flavor_id
  image_id           = data.huaweicloud_images_image.ecs.id
  security_group_ids = [huaweicloud_networking_secgroup.this.id]
  system_disk_type   = var.system_disk_type
  system_disk_size   = var.system_disk_size
  admin_pass         = var.admin_password

  network {
    uuid = huaweicloud_vpc_subnet.this.id
  }

  lifecycle {
    precondition {
      condition     = local.selected_flavor_id != null
      error_message = "No ECS flavor matched the requested AZ, performance type, CPU, and memory filters."
    }
  }
}

resource "huaweicloud_nat_dnat_rule" "this" {
  nat_gateway_id        = huaweicloud_nat_gateway.this.id
  floating_ip_id        = huaweicloud_vpc_eip.this.id
  port_id               = huaweicloud_compute_instance.this.network[0].port
  protocol              = var.frontend_protocol
  internal_service_port = var.backend_port
  external_service_port = var.frontend_port
}
