data "huaweicloud_availability_zones" "test" {}

resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}

resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr != "" ? var.subnet_cidr : cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0)
  gateway_ip = var.subnet_gateway_ip != "" ? var.subnet_gateway_ip : cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1)
}

resource "huaweicloud_networking_secgroup" "test" {
  name = var.security_group_name
}

resource "huaweicloud_networking_secgroup_rule" "test" {
  count = length(var.security_group_rule_configurations)

  security_group_id = huaweicloud_networking_secgroup.test.id
  direction         = lookup(var.security_group_rule_configurations[count.index], "direction", null)
  ethertype         = lookup(var.security_group_rule_configurations[count.index], "ethertype", null)
  protocol          = lookup(var.security_group_rule_configurations[count.index], "protocol", null)
  port_range_min    = lookup(var.security_group_rule_configurations[count.index], "port_range_min", null)
  port_range_max    = lookup(var.security_group_rule_configurations[count.index], "port_range_max", null)
  remote_ip_prefix  = lookup(var.security_group_rule_configurations[count.index], "remote_ip_prefix", null)
  description       = lookup(var.security_group_rule_configurations[count.index], "description", null)
}

data "huaweicloud_dms_rabbitmq_flavors" "test" {
  type               = var.instance_flavor_type
  storage_spec_code  = var.instance_storage_spec_code
  availability_zones = try(slice(data.huaweicloud_availability_zones.test.names, 0, var.availability_zone_number), null)
}

resource "huaweicloud_dms_rabbitmq_instance" "test" {
  name                  = var.instance_name
  engine_version        = var.instance_engine_version
  flavor_id             = try(data.huaweicloud_dms_rabbitmq_flavors.test.flavors[0].id, null)
  vpc_id                = huaweicloud_vpc.test.id
  network_id            = huaweicloud_vpc_subnet.test.id
  security_group_id     = huaweicloud_networking_secgroup.test.id
  availability_zones    = try(slice(data.huaweicloud_availability_zones.test.names, 0, var.availability_zone_number), null)
  broker_num            = var.instance_broker_num
  storage_space         = var.instance_storage_space
  storage_spec_code     = var.instance_storage_spec_code
  ssl_enable            = var.instance_ssl_enable
  access_user           = var.instance_access_user_name
  password              = var.instance_password
  description           = var.instance_description
  enterprise_project_id = var.enterprise_project_id
  tags                  = var.instance_tags
  charging_mode         = var.charging_mode
  period_unit           = var.period_unit
  period                = var.period
  auto_renew            = var.auto_renew

  lifecycle {
    ignore_changes = [
      flavor_id,
      availability_zones,
    ]
  }
}

resource "huaweicloud_smn_topic" "test" {
  name                  = var.smn_topic_name
  display_name          = var.smn_topic_display_name != "" ? var.smn_topic_display_name : var.smn_topic_name
  enterprise_project_id = var.enterprise_project_id
}

resource "huaweicloud_smn_subscription" "test" {
  topic_urn = huaweicloud_smn_topic.test.id
  protocol  = "sms"
  endpoint  = var.sms_subscription_endpoint
  remark    = var.sms_subscription_remark
}

resource "huaweicloud_ces_alarmrule" "test" {
  alarm_name            = var.alarm_rule_name
  alarm_description     = var.alarm_rule_description
  alarm_action_enabled  = var.alarm_action_enabled
  alarm_enabled         = var.alarm_enabled
  alarm_type            = "MULTI_INSTANCE"
  enterprise_project_id = var.enterprise_project_id

  metric {
    namespace = "SYS.DMS"
  }

  resources {
    dimensions {
      name  = "rabbitmq_instance_id"
      value = huaweicloud_dms_rabbitmq_instance.test.id
    }
  }

  dynamic "condition" {
    for_each = var.alarm_rule_conditions

    content {
      metric_name         = condition.value.metric_name
      period              = condition.value.period
      filter              = condition.value.filter
      comparison_operator = condition.value.comparison_operator
      value               = condition.value.value
      count               = condition.value.count
      unit                = condition.value.unit
      suppress_duration   = condition.value.suppress_duration
      alarm_level         = condition.value.alarm_level
    }
  }

  alarm_actions {
    type = "notification"

    notification_list = [
      huaweicloud_smn_topic.test.topic_urn
    ]
  }

  ok_actions {
    type = "notification"

    notification_list = [
      huaweicloud_smn_topic.test.topic_urn
    ]
  }

  notification_begin_time = var.alarm_rule_notification_begin_time
  notification_end_time   = var.alarm_rule_notification_end_time

  depends_on = [huaweicloud_dms_rabbitmq_instance.test]
}

locals {
  dashboard_name = var.dashboard_name != "" ? var.dashboard_name : "RabbitMQ-${var.instance_name}-dashboard"
}

resource "huaweicloud_ces_dashboard" "test" {
  name                  = local.dashboard_name
  row_widget_num        = 2
  enterprise_project_id = var.enterprise_project_id

  depends_on = [
    huaweicloud_dms_rabbitmq_instance.test,
    huaweicloud_ces_alarmrule.test
  ]
}

resource "huaweicloud_ces_dashboard_widget" "test" {
  count = length(var.dashboard_widget_configurations)

  dashboard_id        = huaweicloud_ces_dashboard.test.id
  title               = var.dashboard_widget_configurations[count.index].title
  view                = "line"
  metric_display_mode = "single"

  metrics {
    namespace   = "SYS.DMS"
    metric_name = var.dashboard_widget_configurations[count.index].metric_name

    dimensions {
      name        = "rabbitmq_instance_id"
      filter_type = "specific_instances"
      values      = [huaweicloud_dms_rabbitmq_instance.test.id]
    }
  }

  location {
    left   = var.dashboard_widget_configurations[count.index].left
    top    = var.dashboard_widget_configurations[count.index].top
    width  = var.dashboard_widget_configurations[count.index].width
    height = var.dashboard_widget_configurations[count.index].height
  }
}
