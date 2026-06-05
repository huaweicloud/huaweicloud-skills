# Deploy Log Stream

## Application Scenario

Huawei Cloud Log Tank Service (LTS) log stream functionality is a fundamental component of log management, used to organize and store log data. By creating log groups and log streams, you can implement log classification management, lifecycle control, tag classification, and other functions. Log streams support multiple log collection methods, can receive log data from different applications and services, and provide powerful query and analysis capabilities.

This best practice is particularly suitable for scenarios that require centralized management of application logs, implementing log classification storage, and building log monitoring and analysis systems, such as application operation monitoring, security auditing, business data analysis, etc. This best practice will introduce how to use Terraform to automatically deploy LTS log streams, including log group and log stream creation, implementing complete log management infrastructure.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [Log Group Resource (huaweicloud\_lts\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_group)
- [Log Stream Resource (huaweicloud\_lts\_stream)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_stream)

### Resource/Data Source Dependencies

```
huaweicloud_lts_group
    └── huaweicloud_lts_stream
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create Log Group

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a log group resource:

```hcl
variable "group_name" {
  description = "The name of the log group"
  type        = string
}

variable "group_log_expiration_days" {
  description = "The log expiration days of the log group"
  type        = number
  default     = 14
}

variable "group_tags" {
  description = "The tags of the log group"
  type        = map(string)
  default     = {}
}

variable "enterprise_project_id" {
  description = "The enterprise project ID of the log group"
  type        = string
  default     = null
}

# Create a log group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_lts_group" "test" {
  group_name            = var.group_name
  ttl_in_days           = var.group_log_expiration_days
  tags                  = var.group_tags
  enterprise_project_id = var.enterprise_project_id
}
```

**Parameter Description**:

- **group\_name**: Log group name, assigned by referencing the input variable group\_name
- **ttl\_in\_days**: Log expiration days for the log group, assigned by referencing the input variable group\_log\_expiration\_days, default value is 14
- **tags**: Log group tags, assigned by referencing the input variable group\_tags, default value is empty map
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, default value is null

### 3. Create Log Stream

Add the following script to the TF file to instruct Terraform to create a log stream resource:

```hcl
variable "stream_name" {
  description = "The name of the log stream"
  type        = string
}

variable "stream_log_expiration_days" {
  description = "The log expiration days of the log stream"
  type        = number
  default     = null
}

variable "stream_tags" {
  description = "The tags of the log stream"
  type        = map(string)
  default     = {}
}

variable "stream_is_favorite" {
  description = "Whether to favorite the log stream"
  type        = bool
  default     = false
}

# Create a log stream resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_lts_stream" "test" {
  group_id              = huaweicloud_lts_group.test.id
  stream_name           = var.stream_name
  ttl_in_days           = var.stream_log_expiration_days
  tags                  = var.stream_tags
  enterprise_project_id = var.enterprise_project_id
  is_favorite           = var.stream_is_favorite
}
```

**Parameter Description**:

- **group\_id**: Log group ID that the log stream belongs to, referencing the ID of the previously created log group resource
- **stream\_name**: Log stream name, assigned by referencing the input variable stream\_name
- **ttl\_in\_days**: Log expiration days for the log stream, assigned by referencing the input variable stream\_log\_expiration\_days, default value is null (inherits log group settings)
- **tags**: Log stream tags, assigned by referencing the input variable stream\_tags, default value is empty map
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, default value is null
- **is\_favorite**: Whether to favorite the log stream, assigned by referencing the input variable stream\_is\_favorite, default value is false

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Log group configuration
group_name = "tf_test_server_group"

# Log stream configuration
stream_name = "tf_test_stream"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="group_name=my-group" -var="stream_name=my-stream"`
2. Environment variables: `export TF_VAR_group_name=my-group`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating log streams
4. Run `terraform show` to view the created log stream details

## Reference Information

