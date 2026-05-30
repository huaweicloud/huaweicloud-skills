# Deploy RocketMQ Migration Task

## Application Scenario

Huawei Cloud Distributed Message Service RocketMQ is a highly available, highly reliable, and high-performance distributed message middleware service, widely used in distributed systems in industries such as e-commerce, finance, and IoT. Migration tasks are one of the important functions of RocketMQ, used to migrate existing message middleware configurations and data to Huawei Cloud RocketMQ instances, achieving smooth business migration.

Through RocketMQ migration tasks, enterprises can achieve seamless migration from other message middleware (such as Apache RocketMQ, RabbitMQ, etc.) to Huawei Cloud RocketMQ, including topic configurations, consumer group configurations, virtual hosts, queues, exchanges, and binding relationships, ensuring business continuity and data integrity. This best practice will introduce how to use Terraform to automatically deploy RocketMQ migration tasks, including RocketMQ instance and migration task creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [RocketMQ Availability Zones Query Data Source (data.huaweicloud\_dms\_rocketmq\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/dms_rocketmq_availability_zones)
- [RocketMQ Flavors Query Data Source (data.huaweicloud\_dms\_rocketmq\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/dms_rocketmq_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [RocketMQ Instance Resource (huaweicloud\_dms\_rocketmq\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dms_rocketmq_instance)
- [RocketMQ Migration Task Resource (huaweicloud\_dms\_rocketmq\_migration\_task)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dms_rocketmq_migration_task)

### Resource/Data Source Dependencies

```
data.huaweicloud_dms_rocketmq_availability_zones
    └── data.huaweicloud_dms_rocketmq_flavors
        └── huaweicloud_dms_rocketmq_instance
            └── huaweicloud_dms_rocketmq_migration_task

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_dms_rocketmq_instance
            └── huaweicloud_dms_rocketmq_migration_task

huaweicloud_networking_secgroup
    └── huaweicloud_dms_rocketmq_instance
        └── huaweicloud_dms_rocketmq_migration_task
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query RocketMQ Availability Zone Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to create RocketMQ instances:

```hcl
variable "availability_zones" {
  description = "The availability zones to which the RocketMQ instance belongs"
  type        = list(string)
  default     = []
  nullable    = false
}

# Get all RocketMQ availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create RocketMQ instances
data "huaweicloud_dms_rocketmq_availability_zones" "test" {
  count = length(var.availability_zones) == 0 ? 1 : 0
}
```

**Parameter Description**:

- **count**: Data source creation count, used to control whether to execute the availability zones list query data source, only creates data source when availability\_zones is empty (i.e., executes availability zones list query)

### 3. Query RocketMQ Flavor Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to create RocketMQ instances:

```hcl
variable "instance_flavor_id" {
  description = "The flavor ID of the RocketMQ instance"
  type        = string
  default     = ""
  nullable    = false
}

variable "instance_flavor_type" {
  description = "The flavor type of the RocketMQ instance"
  type        = string
  default     = "cluster.small"
}

variable "availability_zones_count" {
  description = "The number of availability zones"
  type        = number
  default     = 1
}

# Get all RocketMQ flavor information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create RocketMQ instances
data "huaweicloud_dms_rocketmq_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  type               = var.instance_flavor_type
  availability_zones = length(var.availability_zones) != 0 ? var.availability_zones : slice(data.huaweicloud_dms_rocketmq_availability_zones.test[0].availability_zones[*].code, 0, var.availability_zones_count)
}
```

**Parameter Description**:

- **count**: Data source creation count, used to control whether to execute the flavors list query data source, only creates data source when `var.instance_flavor_id` is empty (i.e., executes flavors list query)
- **type**: RocketMQ instance flavor type, prioritizes using the flavor type specified in input variables, defaults to "cluster.small" if not specified
- **availability\_zones**: Availability zones list, prioritizes using the availability zones specified in input variables, uses the first `var.availability_zones_count` availability zones from data source query results if not specified
- **availability\_zones\_count**: Number of availability zones, prioritizes using the availability zones count specified in input variables, defaults to 1 if not specified

### 4. Create VPC Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC resource:

```hcl
variable "vpc_name" {
  description = "The VPC name"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
  default     = "192.168.0.0/16"
}

# Create a VPC resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: VPC name
- **cidr**: VPC CIDR block, prioritizes using the CIDR block specified in input variables, defaults to "192.168.0.0/16" if not specified

### 5. Create VPC Subnet Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "The subnet name"
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

# Create a VPC subnet resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}
```

**Parameter Description**:

- **vpc\_id**: Subnet's VPC ID, references the ID of the VPC resource created earlier
- **name**: Subnet name
- **cidr**: Subnet CIDR block, prioritizes using the CIDR block specified in input variables, automatically calculated if not specified
- **gateway\_ip**: Subnet gateway IP, prioritizes using the gateway IP specified in input variables, automatically calculated if not specified

### 6. Create Security Group Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "The security group name"
  type        = string
}

# Create a security group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: Security group name
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default rules

### 7. Create RocketMQ Instance

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a RocketMQ instance resource:

```hcl
variable "instance_name" {
  description = "The name of the RocketMQ instance"
  type        = string
}

variable "instance_engine_version" {
  description = "The engine version of the RocketMQ instance"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = var.instance_flavor_id == "" || var.instance_engine_version != ""
    error_message = "When 'instance_flavor_id' is not empty, 'instance_engine_version' is required"
  }
}

variable "instance_storage_spec_code" {
  description = "The storage spec code of the RocketMQ instance"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = var.instance_flavor_id == "" || var.instance_storage_spec_code != ""
    error_message = "When 'instance_flavor_id' is not empty, 'instance_storage_spec_code' is required"
  }
}

variable "instance_storage_space" {
  description = "The storage space of the RocketMQ instance in GB"
  type        = number
  default     = 800
}

variable "instance_broker_num" {
  description = "The number of brokers for the RocketMQ instance"
  type        = number
  default     = 1
}

variable "instance_description" {
  description = "The description of the RocketMQ instance"
  type        = string
  default     = ""
}

variable "instance_tags" {
  description = "The tags of the RocketMQ instance"
  type        = map(string)
  default     = {}
}

variable "enterprise_project_id" {
  description = "The enterprise project ID"
  type        = string
  default     = null
}

variable "instance_enable_acl" {
  description = "Whether to enable ACL for the RocketMQ instance"
  type        = bool
  default     = false
}

variable "instance_tls_mode" {
  description = "The TLS mode of the RocketMQ instance"
  type        = string
  default     = "SSL"
}

variable "instance_configs" {
  description = "The configuration parameters of the RocketMQ instance"
  type = list(object({
    name  = string
    value = string
  }))

  nullable = false
  default  = []
}

# Create a RocketMQ instance resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_dms_rocketmq_instance" "test" {
  name                  = var.instance_name
  flavor_id             = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_dms_rocketmq_flavors.test[0].flavors[0].id, null)
  engine_version        = var.instance_engine_version != "" ? var.instance_engine_version : try(data.huaweicloud_dms_rocketmq_flavors.test[0].versions[0], null)
  storage_spec_code     = var.instance_storage_spec_code != "" ? var.instance_storage_spec_code : try(data.huaweicloud_dms_rocketmq_flavors.test[0].flavors[0].ios[0].storage_spec_code, null)
  storage_space         = var.instance_storage_space
  availability_zones    = length(var.availability_zones) != 0 ? var.availability_zones : slice(data.huaweicloud_dms_rocketmq_availability_zones.test[0].availability_zones[*].code, 0, var.availability_zones_count)
  vpc_id                = huaweicloud_vpc.test.id
  subnet_id             = huaweicloud_vpc_subnet.test.id
  security_group_id     = huaweicloud_networking_secgroup.test.id
  broker_num            = var.instance_broker_num
  description           = var.instance_description
  tags                  = var.instance_tags
  enterprise_project_id = var.enterprise_project_id
  enable_acl            = var.instance_enable_acl
  tls_mode              = var.instance_tls_mode

  dynamic "configs" {
    for_each = var.instance_configs

    content {
      name  = configs.value.name
      value = configs.value.value
    }
  }
}
```

**Parameter Description**:

- **name**: RocketMQ instance name
- **flavor\_id**: RocketMQ instance flavor ID, prioritizes using the flavor specified in input variables, uses data source query results if not specified
- **engine\_version**: RocketMQ engine version, prioritizes using the version specified in input variables, uses data source query results if not specified
- **storage\_spec\_code**: Storage spec code, prioritizes using the spec specified in input variables, uses data source query results if not specified
- **storage\_space**: Storage space size, prioritizes using the storage space size specified in input variables, defaults to 800GB if not specified
- **availability\_zones**: Availability zones list, prioritizes using the availability zones specified in input variables, uses data source query results if not specified
- **vpc\_id**: VPC ID, references the ID of the VPC resource created earlier
- **subnet\_id**: Subnet ID, references the ID of the subnet resource created earlier
- **security\_group\_id**: Security group ID, references the ID of the security group resource created earlier
- **broker\_num**: Broker count, prioritizes using the broker count specified in input variables, defaults to 1 if not specified
- **description**: Instance description
- **tags**: Instance tags
- **enterprise\_project\_id**: Enterprise project ID
- **enable\_acl**: Whether to enable ACL, prioritizes using the enable ACL setting specified in input variables, defaults to false if not specified
- **tls\_mode**: TLS mode, prioritizes using the TLS mode specified in input variables, defaults to "SSL" if not specified
- **configs**: Instance configuration block

### 8. Create RocketMQ Migration Task

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a RocketMQ migration task resource:

## Create Migration Task from RocketMQ to RocketMQ

```hcl
variable "migration_task_name" {
  description = "The name of the migration task"
  type        = string
}

