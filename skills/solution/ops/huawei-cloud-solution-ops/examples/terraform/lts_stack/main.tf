resource "huaweicloud_lts_group" "this" {
  group_name  = var.group_name
  ttl_in_days = var.group_log_expiration_days
}

resource "huaweicloud_lts_stream" "this" {
  group_id    = huaweicloud_lts_group.this.id
  stream_name = var.stream_name
  ttl_in_days = var.stream_log_expiration_days
}
