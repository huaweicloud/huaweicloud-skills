# Deploy Event Subscription (Custom Event Source, EG Event Target)

## Application Scenario

EventGrid (EG) event subscription functionality is an event routing and distribution mechanism based on custom event sources, enabling event filtering, transformation, and distribution. Through custom event sources, you can build flexible event-driven architectures, implementing decoupling and asynchronous communication between different systems.

Custom event sources are particularly suitable for scenarios requiring custom event formats, implementing complex event filtering, building event-driven microservices, etc., such as business system integration, real-time data processing, event notification distribution, etc. This best practice will introduce how to use Terraform to automatically deploy a complete event subscription configuration from custom event source to EG event target, including custom event source, custom event channel, and event subscription creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [EventGrid Connections Query Data Source (data.huaweicloud\_eg\_connections)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/eg_connections)

### Resources

- [Custom Event Channel Resource (huaweicloud\_eg\_custom\_event\_channel)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/eg_custom_event_channel)
- [Custom Event Source Resource (huaweicloud\_eg\_custom\_event\_source)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/eg_custom_event_source)
- [Event Subscription Resource (huaweicloud\_eg\_event\_subscription)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/eg_event_subscription)
- [Time Sleep Resource (time\_sleep)](https://registry.terraform.io/providers/hashicorp/time/latest/docs/resources/sleep)

### Resource/Data Source Dependencies

```
data.huaweicloud_eg_connections
    └── huaweicloud_eg_event_subscription

huaweicloud_eg_custom_event_channel
    ├── huaweicloud_eg_custom_event_source
    └── time_sleep
        └── huaweicloud_eg_event_subscription
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create Custom Event Channel

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a custom event channel resource:

```hcl
# Variable definitions for custom event channel
variable "channel_name" {
  description = "The name of the custom event channel"
  type        = string
}

# Create a custom event channel resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_eg_custom_event_channel" "test" {
  name = var.channel_name
}
```

**Parameter Description**:

- **name**: Custom event channel name, assigned by referencing the input variable channel\_name

### 3. Create Custom Event Source

Add the following script to the TF file to instruct Terraform to create a custom event source resource:

```hcl
# Variable definitions for custom event source
variable "source_name" {
  description = "The name of the custom event source"
  type        = string
}

variable "source_type" {
  description = "The type of the custom event source"
  type        = string
  default     = "APPLICATION"
}

# Create a custom event source resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_eg_custom_event_source" "test" {
  channel_id = huaweicloud_eg_custom_event_channel.test.id
  name       = var.source_name
  type       = var.source_type
}
```

**Parameter Description**:

- **channel\_id**: Event channel ID, referencing the ID of the custom event channel resource created earlier
- **name**: Custom event source name, assigned by referencing the input variable source\_name
- **type**: Custom event source type, assigned by referencing the input variable source\_type, default value is "APPLICATION"

### 4. Query EventGrid Connection Information Through Data Source

Add the following script to the TF file to instruct Terraform to query EventGrid connection information:

```hcl
# Variable definitions for connection query
variable "connection_name" {
  description = "The exact name of the connection to be queried"
  type        = string
  default     = "default"
}

# Get all EventGrid connection information that meets specific conditions under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create event subscriptions
data "huaweicloud_eg_connections" "test" {
  name = var.connection_name
}
```

**Parameter Description**:

- **name**: Connection name, assigned by referencing the input variable connection\_name, default value is "default"

### 5. Create Time Sleep Resource

Add the following script to the TF file to instruct Terraform to create a time sleep resource:

```hcl
# Create a time sleep resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to wait for custom event channel to be ready
resource "time_sleep" "test" {
  create_duration = "3s"

  depends_on = [
    huaweicloud_eg_custom_event_channel.test
  ]
}
```

**Parameter Description**:

- **create\_duration**: Wait time, set to "3s" to wait for 3 seconds
- **depends\_on**: Explicit dependency relationship, ensuring custom event channel exists before time sleep resource creation

### 6. Create Event Subscription Resource

Add the following script to the TF file to instruct Terraform to create an event subscription resource:

```hcl
# Variable definitions for event subscription
variable "subscription_name" {
  description = "The name of the event subscription"
  type        = string
}