variable "migration_task_overwrite" {
  description = "Whether to overwrite existing configurations"
  type        = bool
  default     = false
}

variable "migration_task_topic_configs" {
  description = "The topic configuration list of the migration task"

  type = list(object({
    topic_name        = string
    order             = optional(bool)
    perm              = optional(number)
    read_queue_nums   = optional(number)
    write_queue_nums  = optional(number)
    topic_filter_type = optional(string)
    topic_sys_flag    = optional(number)
  }))

  default  = []
  nullable = false
}

variable "migration_task_subscription_groups" {
  description = "The subscription group list of the migration task"

  type = list(object({
    group_name                        = string
    consume_broadcast_enable          = optional(bool)
    consume_enable                    = optional(bool)
    consume_from_min_enable           = optional(bool)
    notify_consumerids_changed_enable = optional(bool)
    retry_max_times                   = optional(number)
    retry_queue_num                   = optional(number)
    which_broker_when_consume_slow    = optional(number)
  }))

  default  = []
  nullable = false
}

# Create a RocketMQ migration task resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_dms_rocketmq_migration_task" "test" {
  instance_id = huaweicloud_dms_rocketmq_instance.test.id
  name        = var.migration_task_name
  overwrite   = var.migration_task_overwrite
  type        = "rocketmq"

  dynamic "topic_configs" {
    for_each = var.migration_task_topic_configs

    content {
      order             = topic_configs.value["order"]
      perm              = topic_configs.value["perm"]
      read_queue_num    = topic_configs.value["read_queue_nums"]
      topic_filter_type = topic_configs.value["topic_filter_type"]
      topic_name        = topic_configs.value["topic_name"]
      topic_sys_flag    = topic_configs.value["topic_sys_flag"]
      write_queue_num   = topic_configs.value["write_queue_nums"]
    }
  }

  dynamic "subscription_groups" {
    for_each = var.migration_task_subscription_groups

    content {
      consume_broadcast_enable          = subscription_groups.value["consume_broadcast_enable"]
      consume_enable                    = subscription_groups.value["consume_enable"]
      consume_from_min_enable           = subscription_groups.value["consume_from_min_enable"]
      group_name                        = subscription_groups.value["group_name"]
      notify_consumerids_changed_enable = subscription_groups.value["notify_consumerids_changed_enable"]
      retry_max_times                   = subscription_groups.value["retry_max_times"]
      retry_queue_num                   = subscription_groups.value["retry_queue_num"]
      which_broker_when_consume_slow    = subscription_groups.value["which_broker_when_consume_slow"]
    }
  }
}
```

## Create Migration Task from RabbitMQ to RocketMQ

```hcl
variable "migration_task_vhosts" {
  description = "The virtual host list of the migration task"

  type = list(object({
    name = string
  }))

  default  = []
  nullable = false
}

