data "huaweicloud_availability_zones" "current" {}

data "huaweicloud_compute_flavors" "ecs" {
  availability_zone = data.huaweicloud_availability_zones.current.names[0]
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}

data "huaweicloud_images_image" "ecs" {
  name        = var.image_name
  visibility  = var.image_visibility
  most_recent = true
}

locals {
  selected_flavor_id = try(data.huaweicloud_compute_flavors.ecs.ids[0], null)
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

resource "huaweicloud_networking_secgroup" "this" {
  name = var.security_group_name
}

resource "huaweicloud_networking_secgroup_rule" "service_ingress" {
  for_each = {
    for mapping in var.endpoint_service_port_mapping : mapping.service_port => mapping
  }

  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = each.value.terminal_port
  port_range_max    = each.value.terminal_port
  remote_ip_prefix  = var.vpc_cidr
  security_group_id = huaweicloud_networking_secgroup.this.id
}

resource "huaweicloud_compute_instance" "this" {
  name               = var.instance_name
  image_id           = data.huaweicloud_images_image.ecs.id
  flavor_id          = local.selected_flavor_id
  security_group_ids = [huaweicloud_networking_secgroup.this.id]
  availability_zone  = data.huaweicloud_availability_zones.current.names[0]
  key_pair           = var.key_pair_name
  system_disk_type   = var.system_disk_type
  system_disk_size   = var.system_disk_size

  network {
    uuid = huaweicloud_vpc_subnet.this.id
  }

  lifecycle {
    precondition {
      condition     = local.selected_flavor_id != null
      error_message = "No ECS flavor matched the requested AZ, performance type, CPU, and memory filters. Adjust the flavor discovery inputs or confirm the region and AZ."
    }
  }
}

resource "huaweicloud_vpcep_service" "this" {
  name        = var.endpoint_service_name
  server_type = var.endpoint_service_type
  vpc_id      = huaweicloud_vpc.this.id
  port_id     = huaweicloud_compute_instance.this.network[0].port

  dynamic "port_mapping" {
    for_each = var.endpoint_service_port_mapping

    content {
      service_port  = port_mapping.value.service_port
      terminal_port = port_mapping.value.terminal_port
    }
  }
}

resource "huaweicloud_vpcep_endpoint" "this" {
  service_id = huaweicloud_vpcep_service.this.id
  vpc_id     = huaweicloud_vpc.this.id
  network_id = huaweicloud_vpc_subnet.this.id

  tags = merge(var.tags, {
    Name = var.endpoint_name
  })
}
