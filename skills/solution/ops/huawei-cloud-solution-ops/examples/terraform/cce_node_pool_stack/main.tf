data "huaweicloud_availability_zones" "current" {}

data "huaweicloud_cce_flavor_specifications" "cluster" {
  cluster_type = var.cluster_type
}

data "huaweicloud_compute_flavors" "node" {
  performance_type  = var.node_performance_type
  cpu_core_count    = var.node_cpu_core_count
  memory_size       = var.node_memory_size
  availability_zone = data.huaweicloud_availability_zones.current.names[0]
}

locals {
  selected_cluster_flavor = var.cluster_flavor_id != null ? var.cluster_flavor_id : try([
    for spec in data.huaweicloud_cce_flavor_specifications.cluster.cluster_flavor_specs : spec.name
    if !spec.is_sold_out
  ][0], null)
  selected_node_flavor = try(data.huaweicloud_compute_flavors.node.flavors[0].id, null)
}

resource "huaweicloud_vpc" "this" {
  name = var.vpc_name
  cidr = var.vpc_cidr

  tags = var.tags
}

resource "huaweicloud_vpc_subnet" "this" {
  vpc_id            = huaweicloud_vpc.this.id
  name              = var.subnet_name
  cidr              = var.subnet_cidr
  gateway_ip        = var.subnet_gateway_ip
  availability_zone = data.huaweicloud_availability_zones.current.names[0]
  primary_dns       = var.subnet_primary_dns
  secondary_dns     = var.subnet_secondary_dns
}

resource "huaweicloud_vpc_eip" "this" {
  count = var.create_eip ? 1 : 0

  publicip {
    type = var.eip_type
  }

  bandwidth {
    name        = var.bandwidth_name
    size        = var.bandwidth_size
    share_type  = var.bandwidth_share_type
    charge_mode = var.bandwidth_charge_mode
  }
}

resource "huaweicloud_cce_cluster" "this" {
  name                   = var.cluster_name
  flavor_id              = local.selected_cluster_flavor
  cluster_version        = var.cluster_version
  cluster_type           = var.cluster_type
  container_network_type = var.container_network_type
  authentication_mode    = var.authentication_mode
  vpc_id                 = huaweicloud_vpc.this.id
  subnet_id              = huaweicloud_vpc_subnet.this.id
  eip                    = var.create_eip ? huaweicloud_vpc_eip.this[0].address : var.eip_address
  tags                   = var.tags

  lifecycle {
    precondition {
      condition     = local.selected_cluster_flavor != null
      error_message = "No sellable CCE cluster flavor was found for the requested cluster type. Set cluster_flavor_id explicitly or adjust the region and cluster_type."
    }

    precondition {
      condition     = var.create_eip || (var.eip_address != null && trimspace(var.eip_address) != "")
      error_message = "Either create_eip must be true or eip_address must be provided."
    }
  }
}

resource "huaweicloud_cce_node_pool" "this" {
  cluster_id               = huaweicloud_cce_cluster.this.id
  type                     = var.node_pool_type
  name                     = var.node_pool_name
  flavor_id                = local.selected_node_flavor
  availability_zone        = data.huaweicloud_availability_zones.current.names[0]
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
      condition     = local.selected_node_flavor != null
      error_message = "No CCE node flavor matched the requested AZ, performance type, CPU, and memory filters. Adjust the node flavor discovery inputs."
    }
  }
}