variable "migration_task_queues" {
  description = "The queue list of the migration task"

  type = list(object({
    name    = optional(string)
    vhost   = optional(string)
    durable = optional(bool)
  }))

  default  = []
  nullable = false
}

variable "migration_task_exchanges" {
  description = "The exchange list of the migration task"

  type = list(object({
    name    = optional(string)
    vhost   = optional(string)
    type    = optional(string)
    durable = optional(bool)
  }))

  default  = []
  nullable = false
}

variable "migration_task_bindings" {
  description = "The binding list of the migration task"

  type = list(object({
    vhost            = optional(string)
    source           = optional(string)
    destination      = optional(string)
    destination_type = optional(string)
    routing_key      = optional(string)
  }))

  default  = []
  nullable = false
}

# Create a RocketMQ migration task resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_dms_rocketmq_migration_task" "test" {
  instance_id = huaweicloud_dms_rocketmq_instance.test.id
  name        = var.migration_task_name
  overwrite   = var.migration_task_overwrite
  type        = "rabbitToRocket"

  dynamic "vhosts" {
    for_each = var.migration_task_vhosts

    content {
      name = vhosts.value["name"]
    }
  }

  dynamic "queues" {
    for_each = var.migration_task_queues

    content {
      name    = queues.value["name"]
      vhost   = queues.value["vhost"]
      durable = queues.value["durable"]
    }
  }

  dynamic "exchanges" {
    for_each = var.migration_task_exchanges

    content {
      name    = exchanges.value["name"]
      vhost   = exchanges.value["vhost"]
      type    = exchanges.value["type"]
      durable = exchanges.value["durable"]
    }
  }

  dynamic "bindings" {
    for_each = var.migration_task_bindings

    content {
      vhost            = bindings.value["vhost"]
      source           = bindings.value["source"]
      destination      = bindings.value["destination"]
      destination_type = bindings.value["destination_type"]
      routing_key      = bindings.value["routing_key"]
    }
  }
}
```

**Parameter Description**:

- **instance\_id**: RocketMQ instance ID, references the ID of the RocketMQ instance resource created earlier
- **name**: Migration task name
- **overwrite**: Whether to overwrite existing configurations with the same name, prioritizes using the overwrite setting specified in input variables, defaults to false if not specified
- **type**: Migration task type, supports "rocketmq" and "rabbitToRocket" types
- **topic\_configs**: Topic configuration block, used to configure RocketMQ topic-related parameters (only used when type="rocketmq")
- **subscription\_groups**: Subscription group configuration block, used to configure consumer group-related parameters (only used when type="rocketmq")
- **vhosts**: Virtual host configuration block, used to configure RabbitMQ virtual hosts (only used when type="rabbitToRocket")
- **queues**: Queue configuration block, used to configure RabbitMQ queues (only used when type="rabbitToRocket")
- **exchanges**: Exchange configuration block, used to configure RabbitMQ exchanges (only used when type="rabbitToRocket")
- **bindings**: Binding relationship configuration block, used to configure RabbitMQ binding relationships (only used when type="rabbitToRocket")

### 9. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and subnet configuration
vpc_name            = "tf_test_vpc"
subnet_name         = "tf_test_subnet"
security_group_name = "tf_test_security_group"

# RocketMQ instance basic information
instance_name        = "tf_test_instance"
instance_broker_num  = 1
instance_description = "Created by terraform script"

# Migration task basic information
migration_task_name      = "tf_test_migration_task"
migration_task_overwrite = "true"
migration_task_type      = "rocketmq"

migration_task_topic_configs = [
  {
    topic_name        = "tf_test_task_topic"
    topic_filter_type = "SINGLE_TAG"
    perm              = 6
    read_queue_nums   = 3
    write_queue_nums  = 3
  }
]

migration_task_subscription_groups = [
  {
    group_name      = "tf_test_task_group"
    consume_enable  = true
    retry_max_times = 16
  }
]
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="subnet_name=my-subnet"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 10. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the RocketMQ migration task
4. Run `terraform show` to view the details of the created RocketMQ migration task

## Reference Information

- [Huawei Cloud Distributed Message Service RocketMQ Product Documentation](https://support.huaweicloud.com/hrm/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For RocketMQ Migration Task](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dms/rocketmq/migration-task)
