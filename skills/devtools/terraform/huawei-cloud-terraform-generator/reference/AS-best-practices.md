# Deploy Alarm Policy

## Application Scenario

Huawei Cloud Auto Scaling service is a service that automatically adjusts computing resources, capable of automatically adjusting the number of elastic computing instances based on business needs and policies. Alarm policy is an automatic scaling policy based on monitoring metrics. By configuring CES (Cloud Eye Service) alarm rules, when monitoring metrics reach the set threshold, scaling policies are automatically triggered to perform scaling operations. This best practice will introduce how to use Terraform to automatically deploy alarm policies, including the creation of VPC network, security groups, key pairs, AS configuration, AS group, SMN topic, CES alarm rules, and alarm policies.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [Compute Flavors Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [Images Query Data Source (data.huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Key Pair Resource (huaweicloud\_kps\_keypair)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/kps_keypair)
- [AS Configuration Resource (huaweicloud\_as\_configuration)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/as_configuration)
- [AS Group Resource (huaweicloud\_as\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/as_group)
- [SMN Topic Resource (huaweicloud\_smn\_topic)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_topic)
- [CES Alarm Rule Resource (huaweicloud\_ces\_alarmrule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/ces_alarmrule)
- [AS Policy Resource (huaweicloud\_as\_policy)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/as_policy)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── data.huaweicloud_compute_flavors
        └── data.huaweicloud_images_images
            └── huaweicloud_as_configuration

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_as_group

huaweicloud_networking_secgroup
    └── huaweicloud_as_group

huaweicloud_kps_keypair
    └── huaweicloud_as_configuration

huaweicloud_as_configuration
    └── huaweicloud_as_group
        ├── huaweicloud_ces_alarmrule
        └── huaweicloud_as_policy

huaweicloud_smn_topic
    └── huaweicloud_ces_alarmrule
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration introduction, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy).

### 2. Query Availability Zones Required for Alarm Policy Resource Creation Through Data Source

Add the following script to the TF file (such as main.tf) to inform Terraform to perform a data source query, the query results are used to create alarm policy related resources:

```hcl
variable "instance_flavor_id" {
  description = "The flavor ID of the AS instance"
  type        = string
  default     = ""
}

variable "instance_flavor_performance_type" {
  description = "The performance type of the AS instance flavor"
  type        = string
  default     = "normal"
}

variable "instance_flavor_cpu_core_count" {
  description = "The CPU core count of the AS instance flavor"
  type        = number
  default     = 2
}

variable "instance_flavor_memory_size" {
  description = "The memory size of the AS instance flavor"
  type        = number
  default     = 4
}

# Get all availability zone information in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating alarm policy related resources
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**: This data source does not require additional parameters and queries all available availability zone information in the current region by default.

### 3. Query Instance Flavors Required for Alarm Policy Resource Creation Through Data Source

Add the following script to the TF file to inform Terraform to query instance flavors that meet the conditions:

```hcl
# Get all instance flavor information that meets specific conditions in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating alarm policy related resources
data "huaweicloud_compute_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  availability_zone = try(data.huaweicloud_availability_zones.test.names[0], null)
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}
```

**Parameter Description**:

- **count**: The number of data source creations, used to control whether to execute the instance flavor list query, only when `var.instance_flavor_id` is empty, the data source is created (i.e., execute the instance flavor list query)
- **availability\_zone**: The availability zone where the instance flavor is located, using the first availability zone from the availability zone list query data source
- **performance\_type**: Performance type, assigned through input variable `instance_flavor_performance_type`, default is "normal" for standard type
- **cpu\_core\_count**: CPU core count, assigned through input variable `instance_flavor_cpu_core_count`
- **memory\_size**: Memory size (GB), assigned through input variable `instance_flavor_memory_size`

### 4. Query Images Required for Alarm Policy Resource Creation Through Data Source

Add the following script to the TF file to inform Terraform to query images that meet the conditions:

```hcl
variable "instance_image_id" {
  description = "The image ID of the AS instance"
  type        = string
  default     = ""
}

# Get all image information that meets specific conditions in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating alarm policy related resources
data "huaweicloud_images_images" "test" {
  count = var.instance_image_id == "" ? 1 : 0

  flavor_id  = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_compute_flavors.test[0].ids[0], null)
  visibility = "public"
  os         = "Ubuntu"
}
```

**Parameter Description**:

- **count**: The number of data source creations, used to control whether to execute the image list query, only when `var.instance_image_id` is empty, the data source is created (i.e., execute the image list query)
- **flavor\_id**: The flavor ID supported by the image, if the instance flavor ID is specified, use that ID, otherwise use the first flavor ID from the instance flavor list query data source
- **visibility**: Image visibility, set to "public" for public images
- **os**: Operating system type, set to "Ubuntu"

### 5. Create VPC Resource

Add the following script to the TF file to inform Terraform to create VPC resources:

```hcl
variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
  default     = "192.168.0.0/16"
}

# Create VPC resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing network environment for AS group
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: The name of the VPC, assigned by referencing input variable `vpc_name`
- **cidr**: The CIDR block of the VPC, assigned by referencing input variable `vpc_cidr`, default is "192.168.0.0/16"

### 6. Create VPC Subnet Resource

Add the following script to the TF file to inform Terraform to create VPC subnet resources:

```hcl
variable "subnet_name" {
  description = "The name of the subnet"
  type        = string
}

variable "subnet_cidr" {
  description = "The CIDR block of the subnet"
  type        = string
  default     = ""
}

variable "subnet_gateway_ip" {
  description = "The gateway IP of the subnet"
  type        = string
  default     = ""

  validation {
    condition     = (var.subnet_cidr != "" && var.subnet_gateway_ip != "") || (var.subnet_cidr == "" && var.subnet_gateway_ip == "")
    error_message = "The 'subnet_cidr' and 'subnet_gateway_ip' is not allowed for only one of them to be empty"
  }
}

# Create VPC subnet resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing network environment for AS group
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr != "" ? var.subnet_cidr : cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0)
  gateway_ip = var.subnet_gateway_ip != "" ? var.subnet_gateway_ip : cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1)
}
```

