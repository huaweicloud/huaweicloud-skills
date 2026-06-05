# Deploy AOM Alarm Action Callback

## Application Scenario

Application Operations Management (AOM) is a one-stop application operations management platform provided by Huawei Cloud, supporting core functions such as application monitoring, log management, and alarm management. By configuring AOM alarm action callbacks, alarm information can be sent to specified callback URLs through Simple Message Notification (SMN), enabling real-time notification and processing of alarm information. Alarm action callbacks help users quickly respond to alarm events and improve operational efficiency.

This best practice will introduce how to use Terraform to automatically deploy AOM alarm action callbacks, including creating SMN topics and subscriptions, AOM message templates, and configuring AOM alarm action rules.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [Simple Message Notification Topic Resource (huaweicloud\_smn\_topic)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_topic)
- [Simple Message Notification Subscription Resource (huaweicloud\_smn\_subscription)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_subscription)
- [AOM Message Template Resource (huaweicloud\_aom\_message\_template)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/aom_message_template)
- [AOM Alarm Action Rule Resource (huaweicloud\_aom\_alarm\_action\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/aom_alarm_action_rule)

### Resource/Data Source Dependencies

```
huaweicloud_smn_topic
    └── huaweicloud_smn_subscription

huaweicloud_aom_message_template
    └── huaweicloud_aom_alarm_action_rule

huaweicloud_smn_topic
    └── huaweicloud_aom_alarm_action_rule
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create Simple Message Notification Topic Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Simple Message Notification topic resource:

```hcl
variable "smn_topic_name" {
  description = "The name of the SMN topic that used to send the SMN notification"
  type        = string
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project"
  type        = string
  default     = ""
}

# Create Simple Message Notification topic resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_smn_topic" "test" {
  name                  = var.smn_topic_name
  enterprise_project_id = var.enterprise_project_id != "" ? var.enterprise_project_id : null
}
```

**Parameter Description**:

- **name**: The topic name, assigned by referencing the input variable smn\_topic\_name
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, set to null when the value is an empty string

### 3. Create Simple Message Notification Subscription Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Simple Message Notification subscription resource:

```hcl
variable "alarm_callback_urls" {
  description = "The URLs of the alarm callback"
  type        = list(string)

  validation {
    condition     = length(var.alarm_callback_urls) > 0 && alltrue([for url in var.alarm_callback_urls : length(regexall("^http[s]?://", url)) > 0])
    error_message = "The alarm callback URLs must be provided and must start with http:// or https://"
  }
}

# Create Simple Message Notification subscription resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_smn_subscription" "test" {
  count = length(var.alarm_callback_urls) > 0 ? 1 : 0

  topic_urn = huaweicloud_smn_topic.test.id
  protocol  = length(regexall("^https?://", var.alarm_callback_urls[count.index])) > 0 ? "https" : "http"
  endpoint  = var.alarm_callback_urls[count.index]
}
```

**Parameter Description**:

- **count**: The number of subscription resources to create, used to control whether to create subscriptions, only created when the alarm\_callback\_urls list is not empty
- **topic\_urn**: The topic URN, referencing the ID of the previously created Simple Message Notification topic resource (huaweicloud\_smn\_topic.test)
- **protocol**: The protocol of the message receiving endpoint, automatically determined as http or https based on the callback URL prefix
- **endpoint**: The message receiving endpoint address, assigned by referencing elements in the input variable alarm\_callback\_urls list

> Note: In actual use, if alarm\_callback\_urls contains multiple URLs, separate subscription resources need to be created for each URL. The above example code needs to be adjusted according to actual requirements.

### 4. Create AOM Message Template Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an AOM message template resource:

```hcl
variable "alarm_notification_template_name" {
  description = "The name of the AOM alarm notification template that used to send the SMN notification"
  type        = string
}

variable "alarm_notification_template_locale" {
  description = "The locale of the AOM alarm notification template that used to send the SMN notification"
  type        = string
  default     = "en-us"

  validation {
    condition     = contains(["en-us", "zh-cn"], var.alarm_notification_template_locale)
    error_message = "The alarm notification template locale must be 'en-us' or 'zh-cn'"
  }
}

variable "alarm_notification_template_description" {
  description = "The description of the AOM alarm notification template that used to send the SMN notification"
  type        = string
  default     = ""
}

variable "alarm_notification_template_notification_type" {
  description = "The notification type of the AOM alarm notification template that used to send the SMN notification"
  type        = string
  default     = "email"
}

variable "alarm_notification_template_notification_topic" {
  description = "The notification topic of the AOM alarm notification template that used to send the SMN notification"
  type        = string
  default     = "An alert occurred at time $${starts_at}[$${event_severity}_$${event_type}_$${clear_type}]."
}

variable "alarm_notification_template_content" {
  description = "The content of the AOM alarm notification template that used to send the SMN notification"
  type        = string
  default     = <<EOT
Alarm Name: $${event_name_alias};
Alarm ID: $${id};
Notification Rule: $${action_rule};
Trigger Time: $${starts_at};
Trigger Level: $${event_severity};
Alarm Content: $${alarm_info};
Resource Identifier: $${resources_new};
Remediation Suggestion: $${alarm_fix_suggestion_zh};
  EOT
}

