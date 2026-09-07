resource "huaweicloud_lb_listener" "this" {
  loadbalancer_id = var.loadbalancer_id
  name            = var.listener_name
  protocol        = var.listener_protocol
  protocol_port   = var.listener_port
}

resource "huaweicloud_lb_pool" "this" {
  listener_id = huaweicloud_lb_listener.this.id
  name        = var.pool_name
  protocol    = var.pool_protocol
  lb_method   = var.pool_method
}

resource "huaweicloud_lb_member" "this" {
  pool_id       = huaweicloud_lb_pool.this.id
  address       = var.backend_address
  protocol_port = var.backend_protocol_port
  subnet_id     = var.backend_subnet_id
  weight        = var.backend_member_weight
}

resource "huaweicloud_lb_monitor" "this" {
  pool_id        = huaweicloud_lb_pool.this.id
  type           = var.monitor_type
  delay          = var.monitor_delay
  timeout        = var.monitor_timeout
  max_retries    = var.monitor_max_retries
  url_path       = var.monitor_type == "HTTP" ? var.monitor_url_path : null
  expected_codes = var.monitor_type == "HTTP" ? var.monitor_expected_codes : null

  depends_on = [huaweicloud_lb_member.this]
}
