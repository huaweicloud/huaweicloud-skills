data "huaweicloud_availability_zones" "current" {}

data "huaweicloud_compute_flavors" "node" {
  count = var.node_flavor_id == "" ? 1 : 0

  availability_zone = var.availability_zone != "" ? var.availability_zone : data.huaweicloud_availability_zones.current.names[0]
  performance_type  = var.node_performance_type
  cpu_core_count    = var.node_cpu_core_count
  memory_size       = var.node_memory_size
}

locals {
  selected_node_flavor       = var.node_flavor_id != "" ? var.node_flavor_id : try(data.huaweicloud_compute_flavors.node[0].flavors[0].id, null)
  selected_availability_zone = var.availability_zone != "" ? var.availability_zone : data.huaweicloud_availability_zones.current.names[0]
}

resource "huaweicloud_cce_partition" "this" {
  cluster_id           = var.cluster_id
  name                 = var.partition_name
  category             = var.partition_category
  public_border_group  = var.partition_public_border_group
  partition_subnet_id  = var.partition_subnet_id
  container_subnet_ids = var.container_subnet_ids
}

resource "huaweicloud_cce_node_pool" "this" {
  cluster_id         = var.cluster_id
  name               = var.node_pool_name
  os                 = var.node_pool_os_type
  flavor_id          = local.selected_node_flavor
  initial_node_count = var.node_pool_initial_node_count
  availability_zone  = local.selected_availability_zone
  key_pair           = var.node_key_pair_name
  type               = "vm"
  partition          = huaweicloud_cce_partition.this.id

  root_volume {
    volumetype = var.root_volume_type
    size       = var.root_volume_size
  }

  data_volumes {
    volumetype = var.data_volume_type
    size       = var.data_volume_size
  }

  lifecycle {
    precondition {
      condition     = local.selected_node_flavor != null
      error_message = "No node flavor matched the requested filters. Set node_flavor_id explicitly or adjust the filters."
    }
  }
}
