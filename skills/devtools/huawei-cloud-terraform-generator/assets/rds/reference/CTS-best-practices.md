# Deploy Data Tracker

## Application Scenario

The Data Tracker of Cloud Trace Service (CTS) is a service used to record and store audit logs of cloud resource operations. Through data trackers, you can achieve security audit, compliance monitoring, operation recording, problem troubleshooting, and other functions.

Data trackers are particularly suitable for scenarios that require recording cloud resource operation history, conducting security audits, meeting compliance requirements, etc., such as enterprise-level security monitoring, compliance checks, operation auditing, problem tracking, etc. This best practice will introduce how to use Terraform to automatically deploy a CTS data tracker, implementing automatic recording and storage of cloud resource operations.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

This best practice does not use data sources.

### Resources

- [OBS Bucket Resource (huaweicloud\_obs\_bucket)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket)
- [CTS Data Tracker Resource (huaweicloud\_cts\_data\_tracker)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cts_data_tracker)

### Resource/Data Source Dependencies

```
huaweicloud_obs_bucket
    └── huaweicloud_cts_data_tracker

huaweicloud_obs_bucket
    └── huaweicloud_cts_data_tracker
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create OBS Bucket

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an OBS bucket resource:

```hcl
# Variable definitions for OBS resources
variable "source_bucket_name" {
  description = "The name of the OBS bucket for storing trace files"
  type        = string
}

variable "transfer_bucket_name" {
  description = "The name of the OBS bucket for transferring trace files"
  type        = string
}

# Create a source OBS bucket resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_obs_bucket" "source" {
  bucket        = var.source_bucket_name
  acl           = "private"
  force_destroy = true
}

# Create a transfer OBS bucket resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_obs_bucket" "transfer" {
  bucket        = var.transfer_bucket_name
  acl           = "private"
  force_destroy = true
}
```

**Parameter Description**:

- **bucket**: OBS bucket name, assigned by referencing the input variables source\_bucket\_name and transfer\_bucket\_name
- **acl**: Bucket access control list, set to "private" for private access
- **force\_destroy**: Whether to force delete the bucket, set to true to allow deletion of non-empty buckets

### 3. Create CTS Data Tracker

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CTS data tracker resource:

```hcl
# Variable definitions for CTS resources
variable "tracker_name" {
  description = "The name of the system tracker"
  type        = string
}

variable "tracker_enabled" {
  description = "Whether to enable the system tracker"
  type        = bool
  default     = true
}

variable "tracker_tags" {
  description = "The tags of the system tracker"
  type        = map(string)
  default     = {}
}

variable "trace_object_prefix" {
  description = "The prefix of the trace object in the OBS bucket"
  type        = string
}

variable "trace_file_compression_type" {
  description = "The compression type of the trace file"
  type        = string
  default     = "gzip"
}

variable "is_lts_enabled" {
  description = "Whether to enable the trace analysis for LTS service"
  type        = bool
  default     = true
}

# Create a CTS data tracker resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_cts_data_tracker" "test" {
  depends_on = [
    huaweicloud_obs_bucket.source,
    huaweicloud_obs_bucket.transfer,
  ]

  name          = var.tracker_name
  enabled       = var.tracker_enabled
  tags          = var.tracker_tags
  data_bucket   = huaweicloud_obs_bucket.source.bucket
  bucket_name   = huaweicloud_obs_bucket.transfer.bucket
  file_prefix   = var.trace_object_prefix
  compress_type = var.trace_file_compression_type
  lts_enabled   = var.is_lts_enabled
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency relationship, ensuring OBS buckets exist before creating the data tracker
- **name**: Data tracker name, assigned by referencing the input variable tracker\_name
- **enabled**: Whether to enable the data tracker, assigned by referencing the input variable tracker\_enabled, default value true means enabled
- **tags**: Data tracker tags, assigned by referencing the input variable tracker\_tags, used for resource classification and management
- **data\_bucket**: OBS bucket name for storing trace data, assigned by referencing the source OBS bucket's bucket attribute
- **bucket\_name**: OBS bucket name for transferring trace data, assigned by referencing the transfer OBS bucket's bucket attribute
- **file\_prefix**: Prefix of trace objects in the OBS bucket, assigned by referencing the input variable trace\_object\_prefix
- **compress\_type**: Compression type of trace files, assigned by referencing the input variable trace\_file\_compression\_type, default value "gzip" means using gzip compression
- **lts\_enabled**: Whether to enable trace analysis for LTS service, assigned by referencing the input variable is\_lts\_enabled, default value true means enabled

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# OBS bucket configuration
source_bucket_name   = "tf-test-source-bucket"
transfer_bucket_name = "tf-test-transfer-bucket"