# Create AOM message template resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_aom_message_template" "test" {
  name                  = var.alarm_notification_template_name
  locale                = var.alarm_notification_template_locale
  enterprise_project_id = var.enterprise_project_id != "" ? var.enterprise_project_id : null
  description           = var.alarm_notification_template_description

  templates {
    sub_type = var.alarm_notification_template_notification_type
    topic    = var.alarm_notification_template_notification_topic
    content  = var.alarm_notification_template_content
  }
}
```

**Parameter Description**:

- **name**: The message template name, assigned by referencing the input variable alarm\_notification\_template\_name
- **locale**: The message template language, assigned by referencing the input variable alarm\_notification\_template\_locale, default value is "en-us", valid values are "en-us" or "zh-cn"
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, set to null when the value is an empty string
- **description**: The message template description, assigned by referencing the input variable alarm\_notification\_template\_description, default value is an empty string
- **templates.sub\_type**: The notification type, assigned by referencing the input variable alarm\_notification\_template\_notification\_type, default value is "email"
- **templates.topic**: The notification topic template, assigned by referencing the input variable alarm\_notification\_template\_notification\_topic, supports variable substitution
- **templates.content**: The notification content template, assigned by referencing the input variable alarm\_notification\_template\_content, supports variable substitution

### 5. Create AOM Alarm Action Rule Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an AOM alarm action rule resource:

```hcl
variable "alarm_action_rule_name" {
  description = "The name of the AOM alarm action rule that used to send the SMN notification"
  type        = string
}

variable "alarm_action_rule_user_name" {
  description = "The user name of the AOM alarm action rule that used to send the SMN notification"
  type        = string
}

variable "alarm_action_rule_type" {
  description = "The type of the AOM alarm action rule that used to send the SMN notification"
  type        = string
  default     = "1" # notification
}

# Create AOM alarm action rule resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_aom_alarm_action_rule" "test" {
  depends_on = [huaweicloud_aom_message_template.test]

  name                  = var.alarm_action_rule_name
  user_name             = var.alarm_action_rule_user_name
  type                  = var.alarm_action_rule_type
  notification_template = huaweicloud_aom_message_template.test.name

  smn_topics {
    topic_urn = huaweicloud_smn_topic.test.topic_urn
  }
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency relationship, ensuring the AOM message template resource is created before the alarm action rule resource
- **name**: The alarm action rule name, assigned by referencing the input variable alarm\_action\_rule\_name
- **user\_name**: The user name, assigned by referencing the input variable alarm\_action\_rule\_user\_name
- **type**: The alarm action rule type, assigned by referencing the input variable alarm\_action\_rule\_type, default value is "1" (indicating notification type)
- **notification\_template**: The notification template name, referencing the name of the previously created AOM message template resource (huaweicloud\_aom\_message\_template.test)
- **smn\_topics.topic\_urn**: The SMN topic URN, referencing the topic\_urn of the previously created Simple Message Notification topic resource (huaweicloud\_smn\_topic.test)

### 6. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Simple Message Notification Topic Configuration
smn_topic_name = "tf_test_alarm_action_callback"

# Alarm Callback URL Configuration
alarm_callback_urls = ["https://www.example.com"]

# AOM Message Template Configuration
alarm_notification_template_name        = "tf_test_alarm_action_callback"
alarm_notification_template_description = "This is a AOM alarm notification template created by Terraform"

# AOM Alarm Action Rule Configuration
alarm_action_rule_name      = "tf_test_alarm_action_callback"
alarm_action_rule_user_name = "your_operation_user_name"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="smn_topic_name=test-topic" -var="alarm_callback_urls=[\"https://www.example.com\"]"`
2. Environment variables: `export TF_VAR_smn_topic_name=test-topic`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 7. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the AOM alarm action callback
4. Run `terraform show` to view the details of the created AOM alarm action callback

## Reference Information

- [Huawei Cloud AOM Product Documentation](https://support.huaweicloud.com/aom/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For AOM Alarm Action Callback](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/aom/action-callback)

# Deploy AOM Distribute Alarms by Tags

## Application Scenario

Application Operations Management (AOM) is a one-stop application operations management platform provided by Huawei Cloud, supporting core functions such as application monitoring, log management, and alarm management. By configuring AOM to distribute alarms by tags, alarms can be grouped and distributed based on Huawei Cloud tags (Tag), enabling fine-grained alarm management based on tags. This approach helps users perform differentiated alarm processing for different types of resources according to business needs, improving the flexibility and efficiency of alarm management.

This best practice will introduce how to use Terraform to automatically deploy AOM distribute alarms by tags, including creating Prometheus instances, cloud service access, alarm rules, and configuring alarm action rules and tag management.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [DCS Instance Query Data Source (data.huaweicloud\_dcs\_instances)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/dcs_instances)
- [Project Query Data Source (data.huaweicloud\_identity\_projects)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/identity_projects)

### Resources

- [Log Tank Service Log Group Resource (huaweicloud\_lts\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_group)
- [Log Tank Service Log Stream Resource (huaweicloud\_lts\_stream)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_stream)
- [Simple Message Notification Topic Resource (huaweicloud\_smn\_topic)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_topic)
- [Simple Message Notification Log Tank Resource (huaweicloud\_smn\_logtank)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_logtank)
- [AOM Alarm Action Rule Resource (huaweicloud\_aom\_alarm\_action\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/aom_alarm_action_rule)
- [Tag Management Service Resource Tags Resource (huaweicloud\_tms\_resource\_tags)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/tms_resource_tags)
- [AOM Prometheus Instance Resource (huaweicloud\_aom\_prom\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/aom_prom_instance)
- [AOM Cloud Service Access Resource (huaweicloud\_aom\_cloud\_service\_access)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/aom_cloud_service_access)
- [AOM Alarm Rule Resource (huaweicloud\_aomv4\_alarm\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/aomv4_alarm_rule)

### Resource/Data Source Dependencies

```
data.huaweicloud_dcs_instances
    ├── huaweicloud_lts_group
    │   ├── huaweicloud_lts_stream
    │   │   └── huaweicloud_smn_logtank
    │   └── huaweicloud_smn_logtank
    ├── huaweicloud_tms_resource_tags
    │   └── huaweicloud_aom_prom_instance
    │       └── huaweicloud_aom_cloud_service_access
    │           └── huaweicloud_aomv4_alarm_rule
    └── huaweicloud_smn_topic
        ├── huaweicloud_smn_logtank
        └── huaweicloud_aom_alarm_action_rule
            └── huaweicloud_aomv4_alarm_rule

