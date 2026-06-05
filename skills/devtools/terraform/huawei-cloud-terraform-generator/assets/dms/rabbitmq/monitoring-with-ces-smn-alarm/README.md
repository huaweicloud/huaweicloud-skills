# Monitoring DMS RabbitMQ with CES and SMN SMS Alerts Best Practice

This example provides best practice code for using Terraform to monitor a DMS RabbitMQ instance with
CES (Cloud Eye Service) alarm rules and SMN (Simple Message Notification) SMS alerts in Huaweicloud.
When key RabbitMQ metrics exceed defined thresholds, CES triggers alarm notifications through SMN to
send SMS alerts to the configured phone number.

## Prerequisites

- A HuaweiCloud account
- Terraform installed (>= 1.3.0)
- HuaweiCloud access key and secret key (AK/SK)
- A valid phone number for receiving SMS alerts

## Architecture

```text
+---------------------------+
|  VPC / Subnet / SecGroup  |
|  (Network infrastructure  |
|   with custom rules)      |
+------------+--------------+
             |
             v
+---------------------------+
|  DMS RabbitMQ Instance    |
|  (Publishes metrics to    |
|   CES via SYS.DMS)        |
+------------+--------------+
             |
             v
+---------------------------+
|  CES Alarm Rule           |
|  (Evaluates metrics:      |
|   connections, channels,  |
|   queues, fd_used, etc.)  |
+------------+--------------+
             |  Alarm triggered
             v
+---------------------------+
|  SMN Topic                |
|  (Receives alarm message) |
+------------+--------------+
             |
             v
+---------------------------+
|  SMN SMS Subscription     |
|  (Sends SMS to phone)     |
+---------------------------+
```

### Monitored RabbitMQ Metrics

| Metric Name   | Description                                       |
|---------------|---------------------------------------------------|
| `connections` | Number of current connections                     |
| `channels`    | Number of current channels                        |
| `queues`      | Number of queues                                  |
| `fd_used`     | Number of file descriptors in use                 |
| `mem_used`    | Memory usage in bytes                             |
| `disk_free`   | Available disk space in bytes                     |
| `messages`    | Total number of messages (ready + unacknowledged) |

## Variable Introduction

The following variables need to be configured:

### Authentication Variables

- `region_name` - The region where resources will be created
- `access_key` - The access key of the IAM user
- `secret_key` - The secret key of the IAM user

### Resource Variables

#### Required Variables

- `vpc_name` - The name of the VPC
- `subnet_name` - The name of the subnet
- `security_group_name` - The name of the security group
- `instance_name` - The name of the RabbitMQ instance
- `instance_access_user_name` - The access user of the RabbitMQ instance
- `instance_password` - The access password of the RabbitMQ instance
- `smn_topic_name` - The name of the SMN topic used to send alarm notifications
- `sms_subscription_endpoint` - The phone number for SMS notification,
  format: +{country_code}{phone_number}, e.g. +8613600000000
- `alarm_rule_name` - The name of the CES alarm rule
- `alarm_rule_conditions` - The list of alarm rule conditions for RabbitMQ monitoring

#### Optional Variables

- `vpc_cidr` - The CIDR block of the VPC (default: "192.168.0.0/16")
- `subnet_cidr` - The CIDR block of the subnet (default: "")
- `subnet_gateway_ip` - The gateway IP of the subnet (default: "")
- `security_group_rule_configurations` - The list of security group rule
  configurations (default: allow AMQP 5672 and management 15672 ports)
- `instance_flavor_type` - The flavor type of the RabbitMQ instance
  (default: "cluster")
- `instance_storage_spec_code` - The storage specification code of the
  RabbitMQ instance (default: "dms.physical.storage.ultra.v2")
- `availability_zone_number` - The number of availability zones to which the
  RabbitMQ instance belongs (default: 1)
- `instance_engine_version` - The engine version of the RabbitMQ instance
  (default: "3.8.35")
- `instance_broker_num` - The number of brokers of the RabbitMQ instance
  (default: 3)
- `instance_storage_space` - The storage space of the RabbitMQ instance in GB
  (default: 600)
- `instance_ssl_enable` - Whether to enable SSL for the RabbitMQ instance
  (default: false)
- `instance_description` - The description of the RabbitMQ instance (default: "")
- `enterprise_project_id` - The enterprise project ID (default: null)
- `instance_tags` - The key/value pairs to associate with the RabbitMQ instance
  (default: {})
- `charging_mode` - The charging mode of the RabbitMQ instance
  (default: "postPaid")
