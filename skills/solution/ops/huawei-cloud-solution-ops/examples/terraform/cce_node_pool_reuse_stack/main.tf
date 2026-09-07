data "huaweicloud_cce_clusters" "selected" {
  count = var.cluster_id == "" ? 1 : 0

  name = var.cluster_name
}

data "huaweicloud_availability_zones" "current" {}

data "huaweicloud_compute_flavors" "node" {
  count = var.node_flavor_id == "" ? 1 : 0

  availability_zone = var.availability_zone != "" ? var.availability_zone : data.huaweicloud_availability_zones.current.names[0]
  performance_type  = var.node_performance_type
  cpu_core_count    = var.node_cpu_core_count
  memory_size       = var.node_memory_size
}

locals {
  selected_cluster_id = var.cluster_id != "" ? var.cluster_id : try(data.huaweicloud_cce_clusters.selected[0].clusters[0].id, null)
  selected_node_flavor = var.node_flavor_id != "" ? var.node_flavor_id : try(
    data.huaweicloud_compute_flavors.node[0].flavors[0].id,
    null,
  )
  selected_availability_zone = var.availability_zone != "" ? var.availability_zone : data.huaweicloud_availability_zones.current.names[0]
}

resource "huaweicloud_cce_node_pool" "this" {
  cluster_id               = local.selected_cluster_id
  type                     = var.node_pool_type
  name                     = var.node_pool_name
  flavor_id                = local.selected_node_flavor
  availability_zone        = local.selected_availability_zone
  os                       = var.node_pool_os_type
  key_pair                 = var.node_key_pair_name
  initial_node_count       = var.node_pool_initial_node_count
  min_node_count           = var.node_pool_min_node_count
  max_node_count           = var.node_pool_max_node_count
  scale_down_cooldown_time = var.node_pool_scale_down_cooldown_time
  priority                 = var.node_pool_priority
  scall_enable             = true
  tags                     = var.tags

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
      condition     = local.selected_cluster_id != null
      error_message = "No CCE cluster was selected. Set cluster_id or a cluster_name that resolves to one cluster."
    }

    precondition {
      condition     = local.selected_node_flavor != null
      error_message = "No CCE node flavor matched the requested filters. Set node_flavor_id explicitly or adjust the filters."
    }
  }
}
