# Deploy Kafka Instance Configuration

## Application Scenario

Huawei Cloud Distributed Message Service Kafka is a highly available, highly reliable, and high-performance distributed message middleware service, widely used in big data, log collection, stream processing and other scenarios. By configuring Kafka instances, you can create and manage Kafka clusters, including instance specifications, storage configuration, network configuration, security configuration, etc., achieving reliable message transmission and processing. Automating Kafka instance configuration through Terraform can ensure standardized and consistent instance configuration, improving operational efficiency. This best practice will introduce how to use Terraform to automatically configure Kafka instances.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Data Source (huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [Kafka Flavors Data Source (huaweicloud\_dms\_kafka\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/dms_kafka_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Kafka Instance Resource (huaweicloud\_dms\_kafka\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dms_kafka_instance)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── data.huaweicloud_dms_kafka_flavors
        └── huaweicloud_dms_kafka_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_dms_kafka_instance

huaweicloud_networking_secgroup
    └── huaweicloud_dms_kafka_instance
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Data Sources

Add the following script to the TF file (e.g., main.tf) to query availability zone and Kafka flavor information:

```hcl
# Query availability zone information
data "huaweicloud_availability_zones" "test" {
  count = length(var.availability_zones) == 0 ? 1 : 0
}

# Query Kafka flavor information
data "huaweicloud_dms_kafka_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  type               = var.instance_flavor_type
  availability_zones = length(var.availability_zones) == 0 ? try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 3)) : var.availability_zones
  storage_spec_code  = var.instance_storage_spec_code
}
```

**Parameter Description**:

- **type**: Flavor type, assigned by referencing the input variable instance\_flavor\_type, default value is "cluster" (cluster mode)
- **availability\_zones**: Availability zone list, assigned by referencing the input variable availability\_zones or availability zones data source
- **storage\_spec\_code**: Storage specification code, assigned by referencing the input variable instance\_storage\_spec\_code, default value is "dms.physical.storage.ultra.v2"

### 3. Create Basic Network Resources

Add the following script to the TF file (e.g., main.tf) to create VPC, subnet and security group:

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
}

variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create VPC
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}

# Create subnet
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}

# Create security group
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

### 4. Create Kafka Instance Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Kafka instance resource:

```hcl
variable "availability_zones" {
  description = "The availability zones to which the Kafka instance belongs"
  type        = list(string)
  default     = []
}

variable "instance_name" {
  description = "The name of the Kafka instance"
  type        = string
}

variable "instance_engine_version" {
  description = "The engine version of the Kafka instance"
  type        = string
  default     = "2.7"
}

variable "instance_flavor_id" {
  description = "The flavor ID of the Kafka instance"
  type        = string
  default     = ""
}

variable "instance_flavor_type" {
  description = "The flavor type of the Kafka instance"
  type        = string
  default     = "cluster"
}

variable "instance_storage_spec_code" {
  description = "The storage specification code of the Kafka instance"
  type        = string
  default     = "dms.physical.storage.ultra.v2"
}

variable "instance_storage_space" {
  description = "The storage space of the Kafka instance"
  type        = number
  default     = 600
}

variable "instance_broker_num" {
  description = "The number of brokers of the Kafka instance"
  type        = number
  default     = 3
}

variable "instance_ssl_enable" {
  description = "Whether to enable SSL for the Kafka instance"
  type        = bool
  default     = false
}

variable "instance_access_user_name" {
  description = "The access user name of the Kafka instance"
  type        = string
  default     = ""
}

variable "instance_access_user_password" {
  description = "The access password of the Kafka instance"
  type        = string
  sensitive   = true
  default     = ""
}

variable "instance_description" {
  description = "The description of the Kafka instance"
  type        = string
  default     = ""
}

variable "charging_mode" {
  description = "The charging mode of the Kafka instance"
  type        = string
  default     = "postPaid"
}

variable "period_unit" {
  description = "The period unit of the Kafka instance"
  type        = string
  default     = null
}

variable "period" {
  description = "The period of the Kafka instance"
  type        = number
  default     = null
}

variable "auto_renew" {
  description = "Whether to enable auto renew for the Kafka instance"
  type        = string
  default     = "false"
}

# Create Kafka instance resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_dms_kafka_instance" "test" {
  name               = var.instance_name
  availability_zones = length(var.availability_zones) == 0 ? try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 3)) : var.availability_zones
  engine_version     = var.instance_engine_version
  flavor_id          = var.instance_flavor_id == "" ? try(data.huaweicloud_dms_kafka_flavors.test[0].flavors[0].id, null) : var.instance_flavor_id
  storage_spec_code  = var.instance_storage_spec_code
  storage_space      = var.instance_storage_space
  broker_num         = var.instance_broker_num
  vpc_id             = huaweicloud_vpc.test.id
  network_id         = huaweicloud_vpc_subnet.test.id
  security_group_id  = huaweicloud_networking_secgroup.test.id
  ssl_enable         = var.instance_ssl_enable
  access_user        = var.instance_access_user_name
  password           = var.instance_access_user_password
  description        = var.instance_description
  charging_mode      = var.charging_mode
  period_unit        = var.period_unit
  period             = var.period
  auto_renew         = var.auto_renew

  lifecycle {
    ignore_changes = [
      availability_zones,
      flavor_id,
    ]
  }
}
```

