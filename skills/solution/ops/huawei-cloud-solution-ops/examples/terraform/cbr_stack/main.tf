data "huaweicloud_availability_zones" "current" {}

locals {
  selected_availability_zone = coalesce(var.availability_zone, try(data.huaweicloud_availability_zones.current.names[0], null))
}

data "huaweicloud_compute_flavors" "ecs" {
  availability_zone = local.selected_availability_zone
  performance_type  = var.flavor_performance_type
  cpu_core_count    = var.flavor_cpu_core_count
  memory_size       = var.flavor_memory_size
}

locals {
  selected_flavor_id = try(data.huaweicloud_compute_flavors.ecs.ids[0], null)
}

data "huaweicloud_images_image" "ecs" {
  name        = var.image_name
  visibility  = "public"
  most_recent = true
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
  availability_zone = local.selected_availability_zone
}

resource "huaweicloud_networking_secgroup" "this" {
  name                 = var.security_group_name
  delete_default_rules = true
}

resource "huaweicloud_compute_instance" "this" {
  name               = var.instance_name
  availability_zone  = local.selected_availability_zone
  flavor_id          = local.selected_flavor_id
  image_id           = data.huaweicloud_images_image.ecs.id
  security_group_ids = [huaweicloud_networking_secgroup.this.id]
  key_pair           = var.key_pair_name
  system_disk_type   = var.system_disk_type
  system_disk_size   = var.system_disk_size

  network {
    uuid = huaweicloud_vpc_subnet.this.id
  }

  lifecycle {
    precondition {
      condition     = local.selected_flavor_id != null
      error_message = "No ECS flavor matched the requested filters."
    }
  }
}

resource "huaweicloud_cbr_vault" "this" {
  name                  = var.vault_name
  type                  = "server"
  protection_type       = "backup"
  consistent_level      = "crash_consistent"
  size                  = var.vault_size
  enterprise_project_id = var.enterprise_project_id

  resources {
    server_id = huaweicloud_compute_instance.this.id
  }
}