**Parameter Description**:

- **vpc\_id**: The VPC ID to which the subnet belongs, assigned by referencing the ID of the VPC resource (huaweicloud\_vpc.test)
- **name**: The name of the subnet, assigned by referencing input variable `subnet_name`
- **cidr**: The CIDR block of the subnet, if the subnet CIDR is specified, use that value, otherwise automatically calculate based on the VPC's CIDR block using the `cidrsubnet` function
- **gateway\_ip**: The gateway IP of the subnet, if the gateway IP is specified, use that value, otherwise automatically calculate based on the subnet CIDR using the `cidrhost` function

### 7. Create Security Group Resource

Add the following script to the TF file to inform Terraform to create security group resources:

```hcl
variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create security group resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing security protection for AS group
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: The name of the security group, assigned by referencing input variable `security_group_name`
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default rules

### 8. Create Key Pair Resource

Add the following script to the TF file to inform Terraform to create key pair resources:

```hcl
variable "keypair_name" {
  description = "The name of the key pair that is used to access the AS instance"
  type        = string
}

variable "keypair_public_key" {
  description = "The public key of the key pair that is used to access the AS instance"
  type        = string
  default     = ""
}

# Create key pair resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for accessing AS instances
resource "huaweicloud_kps_keypair" "test" {
  name       = var.keypair_name
  public_key = var.keypair_public_key != "" ? var.keypair_public_key : null
}
```

**Parameter Description**:

- **name**: The name of the key pair, assigned by referencing input variable `keypair_name`
- **public\_key**: The public key of the key pair, if the public key is specified, use that value, otherwise set to null (the system will automatically generate a key pair)

### 9. Create AS Configuration Resource

Add the following script to the TF file to inform Terraform to create AS configuration resources:

```hcl
variable "configuration_name" {
  description = "The name of the AS configuration"
  type        = string
}

variable "disk_configurations" {
  description = "The disk configurations for the AS instance"
  type = list(object({
    disk_type   = string
    volume_type = string
    volume_size = number
  }))

  nullable = false

  validation {
    condition     = length(var.disk_configurations) > 0 && length([for v in var.disk_configurations : v if v.disk_type == "SYS"]) == 1
    error_message = "The 'disk_configurations' is not allowed to be empty and only one system disk is allowed"
  }
}

# Create AS configuration resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for defining templates for AS instances
resource "huaweicloud_as_configuration" "test" {
  scaling_configuration_name = var.configuration_name

  instance_config {
    image    = var.instance_image_id != "" ? var.instance_image_id : try(data.huaweicloud_images_images.test[0].images[0].id, null)
    flavor   = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null)
    key_name = huaweicloud_kps_keypair.test.id

    dynamic "disk" {
      for_each = var.disk_configurations

      content {
        disk_type   = disk.value.disk_type
        volume_type = disk.value.volume_type
        size        = disk.value.volume_size
      }
    }
  }
}
```

**Parameter Description**:

- **scaling\_configuration\_name**: The name of the AS configuration, assigned by referencing input variable `configuration_name`
- **instance\_config**: Instance configuration block, defines the configuration for AS instances
  - **image**: Instance image ID, if the image ID is specified, use that value, otherwise use the first image ID from the image list query data source
  - **flavor**: Instance flavor ID, if the flavor ID is specified, use that value, otherwise use the first flavor ID from the instance flavor list query data source
  - **key\_name**: Key pair ID, assigned by referencing the ID of the key pair resource (huaweicloud\_kps\_keypair.test)
  - **disk**: Disk configuration block, creates multiple disk configurations through dynamic block (dynamic block) based on input variable `disk_configurations`
    - **disk\_type**: Disk type, assigned through `disk_type` in input variable `disk_configurations`
    - **volume\_type**: Volume type, assigned through `volume_type` in input variable `disk_configurations`
    - **size**: Disk size (GB), assigned through `volume_size` in input variable `disk_configurations`

> Note: The disk configuration must include exactly one system disk (disk\_type is "SYS"), and other disks are data disks.

### 10. Create AS Group Resource

Add the following script to the TF file to inform Terraform to create AS group resources:

```hcl
variable "group_name" {
  description = "The name of the AS group"
  type        = string
}

variable "desire_instance_number" {
  description = "The desired number of scaling instances in the AS group"
  type        = number
  default     = 2
}

variable "min_instance_number" {
  description = "The minimum number of scaling instances in the AS group"
  type        = number
  default     = 0
}

variable "max_instance_number" {
  description = "The maximum number of scaling instances in the AS group"
  type        = number
  default     = 10
}

variable "is_delete_publicip" {
  description = "Whether to delete the public IP address of the scaling instances when the AS group is deleted"
  type        = bool
  default     = true
}

variable "is_delete_instances" {
  description = "Whether to delete the scaling instances when the AS group is deleted"
  type        = bool
  default     = true
}

