# Network
vpc_name            = "rabbitmq-monitor-vpc"
subnet_name         = "rabbitmq-monitor-subnet"
security_group_name = "rabbitmq-monitor-sg"

# DMS RabbitMQ Instance
instance_name = "rabbitmq-monitored"
# Replace with your RabbitMQ instance access information
instance_access_user_name = "rabbitmq_admin"
instance_password         = "YourPassword@123"

# SMN Notification
smn_topic_name = "rabbitmq-alarm-topic"
# Replace with your phone number
# Format: +[country code][phone number], e.g. +8613600000000
sms_subscription_endpoint = "+8613600000000"

# CES Alarm Rule
alarm_rule_name = "rabbitmq-instance-alarm"

# Alarm conditions for RabbitMQ key metrics.
# Each item defines a monitoring rule for a specific metric.
alarm_rule_conditions = [
  {
    # Alert when the number of connections exceeds 1000 (average over 5 minutes, triggered after 3 consecutive breaches)
    metric_name         = "connections"
    period              = 300
    filter              = "average"
    comparison_operator = ">"
    value               = 1000
    count               = 3
    unit                = "count"
    suppress_duration   = 3600
    alarm_level         = 2
  },
  {
    # Alert when the number of channels exceeds 5000 (average over 5 minutes, triggered after 3 consecutive breaches)
    metric_name         = "channels"
    period              = 300
    filter              = "average"
    comparison_operator = ">"
    value               = 5000
    count               = 3
    unit                = "count"
    suppress_duration   = 3600
    alarm_level         = 2
  },
  {
    # Please replace with your own real metric data according to your own business
    # This rule is used for test phone notification
    # Alert when the number of queues is 0 (average over 5 minutes, triggered after 3 consecutive breaches)
    metric_name         = "queues"
    period              = 300
    filter              = "average"
    comparison_operator = "="
    value               = 0
    count               = 3
    unit                = "count"
    suppress_duration   = 3600
    alarm_level         = 3
  },
]
