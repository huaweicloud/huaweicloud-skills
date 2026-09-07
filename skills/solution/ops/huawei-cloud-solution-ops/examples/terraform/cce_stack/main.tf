data "huaweicloud_availability_zones" "current" {}

data "huaweicloud_cce_flavor_specifications" "cluster" {
  cluster_type = var.cluster_type
}

locals {
  selected_cluster_flavor = var.cluster_flavor_id != null ? var.cluster_flavor_id : try([
    for spec in data.huaweicloud_cce_flavor_specifications.cluster.cluster_flavor_specs : spec.name
    if !spec.is_sold_out
  ][0], null)
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
  description            = var.cluster_description
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
