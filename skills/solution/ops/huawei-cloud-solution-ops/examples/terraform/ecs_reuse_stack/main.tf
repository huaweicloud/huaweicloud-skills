data "huaweicloud_vpc_subnet" "selected" {
  id = var.subnet_id
}

data "huaweicloud_networking_secgroup" "selected" {
  secgroup_id = var.security_group_id
}

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

resource "huaweicloud_compute_instance" "this" {
  name               = var.instance_name
  image_id           = data.huaweicloud_images_image.ecs.id
  flavor_id          = local.selected_flavor_id
  security_group_ids = [data.huaweicloud_networking_secgroup.selected.id]
  availability_zone  = data.huaweicloud_availability_zones.current.names[0]
  key_pair           = var.key_pair_name
  system_disk_type   = var.system_disk_type
  system_disk_size   = var.system_disk_size

  network {
    uuid = data.huaweicloud_vpc_subnet.selected.id
  }

  lifecycle {
    precondition {
      condition     = local.selected_flavor_id != null
      error_message = "No ECS flavor matched the requested AZ, performance type, CPU, and memory filters. Adjust the flavor discovery inputs or confirm the region and AZ."
    }
  }
}
