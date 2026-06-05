# Deploy CES Event Alarm Rule

## Application Scenario

Simple Message Notification (SMN) is a reliable and scalable message notification service provided by Huawei Cloud, supporting multiple message notification methods including email, SMS, HTTP/HTTPS, etc. Cloud Eye Service (CES) is a monitoring service provided by Huawei Cloud, supporting real-time resource monitoring and alarms. Through CES event alarm rules, SMN topic events can be monitored, and notifications are automatically sent when alarm conditions are met. This best practice introduces how to use Terraform to automatically deploy CES event alarm rules, including creating SMN topics and configuring CES alarm rules, achieving monitoring and alerting for SMN topic events.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [SMN Topic Resource (huaweicloud\_smn\_topic)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_topic)
- [CES Alarm Rule Resource (huaweicloud\_ces\_alarmrule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/ces_alarmrule)

### Resource/Data Source Dependencies

```
huaweicloud_smn_topic
    └── huaweicloud_ces_alarmrule
```

> Note: CES alarm rules need to reference the SMN topic URN to send alarm notifications, so alarm rules depend on SMN topic resources.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Create SMN Topic

Add the following script to the TF file (such as main.tf) to create an SMN topic:

```hcl
variable "smn_topic_name" {
  description = "The name of the SMN topic used to send alarm notifications"
  type        = string
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project"
  type        = string
  default     = null
}

# Create SMN topic resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_smn_topic" "test" {
  name                  = var.smn_topic_name
  enterprise_project_id = var.enterprise_project_id
}
```

**Parameter Description**:

- **name**: Topic name, assigned by referencing the input variable `smn_topic_name`
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable `enterprise_project_id`, optional parameter

### 3. Create CES Alarm Rule

Add the following script to the TF file (such as main.tf) to create a CES alarm rule:

```hcl
variable "alarm_rule_name" {
  description = "The name of the CES alarm rule"
  type        = string
}

variable "alarm_rule_description" {
  description = "The description of the CES alarm rule"
  type        = string
  default     = null
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

variable "alarm_type" {
  description = "The type of the alarm"
  type        = string
  default     = "ALL_INSTANCE"
}

variable "alarm_rule_conditions" {
  description = "The list of alarm rule conditions"
  type        = list(object({
    metric_name         = string
    period              = string
    filter              = string
    comparison_operator = string
    value               = string
    count               = string
    unit                = optional(string)
    suppress_duration   = optional(string)
    alarm_level         = optional(string)
  }))

  nullable = false
}

variable "alarm_rule_resource" {
  description = "The list of resource dimensions for specified monitoring scope"
  type        = list(object({
    name  = string
    value = optional(string)
  }))

  default  = []
  nullable = true
}

variable "alarm_rule_notification_begin_time" {
  description = "The alarm notification start time"
  type        = string
  default     = null
}

variable "alarm_rule_notification_end_time" {
  description = "The alarm notification stop time"
  type        = string
  default     = null
}

variable "alarm_rule_effective_timezone" {
  description = "The time zone"
  type        = string
  default     = null
}

# Create CES alarm rule resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_ces_alarmrule" "test" {
  alarm_name            = var.alarm_rule_name
  alarm_description     = var.alarm_rule_description
  alarm_action_enabled  = var.alarm_action_enabled
  alarm_enabled         = var.alarm_enabled
  alarm_type            = var.alarm_type
  enterprise_project_id = var.enterprise_project_id

  metric {
    namespace = "SYS.SMN"
  }

  dynamic "condition" {
    for_each = var.alarm_rule_conditions

    content {
      metric_name         = condition.value.metric_name
      period              = condition.value.period
      filter              = condition.value.filter
      comparison_operator = condition.value.comparison_operator
      value               = condition.value.value
      unit                = condition.value.unit
      count               = condition.value.count
      suppress_duration   = condition.value.suppress_duration
      alarm_level         = condition.value.alarm_level
    }
  }

  dynamic "resources" {
    for_each = var.alarm_rule_resource

    content {
      dimensions {
        name  = resources.value.name
        value = resources.value.value
      }
    }
  }

  alarm_actions {
    type = "notification"

    notification_list = [
      huaweicloud_smn_topic.test.topic_urn
    ]
  }

  notification_begin_time = var.alarm_rule_notification_begin_time
  notification_end_time   = var.alarm_rule_notification_end_time
  effective_timezone      = var.alarm_rule_effective_timezone
}
```

**Parameter Description**:

- **alarm\_name**: Alarm rule name, assigned by referencing the input variable `alarm_rule_name`
- **alarm\_description**: Alarm rule description, assigned by referencing the input variable `alarm_rule_description`, optional parameter
- **alarm\_action\_enabled**: Whether to enable alarm actions, assigned by referencing the input variable `alarm_action_enabled`, default is `true`
- **alarm\_enabled**: Whether to enable the alarm, assigned by referencing the input variable `alarm_enabled`, default is `true`
- **alarm\_type**: Alarm type, assigned by referencing the input variable `alarm_type`, default is `ALL_INSTANCE`
- **metric**: Monitoring metric configuration, namespace set to `SYS.SMN` indicates monitoring SMN service
- **condition**: Alarm condition list, creates multiple alarm conditions through dynamic block `dynamic "condition"` based on input variable `alarm_rule_conditions`
- **resources**: Monitoring resource dimension list, creates resource dimensions through dynamic block `dynamic "resources"` based on input variable `alarm_rule_resource`
- **alarm\_actions**: Alarm action configuration, type is `notification`, notification list references SMN topic URN
- **notification\_begin\_time**: Alarm notification start time, assigned by referencing the input variable `alarm_rule_notification_begin_time`, optional parameter
- **notification\_end\_time**: Alarm notification stop time, assigned by referencing the input variable `alarm_rule_notification_end_time`, optional parameter
- **effective\_timezone**: Time zone, assigned by referencing the input variable `alarm_rule_effective_timezone`, optional parameter

> Note: Alarm rules reference the SMN topic `topic_urn` through `notification_list` in `alarm_actions` to send alarm notifications. Alarm conditions support multiple condition configurations, each condition includes metric name, period, filter method, comparison operator, threshold, and other parameters.

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# SMN topic configuration (Required)
smn_topic_name = "tf_test_topic"

# CES alarm rule basic information (Required)
alarm_rule_name        = "tf_test_alarm_rule"
alarm_rule_description = "Monitor SMN topic events"
alarm_type             = "ALL_INSTANCE"

# Alarm condition configuration (Required)
alarm_rule_conditions = [
  {
    metric_name         = "email_total_count"
    period              = "1"
    filter              = "average"
    comparison_operator = ">="
    value               = "80"
    count               = "3"
    unit                = "count"
    alarm_level         = "3"
  }
]

# Monitoring resource dimension configuration (Optional)
alarm_rule_resource = [
  {
    name = "topic_id"
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="smn_topic_name=tf_test_topic" -var="alarm_rule_name=tf_test_alarm_rule"`
2. Environment variables: `export TF_VAR_smn_topic_name=tf_test_topic`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating SMN topic and CES alarm rule
4. Run `terraform show` to view the created resources

## Reference Information

- [Huawei Cloud SMN Product Documentation](https://support.huaweicloud.com/smn/index.html)
- [Huawei Cloud CES Product Documentation](https://support.huaweicloud.com/ces/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For CES Event Alarm Rule](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/smn/ces-event-alarm-rule)

# Deploy Message Publish

## Application Scenario

Simple Message Notification (SMN) is a reliable and scalable message notification service provided by Huawei Cloud, supporting multiple message notification methods including email, SMS, HTTP/HTTPS, etc. Through message publishing, messages can be published to SMN topics, and terminals subscribed to the topic will receive message notifications. Message publishing supports multiple methods including direct message content, message structure, and message templates, meeting message publishing requirements for different scenarios. This best practice introduces how to use Terraform to automatically deploy message publishing, including creating SMN topics, subscriptions, message templates (optional), and publishing messages.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [SMN Topic Resource (huaweicloud\_smn\_topic)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_topic)
- [SMN Subscription Resource (huaweicloud\_smn\_subscription)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_subscription)
- [SMN Message Template Resource (huaweicloud\_smn\_message\_template)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_message_template)
- [SMN Message Publish Resource (huaweicloud\_smn\_message\_publish)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_message_publish)

### Resource/Data Source Dependencies

```
huaweicloud_smn_topic
    ├── huaweicloud_smn_subscription
    └── huaweicloud_smn_message_publish

huaweicloud_smn_message_template
    └── huaweicloud_smn_message_publish
```

> Note: Message publishing depends on SMN topics, and message templates can be optionally used. Subscriptions are used to receive message notifications. After messages are published, terminals subscribed to the topic will receive messages.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Create SMN Topic

Add the following script to the TF file (such as main.tf) to create an SMN topic:

```hcl
variable "topic_name" {
  description = "The name of the SMN topic"
  type        = string
}

variable "topic_display_name" {
  description = "The display name of the SMN topic"
  type        = string
  default     = ""
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project"
  type        = string
  default     = null
}

# Create SMN topic resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_smn_topic" "test" {
  name                  = var.topic_name
  display_name          = var.topic_display_name
  enterprise_project_id = var.enterprise_project_id
}
```

**Parameter Description**:

- **name**: Topic name, assigned by referencing the input variable `topic_name`
- **display\_name**: Topic display name, assigned by referencing the input variable `topic_display_name`, optional parameter
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable `enterprise_project_id`, optional parameter

### 3. Create SMN Subscription

Add the following script to the TF file (such as main.tf) to create an SMN subscription:

```hcl
variable "subscription_protocol" {
  description = "The protocol of the subscription"
  type        = string
}

variable "subscription_endpoint" {
  description = "The endpoint of the subscription"
  type        = string
}

variable "subscription_description" {
  description = "The remark for SMN subscriptions"
  type        = string
  default     = ""
}

# Create SMN subscription resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_smn_subscription" "test" {
  topic_urn = huaweicloud_smn_topic.test.id
  protocol  = var.subscription_protocol
  endpoint  = var.subscription_endpoint
  remark    = var.subscription_description
}
```

**Parameter Description**:

- **topic\_urn**: Topic URN, assigned by referencing the SMN topic resource ID
- **protocol**: Subscription protocol, assigned by referencing the input variable `subscription_protocol`. Supports `email`, `sms`, `http`, `https`, `functionstage`, etc.
- **endpoint**: Subscription endpoint, assigned by referencing the input variable `subscription_endpoint`. Fill in the corresponding endpoint address according to the protocol type
- **remark**: Subscription remark, assigned by referencing the input variable `subscription_description`, optional parameter

> Note: Subscription protocol and endpoint must match. For example, SMS protocol requires a phone number, and email protocol requires an email address.

### 4. Create Message Template (Optional)

Add the following script to the TF file (such as main.tf) to create a message template (optional):

```hcl
variable "template_name" {
  description = "The name of the message template"
  type        = string
  default     = ""
  nullable    = false
}

variable "template_protocol" {
  description = "The protocol of the message template"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = var.template_name == "" || var.template_protocol != ""
    error_message = "The template_protocol is required if template_name is provided."
  }
}