# Create AS group resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for managing AS instances
resource "huaweicloud_as_group" "test" {
  scaling_configuration_id = huaweicloud_as_configuration.test.id
  vpc_id                   = huaweicloud_vpc.test.id
  scaling_group_name       = var.group_name
  desire_instance_number   = var.desire_instance_number
  min_instance_number      = var.min_instance_number
  max_instance_number      = var.max_instance_number
  delete_publicip          = var.is_delete_publicip
  delete_instances         = var.is_delete_instances ? "yes" : "no"

  networks {
    id = huaweicloud_vpc_subnet.test.id
  }

  security_groups {
    id = huaweicloud_networking_secgroup.test.id
  }
}
```

**Parameter Description**:

- **scaling\_configuration\_id**: AS configuration ID, assigned by referencing the ID of the AS configuration resource (huaweicloud\_as\_configuration.test)
- **vpc\_id**: VPC ID, assigned by referencing the ID of the VPC resource (huaweicloud\_vpc.test)
- **scaling\_group\_name**: The name of the AS group, assigned by referencing input variable `group_name`
- **desire\_instance\_number**: The desired number of AS instances, assigned by referencing input variable `desire_instance_number`
- **min\_instance\_number**: The minimum number of AS instances, assigned by referencing input variable `min_instance_number`
- **max\_instance\_number**: The maximum number of AS instances, assigned by referencing input variable `max_instance_number`
- **delete\_publicip**: Whether to delete the public IP address of AS instances when the AS group is deleted, assigned by referencing input variable `is_delete_publicip`
- **delete\_instances**: Whether to delete AS instances when the AS group is deleted, assigned by referencing input variable `is_delete_instances`, value is "yes" or "no"
- **networks**: Network configuration block, defines the subnet used by the AS group
  - **id**: Subnet ID, assigned by referencing the ID of the VPC subnet resource (huaweicloud\_vpc\_subnet.test)
- **security\_groups**: Security group configuration block, defines the security group used by the AS group
  - **id**: Security group ID, assigned by referencing the ID of the security group resource (huaweicloud\_networking\_secgroup.test)

### 11. Create SMN Topic Resource

Add the following script to the TF file to inform Terraform to create SMN topic resources:

```hcl
variable "topic_name" {
  description = "The name of the SMN topic"
  type        = string
}

# Create SMN topic resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for receiving alarm notifications
resource "huaweicloud_smn_topic" "test" {
  name = var.topic_name
}
```

**Parameter Description**:

- **name**: The name of the SMN topic, assigned by referencing input variable `topic_name`

### 12. Create CES Alarm Rule Resource

Add the following script to the TF file to inform Terraform to create CES alarm rule resources:

```hcl
variable "alarm_rule_name" {
  description = "The name of the CES alarm rule"
  type        = string
}

variable "rule_conditions" {
  description = "The conditions of the alarm rule"
  type = list(object({
    alarm_level         = optional(number, 2)
    metric_name         = string
    period              = number
    filter              = string
    comparison_operator = string
    suppress_duration   = optional(number, 0)
    value               = number
    count               = number
  }))

  nullable = false

  validation {
    condition     = length(var.rule_conditions) > 0
    error_message = "The 'rule_conditions' is not allowed to be empty"
  }
}

# Create CES alarm rule resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for monitoring AS group metrics and triggering alarms
resource "huaweicloud_ces_alarmrule" "test" {
  alarm_name = var.alarm_rule_name

  metric {
    namespace = "SYS.AS"
  }

  resources {
    dimensions {
      name  = "AutoScalingGroup"
      value = huaweicloud_as_group.test.id
    }
  }

  dynamic "condition" {
    for_each = var.rule_conditions

    content {
      alarm_level         = condition.value.alarm_level
      metric_name         = condition.value.metric_name
      period              = condition.value.period
      filter              = condition.value.filter
      comparison_operator = condition.value.comparison_operator
      suppress_duration   = condition.value.suppress_duration
      value               = condition.value.value
      count               = condition.value.count
    }
  }

  alarm_actions {
    type              = "autoscaling"
    notification_list = [huaweicloud_smn_topic.test.id]
  }
}
```

**Parameter Description**:

- **alarm\_name**: The name of the alarm rule, assigned by referencing input variable `alarm_rule_name`
- **metric**: Monitoring metric configuration block
  - **namespace**: Namespace, set to "SYS.AS" for Auto Scaling service monitoring metrics
- **resources**: Monitoring resource configuration block
  - **dimensions**: Dimension configuration block, defines dimension information of monitoring resources
    - **name**: Dimension name, set to "AutoScalingGroup" for monitoring AS group
    - **value**: Dimension value, assigned by referencing the ID of the AS group resource (huaweicloud\_as\_group.test)
- **condition**: Alarm condition configuration block, creates multiple alarm conditions through dynamic block (dynamic block) based on input variable `rule_conditions`
  - **alarm\_level**: Alarm level, assigned through `alarm_level` in input variable `rule_conditions`, default is 2 (important)
  - **metric\_name**: Monitoring metric name, assigned through `metric_name` in input variable `rule_conditions`, for example "cpu\_util" for CPU utilization
  - **period**: Monitoring period (seconds), assigned through `period` in input variable `rule_conditions`
  - **filter**: Aggregation method, assigned through `filter` in input variable `rule_conditions`, for example "average" for average value
  - **comparison\_operator**: Comparison operator, assigned through `comparison_operator` in input variable `rule_conditions`, for example ">" for greater than
  - **suppress\_duration**: Suppression duration (seconds), assigned through `suppress_duration` in input variable `rule_conditions`, default is 0
  - **value**: Threshold, assigned through `value` in input variable `rule_conditions`
  - **count**: Continuous trigger count, assigned through `count` in input variable `rule_conditions`
- **alarm\_actions**: Alarm action configuration block
  - **type**: Action type, set to "autoscaling" for triggering Auto Scaling
  - **notification\_list**: Notification list, assigned by referencing the ID of the SMN topic resource (huaweicloud\_smn\_topic.test)

### 13. Create AS Scaling Policy Resources

Add the following script to the TF file to inform Terraform to create AS scaling policy resources:

```hcl
variable "scaling_up_policy_name" {
  description = "The name of the scaling up policy"
  type        = string
}

variable "scaling_up_cool_down_time" {
  description = "The cool down time of the scaling up policy"
  type        = number
  default     = 300
}

variable "scaling_up_instance_number" {
  description = "The number of instances to add when the scaling up policy is triggered"
  type        = number
  default     = 1
}

variable "scaling_down_policy_name" {
  description = "The name of the scaling down policy"
  type        = string
}

variable "scaling_down_cool_down_time" {
  description = "The cool down time of the scaling down policy"
  type        = number
  default     = 300
}

variable "scaling_down_instance_number" {
  description = "The number of instances to remove when the scaling down policy is triggered"
  type        = number
  default     = 1
}