- [Huawei Cloud Log Tank Service Product Documentation](https://support.huaweicloud.com/lts/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference LTS Log Stream](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/lts/log-stream)

# Deploy Log Transfer

## Application Scenario

Huawei Cloud Log Tank Service (LTS) log transfer functionality allows users to periodically transfer log data from LTS log groups and log streams to OBS (Object Storage Service), implementing long-term storage and backup of log data. By configuring log transfer tasks, you can implement automated log data archiving, cost optimization, and compliance requirements.

This best practice is particularly suitable for scenarios that require long-term log data preservation, implementing log data backup, meeting compliance audit requirements, and optimizing storage costs, such as log archiving, data lake construction, compliance auditing, etc. This best practice will introduce how to use Terraform to automatically deploy LTS log transfer, including log group, log stream, OBS bucket, and log transfer task creation, implementing a complete log transfer solution.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [Log Group Resource (huaweicloud\_lts\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_group)
- [Log Stream Resource (huaweicloud\_lts\_stream)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_stream)
- [OBS Bucket Resource (huaweicloud\_obs\_bucket)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket)
- [Log Transfer Resource (huaweicloud\_lts\_transfer)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_transfer)

### Resource/Data Source Dependencies

```
huaweicloud_lts_group
    ├── huaweicloud_lts_stream
    └── huaweicloud_lts_transfer

huaweicloud_obs_bucket
    └── huaweicloud_lts_transfer
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create Log Group

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a log group resource:

```hcl
variable "group_name" {
  description = "The name of the log group"
  type        = string
}

variable "group_log_expiration_days" {
  description = "The log expiration days of the log group"
  type        = number
  default     = 14
}

# Create a log group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_lts_group" "test" {
  group_name  = var.group_name
  ttl_in_days = var.group_log_expiration_days
}
```

**Parameter Description**:

- **group\_name**: Log group name, assigned by referencing the input variable group\_name
- **ttl\_in\_days**: Log expiration days for the log group, assigned by referencing the input variable group\_log\_expiration\_days, default value is 14

### 3. Create Log Stream

Add the following script to the TF file to instruct Terraform to create a log stream resource:

```hcl
variable "stream_name" {
  description = "The name of the log stream"
  type        = string
}

variable "stream_log_expiration_days" {
  description = "The log expiration days of the log stream"
  type        = number
  default     = null
}

# Create a log stream resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_lts_stream" "test" {
  group_id    = huaweicloud_lts_group.test.id
  stream_name = var.stream_name
  ttl_in_days = var.stream_log_expiration_days
}
```

**Parameter Description**:

- **group\_id**: Log group ID that the log stream belongs to, referencing the ID of the previously created log group resource
- **stream\_name**: Log stream name, assigned by referencing the input variable stream\_name
- **ttl\_in\_days**: Log expiration days for the log stream, assigned by referencing the input variable stream\_log\_expiration\_days, default value is null (inherits log group settings)

### 4. Create OBS Bucket

Add the following script to the TF file to instruct Terraform to create an OBS bucket resource:

```hcl
variable "bucket_name" {
  description = "The name of the OBS bucket"
  type        = string
}

# Create an OBS bucket resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_obs_bucket" "test" {
  bucket        = var.bucket_name
  acl           = "private"
  force_destroy = true
}
```

**Parameter Description**:

- **bucket**: OBS bucket name, assigned by referencing the input variable bucket\_name
- **acl**: Bucket ACL policy, set to "private" for private access
- **force\_destroy**: Whether to force delete the bucket, set to true to allow deletion of non-empty buckets

### 5. Create Log Transfer Task

Add the following script to the TF file to instruct Terraform to create a log transfer resource:

```hcl
variable "transfer_type" {
  description = "The type of the log transfer"
  type        = string
  default     = "OBS"
}

variable "transfer_mode" {
  description = "The mode of the log transfer"
  type        = string
  default     = "cycle"
}

variable "transfer_storage_format" {
  description = "The storage format of the log transfer"
  type        = string
  default     = "JSON"
}

variable "transfer_status" {
  description = "The status of the log transfer"
  type        = string
  default     = "ENABLE"
}

variable "bucket_dir_prefix_name" {
  description = "The prefix path of the OBS transfer task"
  type        = string
  default     = "LTS-test/%GroupName/%StreamName/%Y/%m/%d/%H/%M"
}