- `period_unit` - The period unit of the RabbitMQ instance (default: null)
- `period` - The period of the RabbitMQ instance (default: null)
- `auto_renew` - The auto renew of the RabbitMQ instance (default: "false")
- `smn_topic_display_name` - The display name of the SMN topic (default: "")
- `sms_subscription_remark` - The remark of the SMS subscription
  (default: "RabbitMQ alarm notification")
- `alarm_rule_description` - The description of the CES alarm rule (default: "")
- `alarm_action_enabled` - Whether to enable the action to be triggered by an
  alarm (default: true)
- `alarm_enabled` - Whether to enable the alarm (default: true)
- `alarm_rule_notification_begin_time` - The alarm notification start time,
  e.g. 00:00 (default: null)
- `alarm_rule_notification_end_time` - The alarm notification stop time,
  e.g. 23:59 (default: null)
- `dashboard_name` - The name of the CES monitoring dashboard for RabbitMQ
  (default: "")
- `dashboard_widget_configurations` - The list of dashboard widget
  configurations for RabbitMQ monitoring. Each item includes `title`,
  `metric_name`, `left`, `top`, `width` (default: 6), and `height`
  (default: 3). (default: connections, channels, queues, fd_used)

## Usage

- Copy this example script to your working directory.

- Create a `terraform.tfvars` file and fill in the required variables:

   ```hcl
   # Network
   vpc_name            = "rabbitmq-monitor-vpc"
   subnet_name         = "rabbitmq-monitor-subnet"
   security_group_name = "rabbitmq-monitor-sg"

   # DMS RabbitMQ Instance
   instance_name             = "rabbitmq-monitored"
   # Replace with your RabbitMQ instance access information
   instance_access_user_name = "rabbitmq_admin"
   instance_password         = "YourPassword@123"

   # SMN Notification
   smn_topic_name            = "rabbitmq-alarm-topic"
   # Replace with your phone number
   # Format: +[country code][phone number], e.g. +8613600000000
   sms_subscription_endpoint = "+8613600000000"

   # CES Alarm Rule
   alarm_rule_name = "rabbitmq-instance-alarm"
   # Alarm conditions for RabbitMQ key metrics.
   # Each item defines a monitoring rule for a specific metric.
   alarm_rule_conditions = [
     {
       metric_name         = "<metric_name>"
       period              = <period>
       filter              = "<filter>"
       comparison_operator = "<comparison_operator>"
       value               = <value>
       count               = <count>
       unit                = "<unit>"
       suppress_duration   = <suppress_duration>
       alarm_level         = <alarm_level>
     },
     # ... add more rules as needed
   ]
   ```

- Initialize Terraform:

   ```bash
   terraform init
   ```

- Review the Terraform plan:

   ```bash
   terraform plan
   ```

- Apply the configuration:

   ```bash
   terraform apply
   ```

- Verify the deployment:

   After the deployment completes, you can verify that the resources are working:

  - **Confirm SMS subscription:**

     After applying, the phone number will receive an SMS confirmation message from SMN.
     You must reply to confirm the subscription before alarm notifications can be delivered.

  - **Check the CES alarm rule:**

     Log in to the HuaweiCloud console and navigate to CES to see the alarm rule and
     its status.

  - **View the CES dashboard:**

     Navigate to the CES dashboard to view real-time RabbitMQ metric charts for
     connections, channels, queues, and file descriptors used.

  - **Trigger a test alarm:**

     Adjust alarm thresholds to low values to trigger a test alarm and verify that
     the SMS notification is received.

- To clean up the resources:

  ```bash
  terraform destroy
  ```

## Notes

- Never commit `terraform.tfvars` with real credentials to version control
- After applying, you must confirm the SMS subscription on your phone before alarm
  notifications can be delivered
- CES uses the namespace `SYS.DMS` with dimension `rabbitmq_instance_id` to monitor
  RabbitMQ metrics
- The alarm rule is configured with `alarm_type = "MULTI_INSTANCE"` to support
  monitoring multiple metrics on the same instance
- Both alarm trigger (`alarm_actions`) and recovery (`ok_actions`) notifications are
  sent to the SMN topic
- A CES monitoring dashboard with visualization widgets is created for real-time
  graphical views of key metrics. The widgets are configurable via the
  `dashboard_widget_configurations` variable
- RabbitMQ instance creation takes about 20-50 minutes depending on the flavor and
  broker number
- To add more metrics, add entries to the `alarm_rule_conditions` variable
- To add email notification, create another `huaweicloud_smn_subscription` resource
  with `protocol = "email"`

## Requirements

| Name | Version |
| ---- | ------- |
| terraform | >= 1.3.0 |
| huaweicloud | >= 1.68.0 |