# Create AS scaling up policy resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for automatically scaling up when alarm is triggered
resource "huaweicloud_as_policy" "scaling_up" {
  scaling_policy_name = var.scaling_up_policy_name
  scaling_policy_type = "ALARM"
  scaling_group_id    = huaweicloud_as_group.test.id
  alarm_id            = huaweicloud_ces_alarmrule.test.id
  cool_down_time      = var.scaling_up_cool_down_time

  scaling_policy_action {
    operation       = "ADD"
    instance_number = var.scaling_up_instance_number
  }
}

# Create AS scaling down policy resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for automatically scaling down when alarm is triggered
resource "huaweicloud_as_policy" "scaling_down" {
  scaling_policy_name = var.scaling_down_policy_name
  scaling_policy_type = "ALARM"
  scaling_group_id    = huaweicloud_as_group.test.id
  alarm_id            = huaweicloud_ces_alarmrule.test.id
  cool_down_time      = var.scaling_down_cool_down_time

  scaling_policy_action {
    operation       = "REMOVE"
    instance_number = var.scaling_down_instance_number
  }
}
```

**Parameter Description** (Scaling Up Policy):

- **scaling\_policy\_name**: The name of the scaling up policy, assigned by referencing input variable `scaling_up_policy_name`
- **scaling\_policy\_type**: Policy type, set to "ALARM" for alarm-based policy
- **scaling\_group\_id**: AS group ID, assigned by referencing the ID of the AS group resource (huaweicloud\_as\_group.test)
- **alarm\_id**: Alarm rule ID, assigned by referencing the ID of the CES alarm rule resource (huaweicloud\_ces\_alarmrule.test)
- **cool\_down\_time**: Cool down time (seconds), assigned by referencing input variable `scaling_up_cool_down_time`, default is 300 seconds
- **scaling\_policy\_action**: Policy action configuration block
  - **operation**: Operation type, set to "ADD" for adding instances
  - **instance\_number**: Instance count, assigned by referencing input variable `scaling_up_instance_number`, indicates the number of instances to add each time when scaling up

**Parameter Description** (Scaling Down Policy):

- **scaling\_policy\_name**: The name of the scaling down policy, assigned by referencing input variable `scaling_down_policy_name`
- **scaling\_policy\_type**: Policy type, set to "ALARM" for alarm-based policy
- **scaling\_group\_id**: AS group ID, assigned by referencing the ID of the AS group resource (huaweicloud\_as\_group.test)
- **alarm\_id**: Alarm rule ID, assigned by referencing the ID of the CES alarm rule resource (huaweicloud\_ces\_alarmrule.test)
- **cool\_down\_time**: Cool down time (seconds), assigned by referencing input variable `scaling_down_cool_down_time`, default is 300 seconds
- **scaling\_policy\_action**: Policy action configuration block
  - **operation**: Operation type, set to "REMOVE" for removing instances
  - **instance\_number**: Instance count, assigned by referencing input variable `scaling_down_instance_number`, indicates the number of instances to remove each time when scaling down

### 14. Preset Input Parameters Required for Resource Deployment

In this practice, some resources and data sources use input variables to assign configuration content, and these input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory, example content is as follows:

```hcl
vpc_name            = "tf_test_vpc"
subnet_name         = "tf_test_subnet"
security_group_name = "tf_test_security_group"
keypair_name        = "tf_test_keypair"
configuration_name  = "tf_test_configuration"

disk_configurations = [
  {
    disk_type   = "SYS"
    volume_type = "SSD"
    volume_size = 40
  }
]

group_name      = "tf_test_group"
topic_name      = "tf_test_topic"
alarm_rule_name = "tf_test_alarm_rule"

rule_conditions = [
  {
    metric_name         = "cpu_util"
    period              = 300
    filter              = "average"
    comparison_operator = ">"
    value               = 80
    count               = 1
  }
]

scaling_up_policy_name   = "tf_test_scaling_up_policy"
scaling_down_policy_name = "tf_test_scaling_down_policy"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content in the `tfvars` file when executing terraform commands, other naming requires adding `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify the parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="subnet_name=my-subnet"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 15. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating alarm policies
4. Run `terraform show` to view the created alarm policies

## Reference Information

- [Huawei Cloud Auto Scaling Product Documentation](https://support.huaweicloud.com/as/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [AS Alarm Policy Best Practice Source Code Reference](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/as/alarm-policy)

# Deploy Scaling Configuration

## Application Scenario

Huawei Cloud Auto Scaling service is a service that automatically adjusts computing resources, capable of automatically adjusting the number of elastic computing instances based on business needs and policies. By configuring a scaling configuration, you can define templates for elastic scaling instances, including image, specification, security group, and other configurations, providing a foundation for subsequent scaling group creation. This best practice will introduce how to use Terraform to automatically deploy a scaling configuration, including the creation of security groups, key pairs, and scaling configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [Image Query Data Source (data.huaweicloud\_images\_image)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_image)
- [Compute Flavors Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)

### Resources

- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Key Pair Resource (huaweicloud\_kps\_keypair)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/kps_keypair)
- [AS Configuration Resource (huaweicloud\_as\_configuration)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/as_configuration)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── data.huaweicloud_compute_flavors
        └── huaweicloud_as_configuration

data.huaweicloud_images_image
    └── huaweicloud_as_configuration

huaweicloud_networking_secgroup
    └── huaweicloud_as_configuration

huaweicloud_kps_keypair
    └── huaweicloud_as_configuration
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration introduction, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy).

### 2. Query Availability Zones Required for Scaling Configuration Resource Creation Through Data Source

Add the following script to the TF file (such as main.tf) to inform Terraform to perform a data source query, the query results are used to create scaling configuration:

```hcl
# Get all availability zone information in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating scaling configuration
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**: This data source does not require additional parameters and queries all available availability zone information in the current region by default.

### 3. Query Images Required for Scaling Configuration Resource Creation Through Data Source

Add the following script to the TF file to inform Terraform to query images that meet the conditions:

```hcl
# Get all image information that meets specific conditions in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating scaling configuration
data "huaweicloud_images_image" "test" {
  name        = "Ubuntu 18.04 server 64bit"
  visibility  = "public"
  most_recent = true
}
```