variable "bucket_time_zone" {
  description = "The time zone of the OBS bucket"
  type        = string
  default     = "UTC"
}

variable "bucket_time_zone_id" {
  description = "The time zone ID of the OBS bucket"
  type        = string
  default     = "Etc/GMT"
}

# Create a log transfer resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_lts_transfer" "test" {
  log_group_id = huaweicloud_lts_group.test.id

  log_streams {
    log_stream_id = huaweicloud_lts_stream.test.id
  }

  log_transfer_info {
    log_transfer_type   = var.transfer_type
    log_transfer_mode   = var.transfer_mode
    log_storage_format  = var.transfer_storage_format
    log_transfer_status = var.transfer_status

    log_transfer_detail {
      obs_bucket_name     = huaweicloud_obs_bucket.test.bucket
      obs_period          = 3
      obs_period_unit     = "hour"
      obs_dir_prefix_name = var.bucket_dir_prefix_name
      obs_time_zone       = var.bucket_time_zone
      obs_time_zone_id    = var.bucket_time_zone_id
    }
  }

  depends_on = [
    huaweicloud_obs_bucket.test,
  ]
}
```

**Parameter Description**:

- **log\_group\_id**: Log group ID that the log transfer belongs to, referencing the ID of the previously created log group resource
- **log\_streams**: Log stream configuration block
  - **log\_stream\_id**: Log stream ID to transfer, referencing the ID of the previously created log stream resource
- **log\_transfer\_info**: Log transfer information configuration block
  - **log\_transfer\_type**: Log transfer type, assigned by referencing the input variable transfer\_type, default value is "OBS"
  - **log\_transfer\_mode**: Log transfer mode, assigned by referencing the input variable transfer\_mode, default value is "cycle" (periodic transfer)
  - **log\_storage\_format**: Log storage format, assigned by referencing the input variable transfer\_storage\_format, default value is "JSON"
  - **log\_transfer\_status**: Log transfer status, assigned by referencing the input variable transfer\_status, default value is "ENABLE"
- **log\_transfer\_detail**: Log transfer detail configuration block
  - **obs\_bucket\_name**: OBS bucket name, referencing the name of the previously created OBS bucket resource
  - **obs\_period**: Transfer period, set to 3 to transfer every 3 time units
  - **obs\_period\_unit**: Transfer period unit, set to "hour" for hourly calculation
  - **obs\_dir\_prefix\_name**: OBS directory prefix name, assigned by referencing the input variable bucket\_dir\_prefix\_name, supports variable substitution
  - **obs\_time\_zone**: OBS time zone, assigned by referencing the input variable bucket\_time\_zone, default value is "UTC"
  - **obs\_time\_zone\_id**: OBS time zone ID, assigned by referencing the input variable bucket\_time\_zone\_id, default value is "Etc/GMT"
- **depends\_on**: Explicit dependency relationship, ensuring the OBS bucket exists before log transfer task creation

### 6. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Log group configuration
group_name = "tf_test_log_group"

# Log stream configuration
stream_name = "tf_test_log_stream"

# OBS bucket configuration
bucket_name = "tf-test-log-transfer-obs-bucket"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="group_name=my-group" -var="stream_name=my-stream"`
2. Environment variables: `export TF_VAR_group_name=my-group`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 7. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating log transfer
4. Run `terraform show` to view the created log transfer details

## Reference Information