variable "template_content" {
  description = "The content of the message template"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = var.template_name == "" || var.template_content != ""
    error_message = "The template_content is required if template_name is provided."
  }
}

# Create message template (create when template_name is not empty)
resource "huaweicloud_smn_message_template" "test" {
  count    = var.template_name != "" ? 1 : 0

  name     = var.template_name
  protocol = var.template_protocol
  content  = var.template_content
}
```

**Parameter Description**:

- **count**: Resource count, creates resource when `template_name` is not empty
- **name**: Template name, assigned by referencing the input variable `template_name`
- **protocol**: Template protocol, assigned by referencing the input variable `template_protocol`
- **content**: Template content, assigned by referencing the input variable `template_content`

> Note: Message templates are optional. If using templates to publish messages, message templates need to be created first. Template protocol must match subscription protocol.

### 5. Publish Message

Add the following script to the TF file (such as main.tf) to publish a message:

```hcl
variable "pulblish_subject" {
  description = "The subject of the message"
  type        = string
}

variable "pulblish_message" {
  description = "The message content (mutually exclusive with message_structure)"
  type        = string
  default     = ""
  nullable    = false
}

variable "pulblish_message_structure" {
  description = "The JSON message structure that allows sending different content to different protocol subscribers (mutually exclusive with message)"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = !(var.template_name == "" && var.pulblish_message == "") || var.pulblish_message_structure != ""
    error_message = "The pulblish_message_structure is required if both template_name and pulblish_message are not provided."
  }
}