**Parameter Description**:

- **name**: Image name, set to "Ubuntu 18.04 server 64bit"
- **visibility**: Image visibility, set to "public" for public images
- **most\_recent**: Whether to use the latest version of the image, set to true to use the latest version

### 4. Query Instance Flavors Required for Scaling Configuration Resource Creation Through Data Source

Add the following script to the TF file to inform Terraform to query instance flavors that meet the conditions:

```hcl
# Get all instance flavor information that meets specific conditions in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating scaling configuration
data "huaweicloud_compute_flavors" "test" {
  availability_zone = data.huaweicloud_availability_zones.test.names[0]
  performance_type  = "normal"
  cpu_core_count    = 2
  memory_size       = 4
}
```

**Parameter Description**:

- **availability\_zone**: Availability zone where the instance flavor is located, using the first availability zone from the availability zone list query data source
- **performance\_type**: Performance type, set to "normal" for standard type
- **cpu\_core\_count**: CPU core count, set to 2 cores
- **memory\_size**: Memory size (GB), set to 4GB

### 5. Create Security Group Resource

Add the following script to the TF file to inform Terraform to create security group resources:

```hcl
# Create security group resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for deploying scaling configuration
resource "huaweicloud_networking_secgroup" "test" {
  name                 = "test-secgroup-demo"
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: Security group name, set to "test-secgroup-demo"
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default rules

### 6. Create Key Pair Resource

Add the following script to the TF file to inform Terraform to create key pair resources:

```hcl
variable "public_key" {
  description = "The public key for the keypair"
  type        = string
}

# Create key pair resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for deploying scaling configuration
resource "huaweicloud_kps_keypair" "acc_key" {
  name       = "test-keypair-demo"
  public_key = var.public_key
}
```

**Parameter Description**:

- **name**: Key pair name, set to "test-keypair-demo"
- **public\_key**: Public key content, assigned by referencing input variable public\_key

### 7. Create Scaling Configuration Resource

Add the following script to the TF file to inform Terraform to create scaling configuration resources:

```hcl
# Create scaling configuration resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing)
resource "huaweicloud_as_configuration" "acc_as_config" {
  scaling_configuration_name = "test-as-configuration-demo"
  instance_config {
    image              = data.huaweicloud_images_image.test.id
    flavor             = data.huaweicloud_compute_flavors.test.ids[0]
    key_name           = huaweicloud_kps_keypair.acc_key.id
    security_group_ids = [huaweicloud_networking_secgroup.test.id]

    metadata = {
      some_key = "some_value"
    }
    user_data = <<EOT
#!/bin/sh
echo "Hello World! The time is now $(date -R)!" | tee /root/output.txt
EOT

    disk {
      size        = 40
      volume_type = "SSD"
      disk_type   = "SYS"
    }

    public_ip {
      eip {
        ip_type = "5_bgp"
        bandwidth {
          size          = 10
          share_type    = "PER"
          charging_mode = "traffic"
        }
      }
    }
  }
}
```

**Parameter Description**:

- **scaling\_configuration\_name**: Scaling configuration name, set to "test-as-configuration-demo"
- **instance\_config**: Instance configuration block
  - **image**: Image ID, using the ID from the image query data source
  - **flavor**: Instance flavor, using the first flavor ID from the instance flavor query data source
  - **key\_name**: Key pair ID, referencing the ID of the key pair resource created earlier
  - **security\_group\_ids**: Security group ID list, referencing the ID of the security group resource created earlier
  - **metadata**: Metadata configuration, setting key-value pairs
  - **user\_data**: Instance startup script, used for initializing instances
  - **disk**: Disk configuration block
    - **size**: Disk size (GB), set to 40GB
    - **volume\_type**: Disk type, set to "SSD"
    - **disk\_type**: Disk purpose, set to "SYS" for system disk
  - **public\_ip**: Public IP configuration block
    - **eip**: Elastic public IP configuration
      - **ip\_type**: Public IP type, set to "5\_bgp"
      - **bandwidth**: Bandwidth configuration block
        - **size**: Bandwidth size, set to 10Mbps
        - **share\_type**: Bandwidth type, set to "PER" for dedicated
        - **charging\_mode**: Billing mode, set to "traffic" for traffic-based billing

### 8. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content, and these input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Key pair configuration
public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC..."
```

**Usage Method**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content in this `tfvars` file when executing terraform commands, other names need to add `.auto` definition before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="public_key=your-public-key"`
2. Environment variables: `export TF_VAR_public_key=your-public-key`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values in the following priority: command line parameters > variable files > environment variables > default values.

### 9. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating scaling configuration
4. Run `terraform show` to view the details of the created scaling configuration

## Reference Information

- [Huawei Cloud Auto Scaling Product Documentation](https://support.huaweicloud.com/as/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For AS Scaling Configuration](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/as/scaling-configuration)

# Deploy Scaling Group

## Application Scenario

Huawei Cloud Auto Scaling service is a service that automatically adjusts computing resources, capable of automatically adjusting the number of elastic computing instances based on business needs and policies. Scaling group is the core resource of Auto Scaling service, used to manage a group of elastic computing instances with the same configuration and rules. By creating a scaling group, you can automatically manage the increase and decrease of instance numbers, realize elastic expansion and contraction of resources, and meet the needs of business load changes. This best practice will introduce how to use Terraform to automatically deploy a scaling group, including querying availability zones, instance flavors, and images, as well as creating security groups, key pairs, AS configuration, VPC network, and scaling group.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [Compute Flavors Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [Images Query Data Source (data.huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Key Pair Resource (huaweicloud\_kps\_keypair)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/kps_keypair)
- [AS Configuration Resource (huaweicloud\_as\_configuration)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/as_configuration)
- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [AS Group Resource (huaweicloud\_as\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/as_group)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── data.huaweicloud_compute_flavors
        └── data.huaweicloud_images_images
            └── huaweicloud_as_configuration

huaweicloud_networking_secgroup
    └── huaweicloud_as_configuration
        └── huaweicloud_as_group

huaweicloud_kps_keypair
    └── huaweicloud_as_configuration
        └── huaweicloud_as_group

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_as_group
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration introduction, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy).

### 2. Query Availability Zones Required for Scaling Group Resource Creation Through Data Source

Add the following script to the TF file (such as main.tf) to inform Terraform to perform a data source query, the query results are used to create scaling group related resources:

```hcl
variable "availability_zone" {
  description = "The availability zone to which the scaling configuration belongs"
  type        = string
  default     = ""
}

