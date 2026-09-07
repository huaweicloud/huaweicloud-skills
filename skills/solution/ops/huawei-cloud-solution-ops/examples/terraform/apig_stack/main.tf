data "huaweicloud_availability_zones" "current" {}

locals {
  selected_availability_zones = slice(
    data.huaweicloud_availability_zones.current.names,
    0,
    min(length(data.huaweicloud_availability_zones.current.names), var.availability_zones_count)
  )
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
  availability_zone = local.selected_availability_zones[0]
}

resource "huaweicloud_networking_secgroup" "this" {
  name                 = var.security_group_name
  delete_default_rules = true
}

resource "huaweicloud_apig_instance" "this" {
  name               = var.instance_name
  edition            = var.instance_edition
  vpc_id             = huaweicloud_vpc.this.id
  subnet_id          = huaweicloud_vpc_subnet.this.id
  security_group_id  = huaweicloud_networking_secgroup.this.id
  availability_zones = local.selected_availability_zones

  lifecycle {
    precondition {
      condition     = length(local.selected_availability_zones) > 0
      error_message = "No availability zone could be selected for the APIG instance. Confirm the region or reduce availability_zones_count."
    }
  }
}

resource "huaweicloud_apig_plugin" "this" {
  instance_id = huaweicloud_apig_instance.this.id
  name        = var.plugin_name
  type        = "proxy_cache"
  description = var.plugin_description

  content = jsonencode({
    cache_key = {
      system_params = []
      parameters    = ["custom_param"]
      headers       = []
    }
    cache_http_status_and_ttl = [
      {
        http_status = [202, 203]
        ttl         = 5
      }
    ]
    client_cache_control = {
      mode  = "off"
      datas = []
    }
    cacheable_headers = ["X-Custom-Header"]
  })
}