variable "pulblish_time_to_live" {
  description = "The maximum retention time of the message within the SMN system in seconds (default: 3600, max: 86400)"
  type        = string
  default     = null
}

variable "pulblish_tags" {
  description = "The tags of the message"
  type        = map(string)
  default     = {}
}

variable "pulblish_message_attributes" {
  description = "The message attributes of the message"
  type        = list(object({
    name   = string
    type   = string
    value  = optional(string)
    values = optional(list(string))
  }))

  default  = []
  nullable = false
}

# Publish message in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_smn_message_publish" "test" {
  topic_urn             = huaweicloud_smn_topic.test.topic_urn
  subject               = var.pulblish_subject
  message               = var.pulblish_message != "" ? var.pulblish_message : null
  message_structure     = var.pulblish_message_structure != "" ? var.pulblish_message_structure : null
  message_template_name = var.template_name != "" ? try(huaweicloud_smn_message_template.test[0].name, null) : null
  time_to_live          = var.pulblish_time_to_live
  tags                  = var.pulblish_tags

  dynamic "message_attributes" {
    for_each = var.pulblish_message_attributes

    content {
      name   = message_attributes.value.name
      type   = message_attributes.value.type
      value  = message_attributes.value.value
      values = message_attributes.value.values
    }
  }
}
```

**Parameter Description**:

- **topic\_urn**: Topic URN, assigned by referencing the SMN topic resource `topic_urn`
- **subject**: Message subject, assigned by referencing the input variable `pulblish_subject`
- **message**: Message content, assigned by referencing the input variable `pulblish_message`, mutually exclusive with `message_structure`, optional parameter
- **message\_structure**: Message structure, assigned by referencing the input variable `pulblish_message_structure`, JSON format, allows sending different content to different protocol subscribers, mutually exclusive with `message`, optional parameter
- **message\_template\_name**: Message template name, references message template resource name when `template_name` is not empty, optional parameter
- **time\_to\_live**: Maximum retention time of the message within the SMN system (seconds), assigned by referencing the input variable `pulblish_time_to_live`, default is 3600 seconds, maximum 86400 seconds, optional parameter
- **tags**: Message tags, assigned by referencing the input variable `pulblish_tags`, optional parameter
- **message\_attributes**: Message attribute list, creates multiple message attributes through dynamic block `dynamic "message_attributes"` based on input variable `pulblish_message_attributes`, optional parameter

> Note: Message publishing supports three methods: direct message content (message), message structure (message\_structure), and message template (message\_template\_name). Message and message structure are mutually exclusive. If using message templates, message content is not required. Message structure is in JSON format and can send different content to subscribers of different protocols.

### 6. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# SMN topic configuration (Required)
topic_name = "tf_test_topic"

# SMN subscription configuration (Required)
subscription_protocol      = "sms"
subscription_endpoint      = "18629199536"

# Message publishing configuration (Required)
pulblish_subject           = "tf_test_subject"
pulblish_message_structure = "{\"default\":\"Dear user, this is a default message.\",\"sms\":\"Dear user, this is an SMS message.\"}"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="topic_name=tf_test_topic" -var="subscription_protocol=sms"`
2. Environment variables: `export TF_VAR_topic_name=tf_test_topic`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 7. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating SMN topic, subscription, and publishing messages
4. Run `terraform show` to view the created resources