# Get all availability zone information in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating scaling group related resources
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}
```

**Parameter Description**:

- **count**: The number of data source creations, used to control whether to execute the availability zone list query, only when `var.availability_zone` is empty, the data source is created (i.e., execute the availability zone list query)

### 3. Query Instance Flavors Required for Scaling Group Resource Creation Through Data Source

Add the following script to the TF file to inform Terraform to query instance flavors that meet the conditions:

```hcl
variable "configuration_flavor_id" {
  description = "The flavor ID of the scaling configuration"
  type        = string
  default     = ""
}

variable "configuration_flavor_performance_type" {
  description = "The performance type of the scaling configuration"
  type        = string
  default     = "normal"
}

variable "configuration_flavor_cpu_core_count" {
  description = "The CPU core count of the scaling configuration"
  type        = number
  default     = 2
}

variable "configuration_flavor_memory_size" {
  description = "The memory size of the scaling configuration"
  type        = number
  default     = 4
}

# Get all instance flavor information that meets specific conditions in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating scaling group related resources
data "huaweicloud_compute_flavors" "test" {
  count = var.configuration_flavor_id == "" ? 1 : 0

  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
  performance_type  = var.configuration_flavor_performance_type
  cpu_core_count    = var.configuration_flavor_cpu_core_count
  memory_size       = var.configuration_flavor_memory_size
}
```

**Parameter Description**:

- **count**: The number of data source creations, used to control whether to execute the instance flavor list query, only when `var.configuration_flavor_id` is empty, the data source is created (i.e., execute the instance flavor list query)
- **availability\_zone**: The availability zone where the instance flavor is located, if the availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source
- **performance\_type**: Performance type, assigned through input variable `configuration_flavor_performance_type`, default is "normal" for standard type
- **cpu\_core\_count**: CPU core count, assigned through input variable `configuration_flavor_cpu_core_count`
- **memory\_size**: Memory size (GB), assigned through input variable `configuration_flavor_memory_size`

### 4. Query Images Required for Scaling Group Resource Creation Through Data Source

Add the following script to the TF file to inform Terraform to query images that meet the conditions:

```hcl
variable "configuration_image_id" {
  description = "The image ID of the scaling configuration"
  type        = string
  default     = ""
}

variable "configuration_image_visibility" {
  description = "The visibility of the image"
  type        = string
  default     = "public"
}

variable "configuration_image_os" {
  description = "The OS of the image"
  type        = string
  default     = "Ubuntu"
}

# Get all image information that meets specific conditions in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating scaling group related resources
data "huaweicloud_images_images" "test" {
  count = var.configuration_image_id == "" ? 1 : 0

  flavor_id  = var.configuration_flavor_id == "" ? try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null) : var.configuration_flavor_id
  visibility = var.configuration_image_visibility
  os         = var.configuration_image_os
}
```

**Parameter Description**:

- **count**: The number of data source creations, used to control whether to execute the image list query, only when `var.configuration_image_id` is empty, the data source is created (i.e., execute the image list query)
- **flavor\_id**: The flavor ID supported by the image, if the flavor ID is specified, use that value, otherwise use the first flavor ID from the instance flavor list query data source
- **visibility**: Image visibility, assigned through input variable `configuration_image_visibility`, default is "public" for public images
- **os**: Operating system type, assigned through input variable `configuration_image_os`, default is "Ubuntu"

### 5. Create Security Group Resource

Add the following script to the TF file to inform Terraform to create security group resources:

```hcl
variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create security group resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing security protection for scaling group
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: The name of the security group, assigned by referencing input variable `security_group_name`
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default rules

### 6. Create Key Pair Resource

Add the following script to the TF file to inform Terraform to create key pair resources:

```hcl
variable "keypair_name" {
  description = "The name of the key pair"
  type        = string
}

variable "keypair_public_key" {
  description = "The public key for SSH access"
  type        = string
  default     = ""
}

# Create key pair resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for accessing AS instances
resource "huaweicloud_kps_keypair" "test" {
  name       = var.keypair_name
  public_key = var.keypair_public_key != "" ? var.keypair_public_key : null
}
```

**Parameter Description**:

- **name**: The name of the key pair, assigned by referencing input variable `keypair_name`
- **public\_key**: The public key of the key pair, if the public key is specified, use that value, otherwise set to null (the system will automatically generate a key pair)

### 7. Create AS Configuration Resource

Add the following script to the TF file to inform Terraform to create AS configuration resources:

