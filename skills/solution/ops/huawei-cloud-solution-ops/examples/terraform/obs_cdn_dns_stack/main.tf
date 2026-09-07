locals {
  obs_website_origin = var.origin_server != "" ? var.origin_server : format("%s.obs-website.%s.myhuaweicloud.com", var.bucket_name, var.region_name)
}

resource "huaweicloud_obs_bucket" "site" {
  bucket        = var.bucket_name
  storage_class = var.bucket_storage_class
  acl           = "public-read"
  force_destroy = var.bucket_force_destroy

  website {
    index_document = var.index_document
    error_document = var.error_document
  }

  tags = var.tags
}

resource "huaweicloud_obs_bucket_policy" "public_read" {
  bucket = huaweicloud_obs_bucket.site.id
  policy = jsonencode({
    Statement = [
      {
        Sid       = "PublicReadForStaticWebsite"
        Effect    = "Allow"
        Principal = { ID = "*" }
        Action    = ["GetObject"]
        Resource  = "${huaweicloud_obs_bucket.site.id}/*"
      }
    ]
  })
}

resource "huaweicloud_obs_bucket_object" "index" {
  bucket       = huaweicloud_obs_bucket.site.id
  key          = var.index_document
  content_type = "text/html"
  content      = var.index_html
}

resource "huaweicloud_obs_bucket_object" "error" {
  bucket       = huaweicloud_obs_bucket.site.id
  key          = var.error_document
  content_type = "text/html"
  content      = var.error_html
}

resource "huaweicloud_cdn_domain" "site" {
  name         = var.cdn_domain_name
  type         = "web"
  service_area = var.service_area

  sources {
    origin      = local.obs_website_origin
    origin_type = "domain"
    active      = 1
    http_port   = 80
    https_port  = 443
  }

  configs {
    origin_protocol = "http"
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

resource "huaweicloud_dns_zone" "site" {
  count = var.create_dns_zone ? 1 : 0

  name        = var.zone_name
  email       = var.zone_email
  zone_type   = "public"
  description = var.zone_description
  ttl         = var.zone_ttl
  status      = "ENABLE"
}

resource "huaweicloud_dns_recordset" "cdn_cname" {
  count = var.create_dns_record ? 1 : 0

  zone_id = var.create_dns_zone ? huaweicloud_dns_zone.site[0].id : var.zone_id
  name    = var.cdn_domain_name
  type    = "CNAME"
  ttl     = var.record_ttl
  records = [var.cdn_cname_target]

  lifecycle {
    precondition {
      condition     = var.cdn_cname_target != ""
      error_message = "cdn_cname_target must be filled after confirming the CDN CNAME target."
    }
  }
}