data.huaweicloud_identity_projects
    └── huaweicloud_tms_resource_tags
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query DCS Instance Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to obtain the enterprise project ID and other information of the DCS instance:

```hcl
variable "dcs_instance_name" {
  description = "The name of the existing DCS instance to be monitored"
  type        = string
  default     = ""
}

# Query DCS instance information with the specified name in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used to obtain enterprise project ID and other information
data "huaweicloud_dcs_instances" "test" {
  name = var.dcs_instance_name
}
```

**Parameter Description**:

- **name**: The DCS instance name, assigned by referencing the input variable dcs\_instance\_name

### 3. Query Project Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to obtain the project ID:

```hcl
variable "region_name" {
  description = "The region where resources will be created"
  type        = string
}

# Query project information with the specified name in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used to obtain project ID
data "huaweicloud_identity_projects" "test" {
  name = var.region_name
}
```

**Parameter Description**:

- **name**: The project name, assigned by referencing the input variable region\_name

### 4. Create Log Tank Service Log Group Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Log Tank Service log group resource:

```hcl
variable "lts_group_name" {
  description = "The name of the LTS group used to store SMN notification logs"
  type        = string
}

# Create Log Tank Service log group resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_lts_group" "test" {
  group_name            = var.lts_group_name
  ttl_in_days           = 30
  enterprise_project_id = local.enterprise_project_id
}
```

**Parameter Description**:

- **group\_name**: The log group name, assigned by referencing the input variable lts\_group\_name
- **ttl\_in\_days**: The log retention time (unit: days), set to 30 days
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the local variable enterprise\_project\_id

### 5. Create Log Tank Service Log Stream Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Log Tank Service log stream resource:

```hcl
variable "lts_stream_name" {
  description = "The name of the LTS stream used to store SMN notification logs"
  type        = string
}

# Create Log Tank Service log stream resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_lts_stream" "test" {
  group_id              = huaweicloud_lts_group.test.id
  stream_name           = var.lts_stream_name
  enterprise_project_id = local.enterprise_project_id
}
```

**Parameter Description**:

- **group\_id**: The log group ID, referencing the ID of the previously created Log Tank Service log group resource (huaweicloud\_lts\_group.test)
- **stream\_name**: The log stream name, assigned by referencing the input variable lts\_stream\_name
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the local variable enterprise\_project\_id

### 6. Create Simple Message Notification Topic Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Simple Message Notification topic resource:

```hcl
variable "smn_topic_name" {
  description = "The name of the SMN topic used to send notifications"
  type        = string
}

# Create Simple Message Notification topic resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_smn_topic" "test" {
  name                  = var.smn_topic_name
  enterprise_project_id = local.enterprise_project_id
}
```

**Parameter Description**:

- **name**: The topic name, assigned by referencing the input variable smn\_topic\_name
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the local variable enterprise\_project\_id

### 7. Create Simple Message Notification Log Tank Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Simple Message Notification log tank resource:

```hcl
# Create Simple Message Notification log tank resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_smn_logtank" "test" {
  topic_urn     = huaweicloud_smn_topic.test.topic_urn
  log_group_id  = huaweicloud_lts_group.test.id
  log_stream_id = huaweicloud_lts_stream.test.id
}
```

**Parameter Description**:

- **topic\_urn**: The topic URN, referencing the topic\_urn of the previously created Simple Message Notification topic resource (huaweicloud\_smn\_topic.test)
- **log\_group\_id**: The log group ID, referencing the ID of the previously created Log Tank Service log group resource (huaweicloud\_lts\_group.test)
- **log\_stream\_id**: The log stream ID, referencing the ID of the previously created Log Tank Service log stream resource (huaweicloud\_lts\_stream.test)

### 8. Create AOM Alarm Action Rule Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an AOM alarm action rule resource:

```hcl
variable "alarm_action_rule_name" {
  description = "The name of the AOM alarm action rule used to send SMN notifications"
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

# Create AOM alarm action rule resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_aom_alarm_action_rule" "test" {
  name                  = var.alarm_action_rule_name
  user_name             = var.alarm_action_rule_user_name
  type                  = var.alarm_action_rule_type
  notification_template = "aom.built-in.template.zh"

  smn_topics {
    topic_urn = huaweicloud_smn_topic.test.topic_urn
  }
}
```

**Parameter Description**:

