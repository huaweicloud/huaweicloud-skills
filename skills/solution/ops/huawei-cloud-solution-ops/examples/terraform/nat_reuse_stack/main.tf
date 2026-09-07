resource "huaweicloud_nat_snat_rule" "this" {
  count = var.enable_snat ? 1 : 0

  nat_gateway_id = var.nat_gateway_id
  floating_ip_id = var.snat_floating_ip_id
  source_type    = var.snat_source_type
  subnet_id      = var.snat_source_type == 0 ? var.snat_subnet_id : null
  cidr           = var.snat_source_type == 1 ? var.snat_cidr : null
  description    = var.snat_description

  lifecycle {
    precondition {
      condition     = var.snat_source_type == 0 ? var.snat_subnet_id != "" : var.snat_cidr != ""
      error_message = "Set snat_subnet_id when snat_source_type is 0, or snat_cidr when snat_source_type is 1."
    }
  }
}

resource "huaweicloud_nat_dnat_rule" "this" {
  count = var.enable_dnat ? 1 : 0

  nat_gateway_id        = var.nat_gateway_id
  floating_ip_id        = var.dnat_floating_ip_id != "" ? var.dnat_floating_ip_id : var.snat_floating_ip_id
  port_id               = var.dnat_port_id
  protocol              = var.dnat_protocol
  internal_service_port = var.dnat_internal_service_port
  external_service_port = var.dnat_external_service_port

  lifecycle {
    precondition {
      condition     = var.dnat_port_id != ""
      error_message = "dnat_port_id is required when enable_dnat is true."
    }
  }
}