variable "sources_provider_type" {
  description = "The provider type of the event source"
  type        = string
  default     = "CUSTOM"
}

variable "source_op" {
  description = "The operation of the source"
  type        = string
  default     = "StringIn"
}

variable "targets_name" {
  description = "The name of the event target"
  type        = string
  default     = "HTTPS"
}

variable "targets_provider_type" {
  description = "The type of the event target"
  type        = string
  default     = "CUSTOM"
}

variable "transform" {
  description = "The transform configuration of the event target, in JSON format"
  type        = map(string)
  default     = {
    "type" : "ORIGINAL",
  }
}

variable "detail_name" {
  description = "The name(key) of the target detail configuration"
  type        = string
  default     = "detail"
}

variable "target_url" {
  description = "The target url of the event target"
  type        = string
}

# Create an event subscription resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_eg_event_subscription" "test" {
  channel_id = huaweicloud_eg_custom_event_channel.test.id
  name       = var.subscription_name

  sources {
    name          = huaweicloud_eg_custom_event_channel.test.name
    provider_type = var.sources_provider_type

    filter_rule = jsonencode({
      "source" : [
        {
          "op" : var.source_op,
          "values" : [huaweicloud_eg_custom_event_channel.test.name]
        }
      ]
    })
  }

  targets {
    name          = var.targets_name
    provider_type = var.targets_provider_type
    connection_id = try(data.huaweicloud_eg_connections.test.connections[0].id, "")
    transform     = jsonencode(var.transform)
    detail_name   = var.detail_name
    detail        = jsonencode({
      "url" : var.target_url
    })
  }

  lifecycle {
    ignore_changes = [
      sources, targets
    ]
  }

  depends_on = [
    time_sleep.test
  ]
}
```

**Parameter Description**:

- **channel\_id**: Event channel ID, referencing the ID of the custom event channel resource created earlier
- **name**: Event subscription name, assigned by referencing the input variable subscription\_name
- **sources**: Event source configuration block
  - **name**: Event source name, using the custom event channel name
  - **provider\_type**: Event source provider type, assigned by referencing the input variable sources\_provider\_type, default value is "CUSTOM"
  - **filter\_rule**: Filter rule, configuring event source filter conditions in JSON format
- **targets**: Event target configuration block
  - **name**: Event target name, assigned by referencing the input variable targets\_name, default value is "HTTPS"
  - **provider\_type**: Event target provider type, assigned by referencing the input variable targets\_provider\_type, default value is "CUSTOM"
  - **connection\_id**: Connection ID, using the EventGrid connection query data source connection ID
  - **transform**: Transform configuration, configuring event transformation rules in JSON format
  - **detail\_name**: Target detail configuration name, assigned by referencing the input variable detail\_name, default value is "detail"
  - **detail**: Target detail configuration, configuring target URL and other information in JSON format
- **lifecycle**: Lifecycle management, ignoring changes to sources and targets to avoid rebuilding subscriptions
- **depends\_on**: Explicit dependency relationship, ensuring time sleep resource is completed before event subscription creation

### 7. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Custom event channel configuration
channel_name = "tf_test_channel"

# Custom event source configuration
source_name = "tf-test-source"
source_type = "APPLICATION"

# EventGrid connection configuration
connection_name = "default"

# Event subscription configuration
subscription_name = "tf-test-subscription"
target_url        = "https://test.com/example"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="channel_name=my-channel" -var="source_name=my-source"`
2. Environment variables: `export TF_VAR_channel_name=my-channel`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating event subscription (custom event source)
4. Run `terraform show` to view the details of the created event subscription (custom event source)

## Reference Information

- [Huawei Cloud EventGrid Product Documentation](https://support.huaweicloud.com/eg/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For EventGrid Event Subscription (Custom Event Source, EG Event Target)](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/eg/event-subscriptions/custom)