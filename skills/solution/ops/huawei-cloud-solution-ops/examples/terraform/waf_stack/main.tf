resource "huaweicloud_waf_cloud_instance" "this" {
  resource_spec_code = var.resource_spec_code
  charging_mode      = var.charging_mode
  period_unit        = var.period_unit
  period             = var.period
  auto_renew         = var.auto_renew
}

resource "huaweicloud_waf_domain" "this" {
  domain           = var.domain_name
  certificate_id   = var.certificate_id
  certificate_name = var.certificate_name
  proxy            = var.proxy_enabled

  dynamic "server" {
    for_each = var.origin_servers

    content {
      client_protocol = server.value.client_protocol
      server_protocol = server.value.server_protocol
      address         = server.value.address
      port            = server.value.port
      type            = server.value.type
      weight          = server.value.weight
    }
  }

  depends_on = [
    huaweicloud_waf_cloud_instance.this,
  ]
}