- [Huawei Cloud Log Tank Service Product Documentation](https://support.huaweicloud.com/lts/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For LTS Log Transfer](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/lts/log-transfer)

# Deploy SQL Alarm Rule

## Application Scenario

Huawei Cloud Log Tank Service (LTS) SQL alarm rule functionality allows users to set alarm conditions based on SQL query results, automatically triggering alarm notifications when query results meet preset conditions. By configuring SQL alarm rules, you can implement real-time log data monitoring, anomaly detection, and automated alerting, improving operation efficiency and system reliability.

This best practice is particularly suitable for scenarios that require real-time log data monitoring, system anomaly detection, and automated alert notification, such as application performance monitoring, error log alerts, business metric monitoring, security event detection, etc. This best practice will introduce how to use Terraform to automatically deploy LTS SQL alarm rules, including SMN topic, log group, log stream, and SQL alarm rule creation, implementing a complete log monitoring and alert solution.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [LTS Notification Template Query Data Source (data.huaweicloud\_lts\_notification\_templates)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/lts_notification_templates)

### Resources

- [SMN Topic Resource (huaweicloud\_smn\_topic)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_topic)
- [Log Group Resource (huaweicloud\_lts\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_group)
- [Log Stream Resource (huaweicloud\_lts\_stream)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_stream)
- [SQL Alarm Rule Resource (huaweicloud\_lts\_sql\_alarm\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_sql_alarm_rule)

### Resource/Data Source Dependencies

```
data.huaweicloud_lts_notification_templates
    └── huaweicloud_lts_sql_alarm_rule

huaweicloud_smn_topic
    └── huaweicloud_lts_sql_alarm_rule

huaweicloud_lts_group
    ├── huaweicloud_lts_stream
    └── huaweicloud_lts_sql_alarm_rule

huaweicloud_lts_stream
    └── huaweicloud_lts_sql_alarm_rule
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create SMN Topic

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an SMN topic resource:

```hcl
variable "topic_name" {
  description = "The name of the SMN topic"
  type        = string
}

# Create an SMN topic resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_smn_topic" "test" {
  name         = var.topic_name
  display_name = "The display name of topic"
}
```

**Parameter Description**:

- **name**: SMN topic name, assigned by referencing the input variable topic\_name
- **display\_name**: SMN topic display name, set to "The display name of topic"

### 3. Create Log Group

Add the following script to the TF file to instruct Terraform to create a log group resource:

```hcl
variable "group_name" {
  description = "The name of the log group"
  type        = string
}

variable "group_log_expiration_days" {
  description = "The log expiration days of the log group"
  type        = number
  default     = 14
}

# Create a log group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_lts_group" "test" {
  group_name  = var.group_name
  ttl_in_days = var.group_log_expiration_days
}
```

**Parameter Description**:

- **group\_name**: Log group name, assigned by referencing the input variable group\_name
- **ttl\_in\_days**: Log expiration days for the log group, assigned by referencing the input variable group\_log\_expiration\_days, default value is 14

### 4. Create Log Stream

Add the following script to the TF file to instruct Terraform to create a log stream resource:

```hcl
variable "stream_name" {
  description = "The name of the log stream"
  type        = string
}

variable "stream_log_expiration_days" {
  description = "The log expiration days of the log stream"
  type        = number
  default     = null
}

# Create a log stream resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_lts_stream" "test" {
  group_id    = huaweicloud_lts_group.test.id
  stream_name = var.stream_name
  ttl_in_days = var.stream_log_expiration_days
}
```

**Parameter Description**:

- **group\_id**: Log group ID that the log stream belongs to, referencing the ID of the previously created log group resource
- **stream\_name**: Log stream name, assigned by referencing the input variable stream\_name
- **ttl\_in\_days**: Log expiration days for the log stream, assigned by referencing the input variable stream\_log\_expiration\_days, default value is null (inherits log group settings)

### 5. Query LTS Notification Template Information

Add the following script to the TF file to instruct Terraform to query LTS notification template information:

```hcl
variable "notification_template_name" {
  description = "The name of the notification template"
  type        = string
  default     = ""
  nullable    = false
}

variable "domain_id" {
  description = "The domain ID"
  type        = string
  default     = null
}

# Get all LTS notification template information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block) that meets specific conditions, used to create SQL alarm rules
data "huaweicloud_lts_notification_templates" "test" {
  count = var.notification_template_name != "" ? 0 : 1

  domain_id = var.domain_id
}
```

**Parameter Description**:

- **count**: Conditional creation, creates this data source when notification\_template\_name variable is not an empty string
- **domain\_id**: Domain ID, assigned by referencing the input variable domain\_id, default value is null

### 6. Create SQL Alarm Rule

Add the following script to the TF file to instruct Terraform to create a SQL alarm rule resource:

```hcl
variable "alarm_rule_name" {
  description = "The name of the SQL alarm rule"
  type        = string
}