# CTS data tracker configuration
tracker_name         = "tf-test-tracker"
trace_object_prefix  = "tf_test"
tracker_tags         = {
  "owner" = "terraform"
}
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="tracker_name=my-tracker" -var="source_bucket_name=my-bucket"`
2. Environment variables: `export TF_VAR_tracker_name=my-tracker`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating OBS buckets and CTS data tracker
4. Run `terraform show` to view the details of the created OBS buckets and CTS data tracker

## Reference Information

- [Huawei Cloud CTS Product Documentation](https://support.huaweicloud.com/cts/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For CTS Data Tracker](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/cts/data-tracker)

# Deploy Notification

## Application Scenario

The notification function of Cloud Trace Service (CTS) is an event-driven alert mechanism that can monitor cloud resource operations and send real-time notifications. Through CTS notifications, you can achieve security monitoring, abnormal alerting, operation auditing, real-time notification, and other functions.

CTS notifications are particularly suitable for scenarios that require real-time monitoring of cloud resource operations, conducting security alerting, implementing automated responses, etc., such as security event monitoring, abnormal operation alerting, compliance checks, operation automation, etc. This best practice will introduce how to use Terraform to automatically deploy a CTS notification configuration, implementing real-time monitoring and notification of cloud resource operations.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

This best practice does not use data sources.

### Resources

- [SMN Topic Resource (huaweicloud\_smn\_topic)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_topic)
- [CTS Notification Resource (huaweicloud\_cts\_notification)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cts_notification)

### Resource/Data Source Dependencies

```
huaweicloud_smn_topic
    └── huaweicloud_cts_notification
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create SMN Topic

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an SMN topic resource:

```hcl
# Variable definitions for SMN resources
variable "topic_name" {
  description = "The name of the SMN topic"
  type        = string
}

# Create an SMN topic resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_smn_topic" "test" {
  name = var.topic_name
}
```

**Parameter Description**:

- **name**: SMN topic name, assigned by referencing the input variable topic\_name

### 3. Create CTS Notification

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CTS notification resource:

```hcl
# Variable definitions for CTS resources
variable "notification_name" {
  description = "The name of the CTS notification"
  type        = string
}

variable "notification_operation_type" {
  description = "The type of operation"
  type        = string
  default     = "customized"
}

variable "notification_agency_name" {
  description = "The name of the IAM agency which allows CTS to access the SMN resources"
  type        = string
}

variable "notification_filter" {
  description = "The filter of the notification"
  type        = list(object({
    condition = string
    rule      = list(string)
  }))
  default  = []
  nullable = false
}

variable "notification_operations" {
  description = "The operations of the notification"
  type        = list(object({
    service     = string
    resource    = string
    trace_names = list(string)
  }))
  default  = []
  nullable = false
}

variable "notification_operation_users" {
  description = "The operation users of the notification"
  type        = list(object({
    group = string
    users = list(string)
  }))
  default  = []
  nullable = false
}

# Create a CTS notification resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_cts_notification" "test" {
  name           = var.notification_name
  operation_type = var.notification_operation_type
  smn_topic      = huaweicloud_smn_topic.test.id
  agency_name    = var.notification_agency_name

  dynamic "filter" {
    for_each = var.notification_filter

    content {
      condition = filter.value.condition
      rule      = filter.value.rule
    }
  }

  dynamic "operations" {
    for_each = var.notification_operations

    content {
      service     = operations.value.service
      resource    = operations.value.resource
      trace_names = operations.value.trace_names
    }
  }

  dynamic "operation_users" {
    for_each = var.notification_operation_users

    content {
      group = operation_users.value.group
      users = operation_users.value.users
    }
  }
}
```

**Parameter Description**:

- **name**: CTS notification name, assigned by referencing the input variable notification\_name
- **operation\_type**: Operation type, assigned by referencing the input variable notification\_operation\_type, default value "customized" means custom operations
- **smn\_topic**: Associated SMN topic ID, assigned by referencing huaweicloud\_smn\_topic.test.id
- **agency\_name**: IAM agency name that allows CTS to access SMN resources, assigned by referencing the input variable notification\_agency\_name
- **filter**: Notification filter, created using dynamic blocks, containing the following parameters:
  - **condition**: Filter condition, supports logical operators like "AND", "OR"
  - **rule**: Filter rule list, supports filtering based on status code, resource name, API version, etc.
- **operations**: Monitored operations, created using dynamic blocks, containing the following parameters:
  - **service**: Cloud service name, such as "ECS", "VPC", etc.
  - **resource**: Resource type, such as "ecs", "vpc", etc.
  - **trace\_names**: List of tracked operation names, such as "createServer", "deleteServer", etc.
- **operation\_users**: Operation users, created using dynamic blocks, containing the following parameters:
  - **group**: User group name
  - **users**: List of user names

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# SMN topic configuration
topic_name = "tf_test_topic"

# CTS notification configuration
notification_name        = "tf_test_notification"
notification_agency_name = "cts_admin_trust"

# Notification filter configuration
notification_filter = [
  {
    condition = "OR"
    rule      = [
      "code = 400",
      "resource_name = name",
      "api_version = 1.0",
    ]
  }
]