- **name**: The alarm action rule name, assigned by referencing the input variable alarm\_action\_rule\_name
- **user\_name**: The user name, assigned by referencing the input variable alarm\_action\_rule\_user\_name
- **type**: The alarm action rule type, assigned by referencing the input variable alarm\_action\_rule\_type, default value is "1" (indicating notification type)
- **notification\_template**: The notification template name, using the built-in template "aom.built-in.template.zh"
- **smn\_topics.topic\_urn**: The SMN topic URN, referencing the topic\_urn of the previously created Simple Message Notification topic resource (huaweicloud\_smn\_topic.test)

### 9. Create Tag Management Service Resource Tags Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Tag Management Service resource tags resource:

```hcl
variable "alarm_rule_matric_dimension_tags" {
  description = "The custom tags to be added to the DCS instance for alarm distribution"
  type        = map(string)
}

# Create Tag Management Service resource tags resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_tms_resource_tags" "test" {
  project_id = local.exact_project_id

  resources {
    resource_type = "dcs"
    resource_id   = try(data.huaweicloud_dcs_instances.test.instances[0].id, null)
  }

  tags = var.alarm_rule_matric_dimension_tags
}
```

**Parameter Description**:

- **project\_id**: The project ID, assigned by referencing the local variable exact\_project\_id
- **resources.resource\_type**: The resource type, set to "dcs"
- **resources.resource\_id**: The resource ID, assigned based on the return results of the DCS instance query data source (data.huaweicloud\_dcs\_instances.test)
- **tags**: The tag key-value pairs, assigned by referencing the input variable alarm\_rule\_matric\_dimension\_tags

### 10. Create AOM Prometheus Instance Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an AOM Prometheus instance resource:

```hcl
variable "prometheus_instance_name" {
  description = "The name of the Prometheus instance for cloud services"
  type        = string
}

# Create AOM Prometheus instance resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_aom_prom_instance" "test" {
  depends_on = [huaweicloud_tms_resource_tags.test]

  prom_name             = var.prometheus_instance_name
  prom_type             = "CLOUD_SERVICE"
  enterprise_project_id = local.enterprise_project_id
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency relationship, ensuring the Tag Management Service resource tags resource is created before the Prometheus instance resource
- **prom\_name**: The Prometheus instance name, assigned by referencing the input variable prometheus\_instance\_name
- **prom\_type**: The Prometheus instance type, set to "CLOUD\_SERVICE" (indicating cloud service type)
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the local variable enterprise\_project\_id

### 11. Create AOM Cloud Service Access Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an AOM cloud service access resource:

```hcl
# Create AOM cloud service access resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_aom_cloud_service_access" "test" {
  instance_id           = huaweicloud_aom_prom_instance.test.id
  service               = "DCS"
  tag_sync              = "auto"
  enterprise_project_id = local.enterprise_project_id

  provisioner "local-exec" {
    command = "sleep 240" # Waiting for the access center to complete the connection and generate indicators
  }
}
```

**Parameter Description**:

- **instance\_id**: The Prometheus instance ID, referencing the ID of the previously created AOM Prometheus instance resource (huaweicloud\_aom\_prom\_instance.test)
- **service**: The cloud service type, set to "DCS"
- **tag\_sync**: The tag synchronization method, set to "auto" (indicating automatic synchronization)
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the local variable enterprise\_project\_id
- **provisioner.local-exec.command**: Local execution command, wait 240 seconds to ensure the access center completes the connection and generates indicators

### 12. Create AOM Alarm Rule Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an AOM alarm rule resource:

```hcl
variable "alarm_rule_name" {
  description = "The name of the AOM alarm rule"
  type        = string
}

variable "alarm_rule_trigger_conditions" {
  description = "The trigger conditions of the AOM alarm rule"
  type = list(object({
    metric_name             = string
    promql                  = string
    promql_for              = optional(string, "")
    aggregate_type          = optional(string, "by")
    aggregation_type        = string
    aggregation_window      = string
    metric_unit             = string
    metric_query_mode       = string
    metric_namespace        = string
    operator                = string
    metric_statistic_method = string
    thresholds              = map(string)
    trigger_type            = string
    trigger_interval        = string
    trigger_times           = string
    query_param             = string
    query_match             = string
  }))
}