```hcl
variable "configuration_name" {
  description = "The name of the scaling configuration"
  type        = string
}

variable "configuration_metadata" {
  description = "The metadata for the scaling configuration instances"
  type        = map(string)
}

variable "configuration_user_data" {
  description = "The user data script for scaling configuration instances initialization"
  type        = string
}

variable "configuration_disks" {
  description = "The disk configurations for the scaling configuration instances"
  type = list(object({
    size        = number
    volume_type = string
    disk_type   = string
  }))

  nullable = false
}

variable "configuration_public_eip_settings" {
  description = "The public IP settings for the scaling configuration instances"
  type = list(object({
    ip_type = string
    bandwidth = object({
      size          = number
      share_type    = string
      charging_mode = string
    })
  }))

  nullable = false
  default  = []
}

# Create AS configuration resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for defining templates for AS instances
resource "huaweicloud_as_configuration" "test" {
  scaling_configuration_name = var.configuration_name

  instance_config {
    image              = var.configuration_image_id == "" ? try(data.huaweicloud_images_images.test[0].images[0].id, null) : var.configuration_image_id
    flavor             = var.configuration_flavor_id == "" ? try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null) : var.configuration_flavor_id
    key_name           = huaweicloud_kps_keypair.test.id
    security_group_ids = [huaweicloud_networking_secgroup.test.id]

    metadata  = var.configuration_metadata
    user_data = var.configuration_user_data

    dynamic "disk" {
      for_each = var.configuration_disks

      content {
        size        = disk.value["size"]
        volume_type = disk.value["volume_type"]
        disk_type   = disk.value["disk_type"]
      }
    }

    dynamic "public_ip" {
      for_each = var.configuration_public_eip_settings

      content {
        eip {
          ip_type = public_ip.value.ip_type

          bandwidth {
            size          = public_ip.value.bandwidth.size
            share_type    = public_ip.value.bandwidth.share_type
            charging_mode = public_ip.value.bandwidth.charging_mode
          }
        }
      }
    }
  }
}
```

**Parameter Description**:

- **scaling\_configuration\_name**: The name of the AS configuration, assigned by referencing input variable `configuration_name`
- **instance\_config**: Instance configuration block, defines the configuration for AS instances
  - **image**: Instance image ID, if the image ID is specified, use that value, otherwise use the first image ID from the image list query data source
  - **flavor**: Instance flavor ID, if the flavor ID is specified, use that value, otherwise use the first flavor ID from the instance flavor list query data source
  - **key\_name**: Key pair ID, assigned by referencing the ID of the key pair resource (huaweicloud\_kps\_keypair.test)
  - **security\_group\_ids**: Security group ID list, assigned by referencing the ID of the security group resource (huaweicloud\_networking\_secgroup.test)
  - **metadata**: Instance metadata, assigned through input variable `configuration_metadata`, used to inject custom data when instances start
  - **user\_data**: User data script, assigned through input variable `configuration_user_data`, used to execute initialization scripts when instances start
  - **disk**: Disk configuration block, creates multiple disk configurations through dynamic block (dynamic block) based on input variable `configuration_disks`
    - **size**: Disk size (GB), assigned through `size` in input variable `configuration_disks`
    - **volume\_type**: Volume type, assigned through `volume_type` in input variable `configuration_disks`
    - **disk\_type**: Disk type, assigned through `disk_type` in input variable `configuration_disks`
  - **public\_ip**: Public IP configuration block, creates public IP configuration through dynamic block (dynamic block) based on input variable `configuration_public_eip_settings`
    - **eip**: Elastic IP configuration block
      - **ip\_type**: IP type, assigned through `ip_type` in input variable `configuration_public_eip_settings`
      - **bandwidth**: Bandwidth configuration block
        - **size**: Bandwidth size (Mbps), assigned through `bandwidth.size` in input variable `configuration_public_eip_settings`
        - **share\_type**: Share type, assigned through `bandwidth.share_type` in input variable `configuration_public_eip_settings`
        - **charging\_mode**: Charging mode, assigned through `bandwidth.charging_mode` in input variable `configuration_public_eip_settings`

> Note: The disk configuration must include at least one system disk (disk\_type is "SYS"), and other disks are data disks. Public IP configuration is optional, if public IP is not needed, you can not configure `configuration_public_eip_settings` or set it to an empty list.

### 8. Create VPC Resource (Optional)

Add the following script to the TF file to inform Terraform to create VPC resources (if VPC ID is not specified):

```hcl
variable "scaling_group_vpc_id" {
  description = "The ID of the VPC"
  type        = string
  default     = ""
}

variable "scaling_group_vpc_name" {
  description = "The name of the VPC"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = var.scaling_group_vpc_id == "" && var.scaling_group_vpc_name != ""
    error_message = "When 'scaling_group_vpc_id' is empty, 'scaling_group_vpc_name' is not allowed to be empty"
  }
}

variable "scaling_group_vpc_cidr" {
  description = "The CIDR of the VPC"
  type        = string
  default     = "192.168.0.0/16"
}

# Create VPC resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing network environment for scaling group
resource "huaweicloud_vpc" "test" {
  count = var.scaling_group_vpc_id == "" && var.scaling_group_subnet_id == "" ? 1 : 0

  name = var.scaling_group_vpc_name
  cidr = var.scaling_group_vpc_cidr
}
```

**Parameter Description**:

- **count**: The number of resource creations, used to control whether to create VPC resource, only when both `var.scaling_group_vpc_id` and `var.scaling_group_subnet_id` are empty, the VPC resource is created
- **name**: The name of the VPC, assigned by referencing input variable `scaling_group_vpc_name`
- **cidr**: The CIDR block of the VPC, assigned by referencing input variable `scaling_group_vpc_cidr`, default is "192.168.0.0/16"

### 9. Create VPC Subnet Resource (Optional)

Add the following script to the TF file to inform Terraform to create VPC subnet resources (if subnet ID is not specified):

```hcl
variable "scaling_group_subnet_id" {
  description = "The ID of the subnet"
  type        = string
  default     = ""
}

variable "scaling_group_subnet_name" {
  description = "The name of the subnet"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = var.scaling_group_subnet_id == "" && var.scaling_group_subnet_name != ""
    error_message = "When 'scaling_group_subnet_id' is empty, 'scaling_group_subnet_name' is not allowed to be empty"
  }
}

variable "scaling_group_subnet_cidr" {
  description = "The CIDR of the subnet"
  type        = string
  default     = ""
}

variable "scaling_group_subnet_gateway_ip" {
  description = "The gateway IP of the subnet"
  type        = string
  default     = ""
}

# Create VPC subnet resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing network environment for scaling group
resource "huaweicloud_vpc_subnet" "test" {
  count = var.scaling_group_subnet_id == "" ? 1 : 0

  vpc_id     = var.scaling_group_vpc_id == "" ? huaweicloud_vpc.test[0].id : var.scaling_group_vpc_id
  name       = var.scaling_group_subnet_name
  cidr       = var.scaling_group_subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test[0].cidr, 8, 0) : var.scaling_group_subnet_cidr
  gateway_ip = var.scaling_group_subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test[0].cidr, 8, 0), 1) : var.scaling_group_subnet_gateway_ip
}
```

