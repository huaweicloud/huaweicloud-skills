data "huaweicloud_availability_zones" "current" {}

resource "huaweicloud_vpc" "this" {
  name = var.vpc_name
  cidr = var.vpc_cidr

  tags = var.tags
}

resource "huaweicloud_vpc_subnet" "cluster" {
  vpc_id            = huaweicloud_vpc.this.id
  name              = var.cluster_subnet_name
  cidr              = var.cluster_subnet_cidr
  gateway_ip        = var.cluster_subnet_gateway_ip
  availability_zone = data.huaweicloud_availability_zones.current.names[0]
}

resource "huaweicloud_vpc_subnet" "eni" {
  vpc_id            = huaweicloud_vpc.this.id
  name              = var.eni_subnet_name
  cidr              = var.eni_subnet_cidr
  gateway_ip        = var.eni_subnet_gateway_ip
  availability_zone = data.huaweicloud_availability_zones.current.names[0]
}

resource "huaweicloud_vpc_eip" "cluster" {
  count = var.create_eip ? 1 : 0

  publicip {
    type = "5_bgp"
  }

  bandwidth {
    name        = var.bandwidth_name
    size        = var.bandwidth_size
    share_type  = "PER"
    charge_mode = "traffic"
  }

  tags = var.tags
}

resource "huaweicloud_cce_cluster" "this" {
  name                         = var.cluster_name
  flavor_id                    = var.cluster_flavor_id
  cluster_version              = var.cluster_version
  cluster_type                 = "VirtualMachine"
  container_network_type       = "eni"
  vpc_id                       = huaweicloud_vpc.this.id
  subnet_id                    = huaweicloud_vpc_subnet.cluster.id
  eni_subnet_id                = huaweicloud_vpc_subnet.eni.ipv4_subnet_id
  eip                          = var.create_eip ? huaweicloud_vpc_eip.cluster[0].address : var.eip_address
  enable_distribute_management = var.enable_distribute_management
  description                  = var.cluster_description
  tags                         = var.tags

  lifecycle {
    precondition {
      condition     = var.create_eip || var.eip_address != ""
      error_message = "Either create_eip must be true or eip_address must be provided."
    }
  }
}