# Create AOM alarm rule resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_aomv4_alarm_rule" "test" {
  depends_on = [huaweicloud_aom_cloud_service_access.test]

  name                  = var.alarm_rule_name
  type                  = "metric"
  enable                = true
  prom_instance_id      = huaweicloud_aom_prom_instance.test.id
  enterprise_project_id = local.enterprise_project_id

  alarm_notifications {
    notification_enable       = true
    notification_type         = "direct"
    bind_notification_rule_id = huaweicloud_aom_alarm_action_rule.test.id
    notify_resolved           = true
    notify_triggered          = true
    notify_frequency          = "0"
  }

  metric_alarm_spec {
    monitor_type = "all_metric"

    recovery_conditions {
      recovery_timeframe = 1
    }

    dynamic "trigger_conditions" {
      for_each = var.alarm_rule_trigger_conditions

      content {
        metric_query_mode       = trigger_conditions.value.metric_query_mode
        metric_name             = trigger_conditions.value.metric_name
        promql                  = trigger_conditions.value.promql
        promql_for              = trigger_conditions.value.promql_for
        aggregate_type          = trigger_conditions.value.aggregate_type
        aggregation_type        = trigger_conditions.value.aggregation_type
        aggregation_window      = trigger_conditions.value.aggregation_window
        metric_unit             = trigger_conditions.value.metric_unit
        metric_namespace        = trigger_conditions.value.metric_namespace
        operator                = trigger_conditions.value.operator
        metric_statistic_method = trigger_conditions.value.metric_statistic_method
        thresholds              = trigger_conditions.value.thresholds
        trigger_type            = trigger_conditions.value.trigger_type
        trigger_interval        = trigger_conditions.value.trigger_interval
        trigger_times           = trigger_conditions.value.trigger_times
        query_param             = trigger_conditions.value.query_param
        query_match             = trigger_conditions.value.query_match
      }
    }
  }

  lifecycle {
    ignore_changes = [
      metric_alarm_spec # If you want to update this configuration, please use a version higher than 1.82.3
    ]
  }
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency relationship, ensuring the AOM cloud service access resource is created before the alarm rule resource
- **name**: The alarm rule name, assigned by referencing the input variable alarm\_rule\_name
- **type**: The alarm rule type, set to "metric" (indicating metric type)
- **enable**: Whether to enable the alarm rule, set to true
- **prom\_instance\_id**: The Prometheus instance ID, referencing the ID of the previously created AOM Prometheus instance resource (huaweicloud\_aom\_prom\_instance.test)
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the local variable enterprise\_project\_id
- **alarm\_notifications.notification\_enable**: Whether to enable notifications, set to true
- **alarm\_notifications.notification\_type**: The notification type, set to "direct" (indicating direct notification)
- **alarm\_notifications.bind\_notification\_rule\_id**: The bound notification rule ID, referencing the ID of the previously created AOM alarm action rule resource (huaweicloud\_aom\_alarm\_action\_rule.test)
- **alarm\_notifications.notify\_resolved**: Whether to notify on recovery, set to true
- **alarm\_notifications.notify\_triggered**: Whether to notify on trigger, set to true
- **alarm\_notifications.notify\_frequency**: The notification frequency, set to "0" (indicating notify on every trigger)
- **metric\_alarm\_spec.monitor\_type**: The monitoring type, set to "all\_metric" (indicating all metrics)
- **metric\_alarm\_spec.recovery\_conditions.recovery\_timeframe**: The recovery time frame, set to 1 (unit: minutes)
- **metric\_alarm\_spec.trigger\_conditions**: The trigger conditions list, dynamically generated through the dynamic block based on the input variable alarm\_rule\_trigger\_conditions, where promql must include tag conditions (e.g., `huaweicloud_sys_dcs_cpu_usage{Ihn="OPEN"}`), and query\_match must include tag matching conditions

### 13. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# DCS Instance Configuration
dcs_instance_name = "tf_test_aom_alarm_rule_distribute_alarm"

# Log Tank Service Configuration
lts_group_name  = "tf_test_aom_alarm_rule_distribute_alarm"
lts_stream_name = "tf_test_aom_alarm_rule_distribute_alarm"

# Simple Message Notification Topic Configuration
smn_topic_name = "tf_test_aom_alarm_rule_distribute_alarm"

# AOM Alarm Action Rule Configuration
alarm_action_rule_name      = "tf_test_aom_alarm_rule_distribute_alarm_by_Ihn_tag"
alarm_action_rule_user_name = "servicestage"

# Tag Configuration
alarm_rule_matric_dimension_tags = {
  "Ihn" = "OPEN"
}

# Prometheus Instance Configuration
prometheus_instance_name = "tf_test_aom_alarm_rule_distribute_alarm"

