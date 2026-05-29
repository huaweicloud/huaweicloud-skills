# Deploy RocketMQ Consumer Group

## Application Scenario

Huawei Cloud Distributed Message Service RocketMQ is a highly available, highly reliable, and high-performance distributed message middleware service, widely used in distributed systems in industries such as e-commerce, finance, and IoT. Consumer groups are an important concept in RocketMQ message consumption, used to manage message consumption behavior and ensure messages can be consumed correctly and efficiently.

Through RocketMQ consumer groups, enterprises can implement message load balancing consumption, consumption progress management, consumption failure retry, and other functions, meeting message consumption requirements for different business scenarios. This best practice will introduce how to use Terraform to automatically deploy a RocketMQ consumer group, including RocketMQ instance and consumer group creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [RocketMQ Availability Zones Query Data Source (data.huaweicloud\_dms\_rocketmq\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/dms_rocketmq_availability_zones)
- [RocketMQ Flavors Query Data Source (data.huaweicloud\_dms\_rocketmq\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/dms_rocketmq_flavors)
- [RocketMQ Broker Query Data Source (data.huaweicloud\_dms\_rocketmq\_broker)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/dms_rocketmq_broker)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [RocketMQ Instance Resource (huaweicloud\_dms\_rocketmq\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dms_rocketmq_instance)
- [RocketMQ Consumer Group Resource (huaweicloud\_dms\_rocketmq\_consumer\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dms_rocketmq_consumer_group)

### Resource/Data Source Dependencies

```
data.huaweicloud_dms_rocketmq_availability_zones
    └── data.huaweicloud_dms_rocketmq_flavors
        └── huaweicloud_dms_rocketmq_instance
            └── data.huaweicloud_dms_rocketmq_broker
                └── huaweicloud_dms_rocketmq_consumer_group

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_dms_rocketmq_instance
            └── huaweicloud_dms_rocketmq_consumer_group

huaweicloud_networking_secgroup
    └── huaweicloud_dms_rocketmq_instance
        └── huaweicloud_dms_rocketmq_consumer_group
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

- **count**: Data source creation count, used to control whether to execute the availability zones list query data source, only creates data source when `var.availability_zones` is empty (i.e., executes availability zones list query)

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

  nullable    = false
  default = []
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

### 8. Query RocketMQ Broker Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to create consumer groups:

```hcl
variable "consumer_group_brokers" {
  description = "The broker list of the consumer group, it's only valid when the RocketMQ instance version is `4.8.0`"
  type        = list(string)
  default     = []
  nullable    = false
}

# Get all RocketMQ Broker information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create consumer groups
data "huaweicloud_dms_rocketmq_broker" "test" {
  count = length(var.consumer_group_brokers) == 0 && huaweicloud_dms_rocketmq_instance.test.engine_version == "4.8.0" ? 1 : 0

  instance_id = huaweicloud_dms_rocketmq_instance.test.id
}
```

**Parameter Description**:

- **count**: Data source creation count, used to control whether to execute the Broker query data source, only creates data source when consumer group broker list is not specified and RocketMQ instance version is 4.8.0
- **instance\_id**: RocketMQ instance ID, references the ID of the RocketMQ instance resource created earlier

### 9. Create RocketMQ Consumer Group

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a RocketMQ consumer group resource:

```hcl
variable "consumer_group_name" {
  description = "The name of the RocketMQ consumer group"
  type        = string
}

variable "consumer_group_retry_max_times" {
  description = "The maximum retry times for failed consumption"
  type        = number
  default     = 16
}

variable "consumer_group_enabled" {
  description = "Whether to enable the consumer group"
  type        = bool
  default     = true
}

variable "consumer_group_broadcast" {
  description = "Whether to enable broadcast mode for the consumer group"
  type        = bool
  default     = false
}

variable "consumer_group_description" {
  description = "The description of the consumer group"
  type        = string
  default     = ""
}

variable "consumer_group_consume_orderly" {
  description = "Whether to enable orderly consumption for the consumer group"
  type        = bool
  default     = false
}

# Create a RocketMQ consumer group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_dms_rocketmq_consumer_group" "test" {
  instance_id     = huaweicloud_dms_rocketmq_instance.test.id
  name            = var.consumer_group_name
  retry_max_times = var.consumer_group_retry_max_times
  enabled         = var.consumer_group_enabled
  broadcast       = var.consumer_group_broadcast
  description     = var.consumer_group_description
  brokers         = length(var.consumer_group_brokers) > 0 ? var.consumer_group_brokers : try(data.huaweicloud_dms_rocketmq_broker.test[0].brokers, [])
  consume_orderly = var.consumer_group_consume_orderly
}
```

**Parameter Description**:

- **instance\_id**: RocketMQ instance ID, references the ID of the RocketMQ instance resource created earlier
- **name**: Consumer group name
- **retry\_max\_times**: Maximum retry times for failed consumption, prioritizes using the maximum retry times for failed consumption specified in input variables, defaults to 16 times if not specified
- **enabled**: Whether to enable consumer group, prioritizes using the enable consumer group setting specified in input variables, defaults to true if not specified
- **broadcast**: Whether to enable broadcast mode, prioritizes using the enable broadcast mode setting specified in input variables, defaults to false if not specified
- **description**: Consumer group description
- **brokers**: Broker list, prioritizes using the broker list specified in input variables, uses Broker query data source results if not specified
- **consume\_orderly**: Whether to enable orderly consumption, prioritizes using the enable orderly consumption setting specified in input variables, defaults to false if not specified, only valid when RocketMQ instance version is 5.x

### 10. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and subnet configuration
vpc_name            = "tf_test_vpc"
subnet_name         = "tf_test_subnet"
security_group_name = "tf_test_security_group"

# RocketMQ instance basic information
instance_name       = "tf_test_instance"
instance_broker_num = 1

# Consumer group basic information
consumer_group_name = "tf_test_consumer_group"
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

### 11. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the RocketMQ consumer group
4. Run `terraform show` to view the details of the created RocketMQ consumer group

## Reference Information

- [Huawei Cloud Distributed Message Service RocketMQ Product Documentation](https://support.huaweicloud.com/hrm/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For RocketMQ Consumer Group](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dms/rocketmq/consumer-group)