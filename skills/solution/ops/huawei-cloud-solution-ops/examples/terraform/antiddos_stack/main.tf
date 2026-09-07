resource "huaweicloud_vpc_eip" "this" {
  publicip {
    type = var.publicip_type
  }

  bandwidth {
    share_type  = var.bandwidth_share_type
    name        = var.bandwidth_name
    size        = var.bandwidth_size
    charge_mode = var.bandwidth_charge_mode
  }

  lifecycle {
    precondition {
      condition     = var.bandwidth_share_type != "PER" || (var.bandwidth_name != null && var.bandwidth_size != null)
      error_message = "bandwidth_name and bandwidth_size must be provided when bandwidth_share_type is PER."
    }
  }
}

resource "huaweicloud_smn_topic" "this" {
  name = var.topic_name
}

resource "huaweicloud_smn_subscription" "this" {
  topic_urn = huaweicloud_smn_topic.this.id
  endpoint  = var.subscription_endpoint
  protocol  = var.subscription_protocol
}

resource "huaweicloud_antiddos_basic" "this" {
  traffic_threshold = var.traffic_threshold
  eip_id            = huaweicloud_vpc_eip.this.id
  topic_urn         = huaweicloud_smn_topic.this.id
}