# AOM Alarm Rule Configuration
alarm_rule_name = "tf_test_aom_alarm_rule_distribute_alarm_by_Ihn_tag"
alarm_rule_trigger_conditions = [
  {
    metric_name             = "huaweicloud_sys_dcs_cpu_usage"
    promql                  = "label_replace(avg_over_time(huaweicloud_sys_dcs_cpu_usage{Ihn=\"OPEN\"}[59999ms]),\"__name__\",\"huaweicloud_sys_dcs_cpu_usage\",\"\",\"\")"
    promql_for              = ""
    aggregate_type          = "by"
    aggregation_type        = "average"
    aggregation_window      = "1m"
    metric_unit             = "%"
    metric_query_mode       = "PROM"
    metric_namespace        = "SYS.DCS"
    operator                = ">"
    metric_statistic_method = "single"
    thresholds              = {
      "Critical" = 1
    }
    trigger_type            = "FIXED_RATE"
    trigger_interval        = "1m"
    trigger_times           = "3"
    query_param             = "{\"code\": \"a\", \"apmMetricReg\": []}"
    query_match             = "[{\"id\":\"first\",\"dimension\":\"Ihn\",\"conditionValue\":[{\"name\":\"OPEN\"}],\"conditionList\":[{\"name\":\"OPEN\"}],\"addMode\": \"first\",\"conditionCompare\":\"=\",\"regExpress\":null,\"dimensionSelected\":{\"label\":\"Ihn\",\"id\":\"Ihn\"}}]"
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="dcs_instance_name=test-instance" -var="lts_group_name=test-group"`
2. Environment variables: `export TF_VAR_dcs_instance_name=test-instance`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 14. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating AOM distribute alarms by tags
4. Run `terraform show` to view the details of the created AOM distribute alarms by tags

## Reference Information

- [Huawei Cloud AOM Product Documentation](https://support.huaweicloud.com/aom/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For AOM Distribute Alarms by Tags](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/aom/alarm-rule/distribute-alarm)

# Deploy AOM Prevent ELB Alarm Storm

## Application Scenario

Application Operations Management (AOM) is a one-stop application operations management platform provided by Huawei Cloud, supporting core functions such as application monitoring, log management, and alarm management. When monitoring ELB business layer metrics, a large number of duplicate or similar alarms may be generated, causing alarm storms that affect operational efficiency. By configuring AOM alarm group rules, similar alarms can be grouped and merged, reducing alarm noise and preventing alarm storms, improving the effectiveness of alarm management.

This best practice will introduce how to use Terraform to automatically deploy AOM prevent ELB alarm storm, including creating LTS log groups and streams, SMN topics and log tanks, AOM alarm action rules, alarm group rules, and configuring alarm rules.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [Log Tank Service Log Group Resource (huaweicloud\_lts\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_group)
- [Log Tank Service Log Stream Resource (huaweicloud\_lts\_stream)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_stream)
- [Simple Message Notification Topic Resource (huaweicloud\_smn\_topic)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_topic)
- [Simple Message Notification Log Tank Resource (huaweicloud\_smn\_logtank)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_logtank)
- [AOM Alarm Action Rule Resource (huaweicloud\_aom\_alarm\_action\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/aom_alarm_action_rule)
- [AOM Alarm Group Rule Resource (huaweicloud\_aom\_alarm\_group\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/aom_alarm_group_rule)
- [AOM Alarm Rule Resource (huaweicloud\_aomv4\_alarm\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/aomv4_alarm_rule)

### Resource/Data Source Dependencies

```
huaweicloud_lts_group
    └── huaweicloud_lts_stream
        └── huaweicloud_smn_logtank

huaweicloud_smn_topic
    ├── huaweicloud_smn_logtank
    └── huaweicloud_aom_alarm_action_rule
        └── huaweicloud_aom_alarm_group_rule
            └── huaweicloud_aomv4_alarm_rule
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create Log Tank Service Log Group Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Log Tank Service log group resource:

```hcl
variable "lts_group_name" {
  description = "The name of the LTS group that used to store the SMN notification logs"
  type        = string
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project"
  type        = string
  default     = ""
}

# Create Log Tank Service log group resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_lts_group" "test" {
  group_name            = var.lts_group_name
  ttl_in_days           = 30
  enterprise_project_id = var.enterprise_project_id != "" ? var.enterprise_project_id : null
}
```

**Parameter Description**:

- **group\_name**: The log group name, assigned by referencing the input variable lts\_group\_name
- **ttl\_in\_days**: The log retention time (unit: days), set to 30 days
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, set to null when the value is an empty string

### 3. Create Log Tank Service Log Stream Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Log Tank Service log stream resource:

```hcl
variable "lts_stream_name" {
  description = "The name of the LTS stream that used to store the SMN notification logs"
  type        = string
}

# Create Log Tank Service log stream resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_lts_stream" "test" {
  group_id              = huaweicloud_lts_group.test.id
  stream_name           = var.lts_stream_name
  enterprise_project_id = var.enterprise_project_id != "" ? var.enterprise_project_id : null
}
```

**Parameter Description**:

- **group\_id**: The log group ID, referencing the ID of the previously created Log Tank Service log group resource (huaweicloud\_lts\_group.test)
- **stream\_name**: The log stream name, assigned by referencing the input variable lts\_stream\_name
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, set to null when the value is an empty string

### 4. Create Simple Message Notification Topic Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Simple Message Notification topic resource:

```hcl
variable "smn_topic_name" {
  description = "The name of the SMN topic that used to send the SMN notification"
  type        = string
}

# Create Simple Message Notification topic resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_smn_topic" "test" {
  name                  = var.smn_topic_name
  enterprise_project_id = var.enterprise_project_id != "" ? var.enterprise_project_id : null
}
```

**Parameter Description**:

- **name**: The topic name, assigned by referencing the input variable smn\_topic\_name
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, set to null when the value is an empty string

### 5. Create Simple Message Notification Log Tank Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Simple Message Notification log tank resource:

```hcl
# Create Simple Message Notification log tank resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_smn_logtank" "test" {
  topic_urn     = huaweicloud_smn_topic.test.topic_urn
  log_group_id  = huaweicloud_lts_group.test.id
  log_stream_id = huaweicloud_lts_stream.test.id
}
```

**Parameter Description**:

- **topic\_urn**: The topic URN, referencing the topic\_urn of the previously created Simple Message Notification topic resource (huaweicloud\_smn\_topic.test)
- **log\_group\_id**: The log group ID, referencing the ID of the previously created Log Tank Service log group resource (huaweicloud\_lts\_group.test)
- **log\_stream\_id**: The log stream ID, referencing the ID of the previously created Log Tank Service log stream resource (huaweicloud\_lts\_stream.test)

### 6. Create AOM Alarm Action Rule Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an AOM alarm action rule resource:

```hcl
variable "alarm_action_rule_name" {
  description = "The name of the AOM alarm action rule that used to send the SMN notification"
  type        = string
  default     = "apm"
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

# Create AOM alarm action rule resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_aom_alarm_action_rule" "test" {
  name                  = var.alarm_action_rule_name
  user_name             = var.alarm_action_rule_user_name
  type                  = var.alarm_action_rule_type
  notification_template = "aom.built-in.template.zh"

  smn_topics {
    topic_urn = huaweicloud_smn_topic.test.topic_urn
  }
}
```

**Parameter Description**:

- **name**: The alarm action rule name, assigned by referencing the input variable alarm\_action\_rule\_name, default value is "apm"
- **user\_name**: The user name, assigned by referencing the input variable alarm\_action\_rule\_user\_name
- **type**: The alarm action rule type, assigned by referencing the input variable alarm\_action\_rule\_type, default value is "1" (indicating notification type)
- **notification\_template**: The notification template name, using the built-in template "aom.built-in.template.zh"
- **smn\_topics.topic\_urn**: The SMN topic URN, referencing the topic\_urn of the previously created Simple Message Notification topic resource (huaweicloud\_smn\_topic.test)

### 7. Create AOM Alarm Group Rule Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an AOM alarm group rule resource:

```hcl
variable "alarm_group_rule_name" {
  description = "The name of the AOM alarm group rule"
  type        = string
}

variable "alarm_group_rule_group_interval" {
  description = "The group interval of the AOM alarm group rule"
  type        = number
  default     = 60
}

variable "alarm_group_rule_group_repeat_waiting" {
  description = "The group repeat waiting of the AOM alarm group rule"
  type        = number
  default     = 3600
}

variable "alarm_group_rule_group_wait" {
  description = "The group wait of the AOM alarm group rule"
  type        = number
  default     = 15
}

variable "alarm_group_rule_description" {
  description = "The description of the AOM alarm group rule"
  type        = string
  default     = ""
}

variable "alarm_group_rule_condition_matching_rules" {
  description = "The condition matching rules of the AOM alarm group rule"
  type = list(object({
    key     = string
    operate = string
    value   = list(string)
  }))
  default = [
    {
      key     = "event_severity"
      operate = "EXIST"
      value   = ["Critical", "Major"]
    },
    {
      key     = "resource_provider"
      operate = "EQUALS"
      value   = ["AOM"]
    }
  ]
}

# Create AOM alarm group rule resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_aom_alarm_group_rule" "test" {
  depends_on = [huaweicloud_aom_alarm_action_rule.test]

  name                  = var.alarm_group_rule_name
  group_by              = ["resource_provider"]
  group_interval        = var.alarm_group_rule_group_interval
  group_repeat_waiting  = var.alarm_group_rule_group_repeat_waiting
  group_wait            = var.alarm_group_rule_group_wait
  description           = var.alarm_group_rule_description != "" ? var.alarm_group_rule_description : null
  enterprise_project_id = var.enterprise_project_id != "" ? var.enterprise_project_id : null

  detail {
    bind_notification_rule_ids = [huaweicloud_aom_alarm_action_rule.test.name]

    dynamic "match" {
      for_each = var.alarm_group_rule_condition_matching_rules

      content {
        key     = match.value.key
        operate = match.value.operate
        value   = match.value.value
      }
    }
  }
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency relationship, ensuring the AOM alarm action rule resource is created before the alarm group rule resource
- **name**: The alarm group rule name, assigned by referencing the input variable alarm\_group\_rule\_name
- **group\_by**: The list of grouping fields, set to \["resource\_provider"] (indicating grouping by resource provider)
- **group\_interval**: The group check interval (unit: seconds), assigned by referencing the input variable alarm\_group\_rule\_group\_interval, default value is 60 seconds
- **group\_repeat\_waiting**: The group repeat waiting time (unit: seconds), assigned by referencing the input variable alarm\_group\_rule\_group\_repeat\_waiting, default value is 3600 seconds
- **group\_wait**: The group wait time (unit: seconds), assigned by referencing the input variable alarm\_group\_rule\_group\_wait, default value is 15 seconds
- **description**: The alarm group rule description, assigned by referencing the input variable alarm\_group\_rule\_description, set to null when the value is an empty string
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, set to null when the value is an empty string
- **detail.bind\_notification\_rule\_ids**: The list of bound notification rule IDs, referencing the name of the previously created AOM alarm action rule resource (huaweicloud\_aom\_alarm\_action\_rule.test)
- **detail.match**: The list of matching conditions, dynamically generated through the dynamic block based on the input variable alarm\_group\_rule\_condition\_matching\_rules, default filters for Critical and Major severity alarms and alarms from AOM

### 8. Create AOM Alarm Rule Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an AOM alarm rule resource:

```hcl
variable "alarm_rule_name" {
  description = "The name of the AOM alarm rule"
  type        = string
}

variable "prometheus_instance_id" {
  description = "The ID of the Prometheus instance"
  type        = string
  default     = "0"
}

variable "alarm_rule_trigger_conditions" {
  description = "The trigger conditions of the AOM alarm rule"
  type = list(object({
    metric_name             = string
    promql                  = string
    promql_for              = string
    aggregate_type          = optional(string, "by")
    aggregation_type        = string
    aggregation_window      = string
    metric_statistic_method = string
    thresholds              = map(any)
    trigger_type            = string
    trigger_interval        = string
    trigger_times           = string
    query_param             = string
    query_match             = string
  }))
}

# Create AOM alarm rule resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_aomv4_alarm_rule" "test" {
  name             = var.alarm_rule_name
  type             = "metric"
  enable           = true
  prom_instance_id = var.prometheus_instance_id

  alarm_notifications {
    notification_enable = true
    notification_type   = "alarm_policy"
    route_group_enable  = true
    route_group_rule    = huaweicloud_aom_alarm_group_rule.test.name
    notify_resolved     = true
    notify_triggered    = true
    notify_frequency    = "-1"
  }

  metric_alarm_spec {
    monitor_type = "all_metric"

    recovery_conditions {
      recovery_timeframe = 1
    }

    dynamic "trigger_conditions" {
      for_each = var.alarm_rule_trigger_conditions

      content {
        metric_query_mode       = "PROM"
        metric_name             = trigger_conditions.value.metric_name
        promql                  = trigger_conditions.value.promql
        promql_for              = trigger_conditions.value.promql_for
        aggregate_type          = trigger_conditions.value.aggregate_type
        aggregation_type        = trigger_conditions.value.aggregation_type
        aggregation_window      = trigger_conditions.value.aggregation_window
        metric_statistic_method = trigger_conditions.value.metric_statistic_method
        thresholds              = trigger_conditions.value.thresholds
        trigger_type            = trigger_conditions.value.trigger_type
        trigger_interval        = trigger_conditions.value.trigger_interval
        trigger_times           = trigger_conditions.value.trigger_times
        query_param             = trigger_conditions.value.query_param
        query_match             = trigger_conditions.value.query_match
      }
    }
  }

  lifecycle {
    ignore_changes = [
      metric_alarm_spec # If you want to update this configuration, please use a version higher than 1.82.3
    ]
  }
}
```

**Parameter Description**:

- **name**: The alarm rule name, assigned by referencing the input variable alarm\_rule\_name
- **type**: The alarm rule type, set to "metric" (indicating metric type)
- **enable**: Whether to enable the alarm rule, set to true
- **prom\_instance\_id**: The Prometheus instance ID, assigned by referencing the input variable prometheus\_instance\_id, default value is "0" (indicating the default Prometheus\_AOM\_Default instance)
- **alarm\_notifications.notification\_enable**: Whether to enable notifications, set to true
- **alarm\_notifications.notification\_type**: The notification type, set to "alarm\_policy" (indicating alarm policy type)
- **alarm\_notifications.route\_group\_enable**: Whether to enable route grouping, set to true
- **alarm\_notifications.route\_group\_rule**: The route group rule name, referencing the name of the previously created AOM alarm group rule resource (huaweicloud\_aom\_alarm\_group\_rule.test)
- **alarm\_notifications.notify\_resolved**: Whether to notify on recovery, set to true
- **alarm\_notifications.notify\_triggered**: Whether to notify on trigger, set to true
- **alarm\_notifications.notify\_frequency**: The notification frequency, set to "-1" (indicating using the alarm group rule's frequency settings)
- **metric\_alarm\_spec.monitor\_type**: The monitoring type, set to "all\_metric" (indicating all metrics)
- **metric\_alarm\_spec.recovery\_conditions.recovery\_timeframe**: The recovery time frame, set to 1 (unit: minutes)
- **metric\_alarm\_spec.trigger\_conditions**: The trigger conditions list, dynamically generated through the dynamic block based on the input variable alarm\_rule\_trigger\_conditions

### 9. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Log Tank Service Configuration
lts_group_name  = "tf_test_aom_prevent_elb_alarm_storm"
lts_stream_name = "tf_test_aom_prevent_elb_alarm_storm"

# Simple Message Notification Topic Configuration
smn_topic_name = "tf_test_aom_prevent_elb_alarm_storm"

# AOM Alarm Action Rule Configuration
alarm_action_rule_user_name = "servicestage"

# AOM Alarm Group Rule Configuration
alarm_group_rule_name = "tf_test_aom_prevent_elb_alarm_storm"

# AOM Alarm Rule Configuration
alarm_rule_name        = "tf_test_aom_prevent_elb_alarm_storm"
prometheus_instance_id = "0"

alarm_rule_trigger_conditions = [
  {
    metric_name             = "aom_metrics_total_per_hour"
    promql                  = "label_replace(avg_over_time(aom_metrics_total_per_hour{type=\"custom\"}[59999ms]),\"__name__\",\"aom_metrics_total_per_hour\",\"\",\"\")"
    promql_for              = "3m"
    aggregate_type          = "by"
    aggregation_type        = "average"
    aggregation_window      = "1m"
    metric_statistic_method = "single"
    thresholds              = {
      "Critical" = 1
    }
    trigger_type            = "FIXED_RATE"
    trigger_interval        = "1m"
    trigger_times           = "3"
    query_param             = "{\"code\": \"a\", \"apmMetricReg\": []}"
    query_match             = "{\"id\": \"first\", \"dimension\": \"type\", \"conditionValue\": [{\"name\": \"custom\"}], \"conditionList\": [{\"name\": \"custom\"}, {\"name\": \"basic\"}], \"addMode\": \"first\", \"conditionCompare\": \"=\", \"dimensionSelected\": {\"label\": \"type\", \"id\": \"type\"}}"
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="lts_group_name=test-group" -var="alarm_rule_name=test-rule"`
2. Environment variables: `export TF_VAR_lts_group_name=test-group`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 10. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating AOM prevent ELB alarm storm
4. Run `terraform show` to view the details of the created AOM prevent ELB alarm storm

## Reference Information

- [Huawei Cloud AOM Product Documentation](https://support.huaweicloud.com/aom/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For AOM Prevent ELB Alarm Storm](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/aom/alarm-rule/prevent-elb-alarm-storm)