**Parameter Description**:

- **count**: The number of resource creations, used to control whether to create VPC subnet resource, only when `var.scaling_group_subnet_id` is empty, the VPC subnet resource is created
- **vpc\_id**: The VPC ID to which the subnet belongs, if the VPC ID is specified, use that value, otherwise assign by referencing the ID of the VPC resource (huaweicloud\_vpc.test\[0])
- **name**: The name of the subnet, assigned by referencing input variable `scaling_group_subnet_name`
- **cidr**: The CIDR block of the subnet, if the subnet CIDR is specified, use that value, otherwise automatically calculate based on the VPC's CIDR block using the `cidrsubnet` function
- **gateway\_ip**: The gateway IP of the subnet, if the gateway IP is specified, use that value, otherwise automatically calculate based on the subnet CIDR using the `cidrhost` function

### 10. Create AS Group Resource

Add the following script to the TF file to inform Terraform to create AS group resources:

```hcl
variable "scaling_group_name" {
  description = "The name of the scaling group"
  type        = string
}

variable "scaling_group_desire_instance_number" {
  description = "The desired number of instances"
  type        = number
  default     = 2
}

variable "scaling_group_min_instance_number" {
  description = "The minimum number of instances"
  type        = number
  default     = 0
}

variable "scaling_group_max_instance_number" {
  description = "The maximum number of instances"
  type        = number
  default     = 10
}

variable "is_delete_scaling_group_publicip" {
  description = "Whether to delete the public IP address of the scaling instances when the scaling group is deleted"
  type        = bool
  default     = true
}

variable "is_delete_scaling_group_instances" {
  description = "Whether to delete the scaling instances when the scaling group is deleted"
  type        = string
  default     = "yes"
}

# Create AS group resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for managing AS instances
resource "huaweicloud_as_group" "test" {
  scaling_group_name       = var.scaling_group_name
  scaling_configuration_id = huaweicloud_as_configuration.test.id
  desire_instance_number   = var.scaling_group_desire_instance_number
  min_instance_number      = var.scaling_group_min_instance_number
  max_instance_number      = var.scaling_group_max_instance_number
  vpc_id                   = var.scaling_group_vpc_id == "" ? huaweicloud_vpc.test[0].id : var.scaling_group_vpc_id
  delete_publicip          = var.is_delete_scaling_group_publicip
  delete_instances         = var.is_delete_scaling_group_instances

  networks {
    id = var.scaling_group_subnet_id == "" ? huaweicloud_vpc_subnet.test[0].id : var.scaling_group_subnet_id
  }
}
```

**Parameter Description**:

- **scaling\_group\_name**: The name of the AS group, assigned by referencing input variable `scaling_group_name`
- **scaling\_configuration\_id**: AS configuration ID, assigned by referencing the ID of the AS configuration resource (huaweicloud\_as\_configuration.test)
- **desire\_instance\_number**: The desired number of AS instances, assigned by referencing input variable `scaling_group_desire_instance_number`, default is 2
- **min\_instance\_number**: The minimum number of AS instances, assigned by referencing input variable `scaling_group_min_instance_number`, default is 0
- **max\_instance\_number**: The maximum number of AS instances, assigned by referencing input variable `scaling_group_max_instance_number`, default is 10
- **vpc\_id**: VPC ID, if the VPC ID is specified, use that value, otherwise assign by referencing the ID of the VPC resource (huaweicloud\_vpc.test\[0])
- **delete\_publicip**: Whether to delete the public IP address of AS instances when the AS group is deleted, assigned by referencing input variable `is_delete_scaling_group_publicip`, default is true
- **delete\_instances**: Whether to delete AS instances when the AS group is deleted, assigned by referencing input variable `is_delete_scaling_group_instances`, value is "yes" or "no", default is "yes"
- **networks**: Network configuration block, defines the subnet used by the AS group
  - **id**: Subnet ID, if the subnet ID is specified, use that value, otherwise assign by referencing the ID of the VPC subnet resource (huaweicloud\_vpc\_subnet.test\[0])

> Note: `min_instance_number`, `desire_instance_number` and `max_instance_number` must satisfy the relationship: `min_instance_number <= desire_instance_number <= max_instance_number`.

### 11. Preset Input Parameters Required for Resource Deployment

In this practice, some resources and data sources use input variables to assign configuration content, and these input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory, example content is as follows:

```hcl
security_group_name     = "tf_test_secgroup_demo"
keypair_name            = "tf_test_keypair_demo"
configuration_name      = "tf_test_as_configuration"
configuration_metadata  = {
  some_key = "some_value"
}
configuration_user_data = <<EOT
# !/bin/sh
echo "Hello World! The time is now $(date -R)!" | tee /root/output.txt
EOT

configuration_disks = [
  {
    size        = 40
    volume_type = "SSD"
    disk_type   = "SYS"
  }
]

configuration_public_eip_settings = [
  {
    ip_type   = "5_bgp"
    bandwidth = {
      size          = 10
      share_type    = "PER"
      charging_mode = "traffic"
    }
  }
]

scaling_group_vpc_name    = "tf_test_vpc_demo"
scaling_group_subnet_name = "tf_test_subnet_demo"
scaling_group_name        = "tf_test_scaling_group_demo"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content in the `tfvars` file when executing terraform commands, other naming requires adding `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify the parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command line parameters: `terraform apply -var="security_group_name=my-secgroup" -var="keypair_name=my-keypair"`
2. Environment variables: `export TF_VAR_security_group_name=my-secgroup`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 12. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating scaling group
4. Run `terraform show` to view the created scaling group

## Reference Information

- [Huawei Cloud Auto Scaling Product Documentation](https://support.huaweicloud.com/as/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [AS Scaling Group Best Practice Source Code Reference](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/as/scaling-group)
