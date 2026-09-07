data "huaweicloud_availability_zones" "current" {}

locals {
  selected_availability_zone = var.availability_zone != null ? var.availability_zone : try(data.huaweicloud_availability_zones.current.names[0], null)
}

resource "huaweicloud_evs_volume" "this" {
  availability_zone = local.selected_availability_zone
  name              = var.volume_name
  volume_type       = var.volume_type
  size              = var.volume_size
  description       = var.volume_description
  multiattach       = var.volume_multiattach
  iops              = var.volume_iops
  throughput        = var.volume_throughput
  device_type       = var.device_type
  tags              = var.tags

  lifecycle {
    precondition {
      condition     = local.selected_availability_zone != null
      error_message = "No availability zone could be selected for the EVS volume. Set availability_zone explicitly or confirm the region."
    }
  }
}