variable "alarm_rule_condition_expression" {
  description = "The condition expression of the SQL alarm rule"
  type        = string
}

variable "alarm_rule_alarm_level" {
  description = "The alarm level of the SQL alarm rule"
  type        = string
  default     = "MINOR"
}

variable "alarm_rule_trigger_condition_count" {
  description = "The trigger condition count of the SQL alarm rule"
  type        = number
  default     = 2
}

variable "alarm_rule_trigger_condition_frequency" {
  description = "The trigger condition frequency of the SQL alarm rule"
  type        = number
  default     = 3
}

variable "alarm_rule_send_recovery_notifications" {
  description = "The send recovery notifications of the SQL alarm rule"
  type        = bool
  default     = true
}

variable "alarm_rule_recovery_frequency" {
  description = "The recovery frequency of the SQL alarm rule"
  type        = number
  default     = 4
}

variable "alarm_rule_notification_frequency" {
  description = "The notification frequency of the SQL alarm rule"
  type        = number
  default     = 15
}

variable "alarm_rule_alias" {
  description = "The alias of the SQL alarm rule"
  type        = string
  default     = ""
}

variable "alarm_rule_request_title" {
  description = "The request title of the SQL alarm rule"
  type        = string
}

variable "alarm_rule_request_sql" {
  description = "The request SQL of the SQL alarm rule"
  type        = string
}

variable "alarm_rule_request_search_time_range_unit" {
  description = "The request search time range unit of the SQL alarm rule"
  type        = string
  default     = "minute"
}

variable "alarm_rule_request_search_time_range" {
  description = "The request search time range of the SQL alarm rule"
  type        = number
  default     = 5
}

variable "alarm_rule_frequency_type" {
  description = "The frequency type of the SQL alarm rule"
  type        = string
  default     = "HOURLY"
}

variable "alarm_rule_notification_user_name" {
  description = "The notification user name of the SQL alarm rule"
  type        = string
}

variable "alarm_rule_notification_language" {
  description = "The notification language of the SQL alarm rule"
  type        = string
  default     = "en-us"
}

