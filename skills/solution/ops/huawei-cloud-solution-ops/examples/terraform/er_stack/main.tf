data "huaweicloud_er_availability_zones" "current" {}

locals {
  selected_availability_zone = try(data.huaweicloud_er_availability_zones.current.names[0], null)
}

resource "huaweicloud_vpc" "this" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}

resource "huaweicloud_vpc_subnet" "this" {
  vpc_id     = huaweicloud_vpc.this.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip
}

resource "huaweicloud_er_instance" "this" {
  availability_zones = [local.selected_availability_zone]
  name               = var.er_instance_name
  asn                = var.er_instance_asn

  lifecycle {
    precondition {
      condition     = local.selected_availability_zone != null
      error_message = "No ER availability zone was found in the current region."
    }
  }
}

resource "huaweicloud_er_vpc_attachment" "this" {
  instance_id = huaweicloud_er_instance.this.id
  vpc_id      = huaweicloud_vpc.this.id
  subnet_id   = huaweicloud_vpc_subnet.this.id

  name                   = var.er_vpc_attachment_name
  auto_create_vpc_routes = var.auto_create_vpc_routes
}
