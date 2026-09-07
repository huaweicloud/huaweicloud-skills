resource "huaweicloud_cdn_domain" "this" {
  name         = var.domain_name
  type         = var.domain_type
  service_area = var.service_area

  sources {
    origin      = var.origin_server
    origin_type = var.origin_type
    active      = 1
    http_port   = var.http_port
    https_port  = var.https_port
  }

  configs {
    origin_protocol = var.origin_protocol
  }

  dynamic "cache_settings" {
    for_each = length(var.cache_rules) > 0 ? [var.cache_rules] : []

    content {
      dynamic "rules" {
        for_each = cache_settings.value

        content {
          rule_type           = rules.value.rule_type
          ttl                 = rules.value.ttl
          ttl_type            = rules.value.ttl_type
          priority            = rules.value.priority
          content             = rules.value.content
          url_parameter_type  = try(rules.value.url_parameter_type, null)
          url_parameter_value = try(rules.value.url_parameter_value, null)
        }
      }
    }
  }
}