# Create a SQL alarm rule resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_lts_sql_alarm_rule" "test" {
  name                        = var.alarm_rule_name
  condition_expression        = var.alarm_rule_condition_expression
  alarm_level                 = var.alarm_rule_alarm_level
  send_notifications          = true
  trigger_condition_count     = var.alarm_rule_trigger_condition_count
  trigger_condition_frequency = var.alarm_rule_trigger_condition_frequency
  send_recovery_notifications = var.alarm_rule_send_recovery_notifications
  recovery_frequency          = var.alarm_rule_send_recovery_notifications ? var.alarm_rule_recovery_frequency : null
  notification_frequency      = var.alarm_rule_notification_frequency
  alarm_rule_alias            = var.alarm_rule_alias

  sql_requests {
    title                  = var.alarm_rule_request_title
    sql                    = var.alarm_rule_request_sql
    log_group_id           = huaweicloud_lts_group.test.id
    log_stream_id          = huaweicloud_lts_stream.test.id
    search_time_range_unit = var.alarm_rule_request_search_time_range_unit
    search_time_range      = var.alarm_rule_request_search_time_range
    log_group_name         = huaweicloud_lts_group.test.group_name
    log_stream_name        = huaweicloud_lts_stream.test.stream_name
  }

  frequency {
    type = var.alarm_rule_frequency_type
  }

  notification_save_rule {
    template_name = var.notification_template_name!= "" ? var.notification_template_name : try([for v in data.huaweicloud_lts_notification_templates.test.templates[*].name :v if v == "sql_template"][0], null)
    user_name     = var.alarm_rule_notification_user_name
    language      = var.alarm_rule_notification_language

    topics {
      name         = huaweicloud_smn_topic.test.name
      topic_urn    = huaweicloud_smn_topic.test.topic_urn
      display_name = huaweicloud_smn_topic.test.display_name
      push_policy  = huaweicloud_smn_topic.test.push_policy
    }
  }
}
```

**Parameter Description**:

- **name**: SQL alarm rule name, assigned by referencing the input variable alarm\_rule\_name
- **condition\_expression**: Alarm condition expression, assigned by referencing the input variable alarm\_rule\_condition\_expression
- **alarm\_level**: Alarm level, assigned by referencing the input variable alarm\_rule\_alarm\_level, default value is "MINOR"
- **send\_notifications**: Whether to send notifications, set to true to enable notifications
- **trigger\_condition\_count**: Trigger condition count, assigned by referencing the input variable alarm\_rule\_trigger\_condition\_count, default value is 2
- **trigger\_condition\_frequency**: Trigger condition frequency, assigned by referencing the input variable alarm\_rule\_trigger\_condition\_frequency, default value is 3
- **send\_recovery\_notifications**: Whether to send recovery notifications, assigned by referencing the input variable alarm\_rule\_send\_recovery\_notifications, default value is true
- **recovery\_frequency**: Recovery frequency, uses alarm\_rule\_recovery\_frequency value when send\_recovery\_notifications is true
- **notification\_frequency**: Notification frequency, assigned by referencing the input variable alarm\_rule\_notification\_frequency, default value is 15
- **alarm\_rule\_alias**: Alarm rule alias, assigned by referencing the input variable alarm\_rule\_alias, default value is empty string
- **sql\_requests**: SQL request configuration block
  - **title**: Request title, assigned by referencing the input variable alarm\_rule\_request\_title
  - **sql**: SQL query statement, assigned by referencing the input variable alarm\_rule\_request\_sql
  - **log\_group\_id**: Log group ID, referencing the ID of the previously created log group resource
  - **log\_stream\_id**: Log stream ID, referencing the ID of the previously created log stream resource
  - **search\_time\_range\_unit**: Search time range unit, assigned by referencing the input variable alarm\_rule\_request\_search\_time\_range\_unit, default value is "minute"
  - **search\_time\_range**: Search time range, assigned by referencing the input variable alarm\_rule\_request\_search\_time\_range, default value is 5
  - **log\_group\_name**: Log group name, referencing the name of the previously created log group resource
  - **log\_stream\_name**: Log stream name, referencing the name of the previously created log stream resource
- **frequency**: Frequency configuration block
  - **type**: Frequency type, assigned by referencing the input variable alarm\_rule\_frequency\_type, default value is "HOURLY"
- **notification\_save\_rule**: Notification save rule configuration block
  - **template\_name**: Notification template name, prioritizes using notification\_template\_name variable, if empty then tries to get "sql\_template" from query results
  - **user\_name**: Notification user name, assigned by referencing the input variable alarm\_rule\_notification\_user\_name
  - **language**: Notification language, assigned by referencing the input variable alarm\_rule\_notification\_language, default value is "en-us"
  - **topics**: Topic configuration block
    - **name**: Topic name, referencing the name of the previously created SMN topic resource
    - **topic\_urn**: Topic URN, referencing the URN of the previously created SMN topic resource
    - **display\_name**: Topic display name, referencing the display name of the previously created SMN topic resource
    - **push\_policy**: Push policy, referencing the push policy of the previously created SMN topic resource

### 7. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# SMN topic configuration
topic_name = "tf-test-topic"

# Log group configuration
group_name = "tf_test_log_group"

# Log stream configuration
stream_name = "tf_test_log_stream"

# Notification template configuration
domain_id = "your_domain_id"

# SQL alarm rule configuration
alarm_rule_name                   = "tf-test-sql-alarm-rule"
alarm_rule_condition_expression   = "t>0"
alarm_rule_request_title          = "tf-test-sql-alarm-rule-title"
alarm_rule_request_sql            = "select count(*) as t"
alarm_rule_notification_user_name = "your_notification_user_name"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="group_name=my-group" -var="stream_name=my-stream"`
2. Environment variables: `export TF_VAR_group_name=my-group`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating SQL alarm rules
4. Run `terraform show` to view the created SQL alarm rule details

## Reference Information

- [Huawei Cloud Log Tank Service Product Documentation](https://support.huaweicloud.com/lts/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For LTS SQL Alarm Rule](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/lts/sql-alarm-rule)