# Monitored operations configuration
notification_operations = [
  {
    service     = "ECS"
    resource    = "ecs"
    trace_names = [
      "createServer",
      "deleteServer",
    ]
  }
]

# Operation users configuration
notification_operation_users = [
  {
    group = "devops"
    users = [
      "your_operation_user_name",
    ]
  }
]
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="notification_name=my-notification" -var="topic_name=my-topic"`
2. Environment variables: `export TF_VAR_notification_name=my-notification`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating SMN topic and CTS notification
4. Run `terraform show` to view the details of the created SMN topic and CTS notification

## Reference Information

- [Huawei Cloud CTS Product Documentation](https://support.huaweicloud.com/cts/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For CTS Notification](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/cts/notification)

# Deploy System Tracker

## Application Scenario

The System Tracker of Cloud Trace Service (CTS) is a core service used to record and store audit logs of cloud resource operations. Through system trackers, you can achieve security audit, compliance monitoring, operation recording, problem troubleshooting, and other functions.

System trackers are particularly suitable for scenarios that require recording cloud resource operation history, conducting security audits, meeting compliance requirements, etc., such as enterprise-level security monitoring, compliance checks, operation auditing, problem tracking, etc. This best practice will introduce how to use Terraform to automatically deploy a CTS system tracker, implementing automatic recording and storage of cloud resource operations.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

This best practice does not use data sources.

### Resources

- [OBS Bucket Resource (huaweicloud\_obs\_bucket)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket)
- [CTS System Tracker Resource (huaweicloud\_cts\_tracker)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cts_tracker)

### Resource/Data Source Dependencies

```
huaweicloud_obs_bucket
    └── huaweicloud_cts_tracker
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create OBS Bucket

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an OBS bucket resource:

```hcl
# Variable definitions for OBS resources
variable "bucket_name" {
  description = "The name of the OBS bucket for storing trace files"
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
- **acl**: Bucket access control list, set to "private" for private access
- **force\_destroy**: Whether to force delete the bucket, set to true to allow deletion of non-empty buckets

### 3. Create CTS System Tracker

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CTS system tracker resource:

```hcl
# Variable definitions for CTS resources
variable "tracker_enabled" {
  description = "Whether to enable the system tracker"
  type        = bool
  default     = true
}

variable "tracker_tags" {
  description = "The tags of the system tracker"
  type        = map(string)
  default     = {}
}

variable "is_system_tracker_delete" {
  description = "Whether to delete the system tracker when the tracker resource is deleted"
  type        = bool
  default     = true
}

variable "trace_object_prefix" {
  description = "The prefix of the trace object in the OBS bucket"
  type        = string
}

variable "trace_file_compression_type" {
  description = "The compression type of the trace file"
  type        = string
  default     = "gzip"
}

variable "is_lts_enabled" {
  description = "Whether to enable the trace analysis for LTS service"
  type        = bool
  default     = true
}

# Create a CTS system tracker resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_cts_tracker" "test" {
  enabled        = var.tracker_enabled
  tags           = var.tracker_tags
  delete_tracker = var.is_system_tracker_delete
  bucket_name    = huaweicloud_obs_bucket.test.bucket
  file_prefix    = var.trace_object_prefix
  compress_type  = var.trace_file_compression_type
  lts_enabled    = var.is_lts_enabled
}
```

**Parameter Description**:

- **enabled**: Whether to enable the system tracker, assigned by referencing the input variable tracker\_enabled, default value true means enabled
- **tags**: System tracker tags, assigned by referencing the input variable tracker\_tags, used for resource classification and management
- **delete\_tracker**: Whether to delete the system tracker when the tracker resource is deleted, assigned by referencing the input variable is\_system\_tracker\_delete, default value true means delete
- **bucket\_name**: OBS bucket name for storing trace data, assigned by referencing the OBS bucket's bucket attribute
- **file\_prefix**: Prefix of trace objects in the OBS bucket, assigned by referencing the input variable trace\_object\_prefix
- **compress\_type**: Compression type of trace files, assigned by referencing the input variable trace\_file\_compression\_type, default value "gzip" means using gzip compression
- **lts\_enabled**: Whether to enable trace analysis for LTS service, assigned by referencing the input variable is\_lts\_enabled, default value true means enabled

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# OBS bucket configuration
bucket_name = "tf-test-trace-bucket"

# CTS system tracker configuration
trace_object_prefix = "tf_test"
tracker_tags        = {
  "owner" = "terraform"
}
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="bucket_name=my-bucket" -var="trace_object_prefix=my-prefix"`
2. Environment variables: `export TF_VAR_bucket_name=my-bucket`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating OBS bucket and CTS system tracker
4. Run `terraform show` to view the details of the created OBS bucket and CTS system tracker

## Reference Information

- [Huawei Cloud CTS Product Documentation](https://support.huaweicloud.com/cts/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For CTS System Tracker](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/cts/system-tracker)