## Reference Information

- [Huawei Cloud SMN Product Documentation](https://support.huaweicloud.com/smn/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Message Publish](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/smn/publish-message)

# Deploy Topic with AOM Alarm Notification

## Application Scenario

Simple Message Notification (SMN) is a reliable and scalable message notification service provided by Huawei Cloud, supporting multiple message notification methods including email, SMS, HTTP/HTTPS, etc. Application Operations Management (AOM) is a one-stop application operations management platform provided by Huawei Cloud, supporting application monitoring, log management, alarm management, and other functions. By configuring AOM alarm notifications to SMN topics, automatic push of alarm messages can be achieved. At the same time, by configuring SMN log tanks, operation logs of SMN topics can be stored in Log Tank Service (LTS), achieving unified log management and analysis. This best practice introduces how to use Terraform to automatically deploy topics with AOM alarm notifications, including creating SMN topics, LTS log groups and streams, SMN log tank configuration, and AOM alarm action rule configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [SMN Topic Resource (huaweicloud\_smn\_topic)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_topic)
- [LTS Log Group Resource (huaweicloud\_lts\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_group)
- [LTS Log Stream Resource (huaweicloud\_lts\_stream)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_stream)
- [SMN Log Tank Resource (huaweicloud\_smn\_logtank)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_logtank)
- [AOM Alarm Action Rule Resource (huaweicloud\_aom\_alarm\_action\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/aom_alarm_action_rule)

### Resource/Data Source Dependencies

```
huaweicloud_smn_topic
    ├── huaweicloud_smn_logtank
    └── huaweicloud_aom_alarm_action_rule

huaweicloud_lts_group
    └── huaweicloud_lts_stream
        └── huaweicloud_smn_logtank
```

> Note: SMN log tanks depend on SMN topics and LTS log streams, used to store operation logs of SMN topics to LTS. AOM alarm action rules depend on SMN topics, used to configure the sending target of alarm notifications.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Create SMN Topic

Add the following script to the TF file (such as main.tf) to create an SMN topic:

```hcl
variable "smn_topic_name" {
  description = "The name of the SMN topic used to send AOM alarm notifications"
  type        = string
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project"
  type        = string
  default     = null
}

# Create SMN topic resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_smn_topic" "test" {
  name                  = var.smn_topic_name
  enterprise_project_id = var.enterprise_project_id
}
```

**Parameter Description**:

- **name**: Topic name, assigned by referencing the input variable `smn_topic_name`
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable `enterprise_project_id`, optional parameter

### 3. Create LTS Log Group and Log Stream

Add the following script to the TF file (such as main.tf) to create LTS log group and log stream:

```hcl
variable "lts_group_name" {
  description = "The name of the LTS group"
  type        = string
}

variable "lts_group_ttl_in_days" {
  description = "The TTL in days of the LTS group"
  type        = number
  default     = 30
}

variable "lts_stream_name" {
  description = "The name of the LTS stream"
  type        = string
}

# Create LTS log group resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_lts_group" "test" {
  group_name            = var.lts_group_name
  ttl_in_days           = var.lts_group_ttl_in_days
  enterprise_project_id = var.enterprise_project_id
}

# Create LTS log stream resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_lts_stream" "test" {
  group_id              = huaweicloud_lts_group.test.id
  stream_name           = var.lts_stream_name
  enterprise_project_id = var.enterprise_project_id
}
```

**Parameter Description**:

- **group\_name**: Log group name, assigned by referencing the input variable `lts_group_name`
- **ttl\_in\_days**: Log group TTL (days), assigned by referencing the input variable `lts_group_ttl_in_days`, default is 30 days
- **stream\_name**: Log stream name, assigned by referencing the input variable `lts_stream_name`
- **group\_id**: Log group ID, assigned by referencing the LTS log group resource ID

> Note: Log streams must belong to a log group, so the log group needs to be created first. The log group TTL is used to set the log retention time.

### 4. Configure SMN Log Tank

Add the following script to the TF file (such as main.tf) to configure SMN log tank:

```hcl
# Create SMN log tank resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_smn_logtank" "test" {
  topic_urn     = huaweicloud_smn_topic.test.topic_urn
  log_group_id  = huaweicloud_lts_group.test.id
  log_stream_id = huaweicloud_lts_stream.test.id
}
```

**Parameter Description**:

- **topic\_urn**: Topic URN, assigned by referencing the SMN topic resource `topic_urn`
- **log\_group\_id**: Log group ID, assigned by referencing the LTS log group resource ID
- **log\_stream\_id**: Log stream ID, assigned by referencing the LTS log stream resource ID

> Note: SMN log tanks are used to store operation logs of SMN topics to LTS, achieving unified log management and analysis.

### 5. Configure AOM Alarm Action Rule

Add the following script to the TF file (such as main.tf) to configure AOM alarm action rule:

```hcl
variable "alarm_action_rule_name" {
  description = "The name of the AOM alarm action rule that used to send the SMN notification"
  type        = string
}

variable "alarm_action_rule_user_name" {
  description = "The user name of the AOM alarm action rule"
  type        = string
}

variable "alarm_action_rule_type" {
  description = "The type of the AOM alarm action rule"
  type        = string
  default     = "1"
}

variable "alarm_action_rule_description" {
  description = "The description of the AOM alarm action rule"
  type        = string
  default     = null
}

# Create AOM alarm action rule resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_aom_alarm_action_rule" "test" {
  name                  = var.alarm_action_rule_name
  user_name             = var.alarm_action_rule_user_name
  type                  = var.alarm_action_rule_type
  notification_template = "aom.built-in.template.zh"
  description           = var.alarm_action_rule_description

  smn_topics {
    topic_urn = huaweicloud_smn_topic.test.topic_urn
  }
}
```

**Parameter Description**:

- **name**: Alarm action rule name, assigned by referencing the input variable `alarm_action_rule_name`
- **user\_name**: User name, assigned by referencing the input variable `alarm_action_rule_user_name`
- **type**: Rule type, assigned by referencing the input variable `alarm_action_rule_type`, default is `1` (notification type)
- **notification\_template**: Notification template, set to `aom.built-in.template.zh` indicates using AOM built-in Chinese template
- **description**: Rule description, assigned by referencing the input variable `alarm_action_rule_description`, optional parameter
- **smn\_topics**: SMN topic configuration, assigned by referencing the SMN topic resource `topic_urn`, used to specify the sending target of alarm notifications

> Note: AOM alarm action rules are used to configure the sending method of alarm notifications. By configuring SMN topics, automatic push of alarm messages can be achieved. Notification templates can choose built-in templates or custom templates.

### 6. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# SMN topic configuration (Required)
smn_topic_name = "tf_test_topic"

# LTS log group and stream configuration (Required)
lts_group_name  = "tf_test_group"
lts_stream_name = "tf_test_stream"

# AOM alarm action rule configuration (Required)
alarm_action_rule_name      = "tf_test_action_rule"
alarm_action_rule_user_name = "your_operation_user_name"
alarm_action_rule_type      = "1"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="smn_topic_name=tf_test_topic" -var="lts_group_name=tf_test_group"`
2. Environment variables: `export TF_VAR_smn_topic_name=tf_test_topic`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 7. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating SMN topic, LTS log group and stream, SMN log tank, and AOM alarm action rule
4. Run `terraform show` to view the created resources

## Reference Information

- [Huawei Cloud SMN Product Documentation](https://support.huaweicloud.com/smn/index.html)
- [Huawei Cloud AOM Product Documentation](https://support.huaweicloud.com/aom/index.html)
- [Huawei Cloud LTS Product Documentation](https://support.huaweicloud.com/lts/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Topic with AOM Alarm Notification](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/smn/topic-with-aom-alarm-notification)
