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

resource "huaweicloud_networking_secgroup" "this" {
  name = "${var.instance_name}-sg"
}

resource "huaweicloud_networking_secgroup_rule" "ingress" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  ports             = tostring(var.backend_protocol_port)
  remote_ip_prefix  = var.security_group_ingress_cidr
  security_group_id = huaweicloud_networking_secgroup.this.id
}

resource "huaweicloud_compute_instance" "this" {
  name               = var.instance_name
  image_id           = data.huaweicloud_images_image.ecs.id
  flavor_id          = local.selected_flavor_id
  availability_zone  = data.huaweicloud_availability_zones.current.names[0]
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

resource "huaweicloud_lb_member" "this" {
  pool_id       = huaweicloud_lb_pool.this.id
  address       = huaweicloud_compute_instance.this.access_ip_v4
  protocol_port = var.backend_protocol_port
  subnet_id     = huaweicloud_vpc_subnet.this.ipv4_subnet_id
  weight        = var.backend_member_weight
}

resource "huaweicloud_lb_monitor" "this" {
  pool_id        = huaweicloud_lb_pool.this.id
  type           = var.monitor_type
  delay          = var.monitor_delay
  timeout        = var.monitor_timeout
  max_retries    = var.monitor_max_retries
  url_path       = var.monitor_type == "HTTP" ? var.monitor_url_path : null
  expected_codes = var.monitor_type == "HTTP" ? var.monitor_expected_codes : null

  depends_on = [huaweicloud_lb_member.this]
}
