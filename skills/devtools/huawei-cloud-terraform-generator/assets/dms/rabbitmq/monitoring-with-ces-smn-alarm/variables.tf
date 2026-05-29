# Variable definitions for authentication
variable "region_name" {
  description = "The region where resources will be created"
  type        = string
}

variable "access_key" {
  description = "The access key of the IAM user"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "The secret key of the IAM user"
  type        = string
  sensitive   = true
}

# Variable definitions for network resources
variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
  default     = "192.168.0.0/16"
}

variable "subnet_name" {
  description = "The name of the subnet"
  type        = string
}

variable "subnet_cidr" {
  description = "The CIDR block of the subnet"
  type        = string
  default     = ""
  nullable    = false
}

variable "subnet_gateway_ip" {
  description = "The gateway IP of the subnet"
  type        = string
  default     = ""
  nullable    = false
}

variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

variable "security_group_rule_configurations" {
  description = "The list of security group rule configurations."

  type = list(object({
    direction        = string
    ethertype        = string
    protocol         = string
    port_range_min   = number
    port_range_max   = number
    remote_ip_prefix = string
    description      = string
  }))

  default = [
    {
      direction        = "ingress"
      ethertype        = "IPv4"
      protocol         = "tcp"
      port_range_min   = 5672
      port_range_max   = 5672
      remote_ip_prefix = "192.168.0.0/16"
      description      = "Allow access to RabbitMQ AMQP port"
    },
    {
      direction        = "ingress"
      ethertype        = "IPv4"
      protocol         = "tcp"
      port_range_min   = 15672
      port_range_max   = 15672
      remote_ip_prefix = "192.168.0.0/16"
      description      = "Allow access to RabbitMQ management port"
    }
  ]
}

# Variable definitions for DMS RabbitMQ instance
variable "instance_flavor_type" {
  description = "The flavor type of the RabbitMQ instance"
  type        = string
  default     = "cluster"
}

variable "instance_storage_spec_code" {
  description = "The storage specification code of the RabbitMQ instance"
  type        = string
  default     = "dms.physical.storage.ultra.v2"
}

variable "availability_zone_number" {
  description = "The number of availability zones to which the RabbitMQ instance belongs"
  type        = number
  default     = 1
}

variable "instance_name" {
  description = "The name of the RabbitMQ instance"
  type        = string
}

variable "instance_engine_version" {
  description = "The engine version of the RabbitMQ instance"
  type        = string
  default     = "3.8.35"
}

variable "instance_broker_num" {
  description = "The number of brokers of the RabbitMQ instance"
  type        = number
  default     = 3
}

variable "instance_storage_space" {
  description = "The storage space of the RabbitMQ instance (in GB)"
  type        = number
  default     = 600
}

variable "instance_ssl_enable" {
  description = "Whether to enable SSL for the RabbitMQ instance"
  type        = bool
  default     = false
}

variable "instance_access_user_name" {
  description = "The access user of the RabbitMQ instance"
  type        = string
}

variable "instance_password" {
  description = "The access password of the RabbitMQ instance"
  type        = string
  sensitive   = true
}

variable "instance_description" {
  description = "The description of the RabbitMQ instance"
  type        = string
  default     = ""
}

variable "enterprise_project_id" {
  description = "The enterprise project ID"
  type        = string
  default     = null
}

variable "instance_tags" {
  description = "The key/value pairs to associate with the RabbitMQ instance"
  type        = map(string)
  default     = {}
}

variable "charging_mode" {
  description = "The charging mode of the RabbitMQ instance"
  type        = string
  default     = "postPaid"
}

variable "period_unit" {
  description = "The period unit of the RabbitMQ instance"
  type        = string
  default     = null
}

variable "period" {
  description = "The period of the RabbitMQ instance"
  type        = number
  default     = null
}

variable "auto_renew" {
  description = "The auto renew of the RabbitMQ instance"
  type        = string
  default     = "false"
}

# Variable definitions for SMN notification
variable "smn_topic_name" {
  description = "The name of the SMN topic used to send alarm notifications"
  type        = string
}

variable "smn_topic_display_name" {
  description = "The display name of the SMN topic"
  type        = string
  default     = ""
  nullable    = false
}

variable "sms_subscription_endpoint" {
  description = "The phone number for SMS notification, format: +[country code][phone number], e.g. +8613600000000"
  type        = string
}

variable "sms_subscription_remark" {
  description = "The remark of the SMS subscription"
  type        = string
  default     = "RabbitMQ alarm notification"
}

# Variable definitions for CES alarm rules
variable "alarm_rule_name" {
  description = "The name of the CES alarm rule"
  type        = string
}

variable "alarm_rule_description" {
  description = "The description of the CES alarm rule"
  type        = string
  default     = "The alarm rule for RabbitMQ monitoring"
}

variable "alarm_action_enabled" {
  description = "Whether to enable the action to be triggered by an alarm"
  type        = bool
  default     = true
}

variable "alarm_enabled" {
  description = "Whether to enable the alarm"
  type        = bool
  default     = true
}

variable "alarm_rule_conditions" {
  description = "The list of alarm rule conditions for RabbitMQ monitoring"

  type = list(object({
    metric_name         = string
    period              = number
    filter              = string
    comparison_operator = string
    value               = number
    count               = number
    unit                = optional(string)
    suppress_duration   = optional(number, 300)
    alarm_level         = optional(number, 2)
  }))

  nullable = false
}

variable "alarm_rule_notification_begin_time" {
  description = "The alarm notification start time, e.g. 00:00"
  type        = string
  default     = null
}

variable "alarm_rule_notification_end_time" {
  description = "The alarm notification stop time, e.g. 23:59"
  type        = string
  default     = null
}

# Variable definitions for CES dashboard
variable "dashboard_name" {
  description = "The name of the CES monitoring dashboard for RabbitMQ"
  type        = string
  default     = ""
  nullable    = false
}

variable "dashboard_widget_configurations" {
  description = "The list of dashboard widget configurations for RabbitMQ monitoring"

  type = list(object({
    title       = string
    metric_name = string
    left        = number
    top         = number
    width       = optional(number, 6)
    height      = optional(number, 3)
  }))

  default = [
    {
      title       = "RabbitMQ Connections"
      metric_name = "connections"
      left        = 0
      top         = 0
    },
    {
      title       = "RabbitMQ Channels"
      metric_name = "channels"
      left        = 6
      top         = 0
    },
    {
      title       = "RabbitMQ Queues"
      metric_name = "queues"
      left        = 0
      top         = 3
    },
    {
      title       = "RabbitMQ File Descriptors Used"
      metric_name = "fd_used"
      left        = 6
      top         = 3
    },
  ]
}