**Parameter Description**:

- **name**: Kafka instance name, assigned by referencing the input variable instance\_name
- **availability\_zones**: Availability zone list, assigned by referencing the input variable availability\_zones or availability zones data source
- **engine\_version**: Engine version, assigned by referencing the input variable instance\_engine\_version, default value is "2.7"
- **flavor\_id**: Flavor ID, assigned by referencing the input variable instance\_flavor\_id or Kafka flavors data source
- **storage\_spec\_code**: Storage specification code, assigned by referencing the input variable instance\_storage\_spec\_code, default value is "dms.physical.storage.ultra.v2"
- **storage\_space**: Storage space, assigned by referencing the input variable instance\_storage\_space, default value is 600 (GB)
- **broker\_num**: Number of brokers, assigned by referencing the input variable instance\_broker\_num, default value is 3
- **vpc\_id**: VPC ID, assigned by referencing the VPC resource
- **network\_id**: Network subnet ID, assigned by referencing the subnet resource
- **security\_group\_id**: Security group ID, assigned by referencing the security group resource
- **ssl\_enable**: Whether to enable SSL, assigned by referencing the input variable instance\_ssl\_enable, default value is false
- **access\_user**: Access user name, assigned by referencing the input variable instance\_access\_user\_name, optional parameter, default value is empty string
- **password**: Access password, assigned by referencing the input variable instance\_access\_user\_password, optional parameter, default value is empty string
- **description**: Instance description, assigned by referencing the input variable instance\_description, optional parameter, default value is empty string
- **charging\_mode**: Charging mode, assigned by referencing the input variable charging\_mode, default value is "postPaid" (on-demand)
- **period\_unit**: Billing period unit, assigned by referencing the input variable period\_unit, optional parameter, default value is null
- **period**: Billing period, assigned by referencing the input variable period, optional parameter, default value is null
- **auto\_renew**: Whether to enable auto renew, assigned by referencing the input variable auto\_renew, default value is "false"

### 5. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and Subnet Configuration
vpc_name    = "tf_test_instance"
vpc_cidr    = "192.168.0.0/16"
subnet_name = "tf_test_instance"

# Security Group Configuration
security_group_name = "tf_test_instance"

# Kafka Instance Configuration
instance_name                 = "tf_test_instance"
instance_ssl_enable           = true
instance_access_user_name     = "admin"
instance_access_user_password = "YourKafkaInstancePassword!"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially `instance_access_user_password` needs to be set to a password that meets password complexity requirements
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="instance_name=my_kafka" -var="vpc_name=my_vpc"`
2. Environment variables: `export TF_VAR_instance_name=my_kafka` and `export TF_VAR_vpc_name=my_vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. Since instance\_access\_user\_password contains sensitive information, it is recommended to use environment variables or encrypted variable files for setting.

### 6. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create a Kafka instance:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the Kafka instance and related resources
4. Run `terraform show` to view the details of the created Kafka instance

> Note: After the Kafka instance is created, security can be enhanced by configuring SSL and access users. The instance's availability zones and flavor ID cannot be modified after creation, so they need to be configured correctly during creation. Through lifecycle.ignore\_changes, Terraform can be prevented from modifying these immutable parameters in subsequent updates.

## Reference Information

- [Huawei Cloud Distributed Message Service Kafka Product Documentation](https://support.huaweicloud.com/kafka/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Instance Configuration](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dms/kafka/instance-configuration)
