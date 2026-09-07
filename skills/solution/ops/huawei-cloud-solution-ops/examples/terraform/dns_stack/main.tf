resource "huaweicloud_dns_zone" "this" {
  name        = var.zone_name
  email       = var.zone_email
  zone_type   = var.zone_type
  description = var.zone_description
  ttl         = var.zone_ttl
  status      = var.zone_status
  dnssec      = var.zone_dnssec

  dynamic "router" {
    for_each = var.routers

    content {
      router_id     = router.value.router_id
      router_region = router.value.router_region
    }
  }
}
