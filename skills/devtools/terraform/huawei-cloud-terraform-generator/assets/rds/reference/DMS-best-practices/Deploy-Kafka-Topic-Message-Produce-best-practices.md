# Deploy Kafka Topic Message Produce

## Application Scenario

Huawei Cloud Distributed Message Service Kafka is a highly available, highly reliable, and high-performance distributed message middleware service, widely used in big data, log collection, stream processing and other scenarios. Through Kafka topic message production functionality, you can send messages to specified Kafka topics to achieve reliable message transmission and processing. By using Terraform to automatically deploy Kafka topic message production, you can ensure the standardization and consistency of message production configuration and improve operational efficiency. This best practice will introduce how to use Terraform to automatically deploy Kafka topic message production, including creating Kafka instances, topics, and message production.

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
- [Kafka Topic Resource (huaweicloud\_dms\_kafka\_topic)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dms_kafka_topic)
- [Kafka Message Produce Resource (huaweicloud\_dms\_kafka\_message\_produce)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dms_kafka_message_produce)

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

huaweicloud_dms_kafka_instance
    └── huaweicloud_dms_kafka_topic
        └── huaweicloud_dms_kafka_message_produce
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

# Query Kafka flavor information (only query when flavor_id is not specified)
data "huaweicloud_dms_kafka_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  type               = var.instance_flavor_type
  availability_zones = length(var.availability_zones) == 0 ? try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 1)) : var.availability_zones
  storage_spec_code  = var.instance_storage_spec_code
}
```

**Parameter Description**:

- **type**: Flavor type, assigned by referencing input variable instance\_flavor\_type, default value is "cluster" (cluster mode)
- **availability\_zones**: Availability zone list, assigned by referencing input variables or availability zones data source
- **storage\_spec\_code**: Storage specification code, assigned by referencing input variable instance\_storage\_spec\_code, default value is "dms.physical.storage.ultra.v2"

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
  name = var.security_group_name
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

variable "instance_name" {
  description = "The name of the Kafka instance"
  type        = string
}

variable "instance_engine_version" {
  description = "The engine version of the Kafka instance"
  type        = string
  default     = "2.7"
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

variable "instance_access_user_name" {
  description = "The access user of the Kafka instance"
  type        = string
  default     = ""
}

variable "instance_access_user_password" {
  description = "The access password of the Kafka instance"
  type        = string
  default     = ""
  sensitive   = true
}

variable "instance_enabled_mechanisms" {
  description = "The enabled mechanisms of the Kafka instance"
  type        = list(string)
  default     = ["PLAIN"]
}

variable "port_protocol" {
  description = "The port protocol of the Kafka instance"

  type = object({
    private_plain_enable          = optional(bool, null)
    private_sasl_ssl_enable       = optional(bool, null)
    private_sasl_plaintext_enable = optional(bool, null)
    public_plain_enable           = optional(bool, null)
    public_sasl_ssl_enable        = optional(bool, null)
    public_sasl_plaintext_enable  = optional(bool, null)
  })

  default = {
    private_plain_enable = true
  }
}

# Create Kafka instance
resource "huaweicloud_dms_kafka_instance" "test" {
  name               = var.instance_name
  availability_zones = length(var.availability_zones) == 0 ? try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 1)) : var.availability_zones
  engine_version     = var.instance_engine_version
  flavor_id          = var.instance_flavor_id == "" ? try(data.huaweicloud_dms_kafka_flavors.test[0].flavors[0].id, null) : var.instance_flavor_id
  storage_spec_code  = var.instance_storage_spec_code
  storage_space      = var.instance_storage_space
  broker_num         = var.instance_broker_num
  vpc_id             = huaweicloud_vpc.test.id
  network_id         = huaweicloud_vpc_subnet.test.id
  security_group_id  = huaweicloud_networking_secgroup.test.id
  access_user        = var.instance_access_user_name
  password           = var.instance_access_user_password
  enabled_mechanisms = var.instance_enabled_mechanisms

  dynamic "port_protocol" {
    for_each = [var.port_protocol]

    content {
      private_plain_enable          = port_protocol.value.private_plain_enable
      private_sasl_ssl_enable       = port_protocol.value.private_sasl_ssl_enable
      private_sasl_plaintext_enable = port_protocol.value.private_sasl_plaintext_enable
      public_plain_enable           = port_protocol.value.public_plain_enable
      public_sasl_ssl_enable        = port_protocol.value.public_sasl_ssl_enable
      public_sasl_plaintext_enable  = port_protocol.value.public_sasl_plaintext_enable
    }
  }

  lifecycle {
    ignore_changes = [
      availability_zones,
      flavor_id,
    ]
  }
}
```

**Parameter Description**:

- **name**: Kafka instance name, assigned by referencing input variable instance\_name
- **availability\_zones**: Availability zone list, assigned by referencing input variables or availability zones data source
- **engine\_version**: Engine version, assigned by referencing input variable instance\_engine\_version, default value is "2.7"
- **flavor\_id**: Flavor ID, assigned by referencing input variables or Kafka flavors data source
- **storage\_spec\_code**: Storage specification code, assigned by referencing input variable instance\_storage\_spec\_code, default value is "dms.physical.storage.ultra.v2"
- **storage\_space**: Storage space, assigned by referencing input variable instance\_storage\_space, default value is 600 (GB)
- **broker\_num**: Number of brokers, assigned by referencing input variable instance\_broker\_num, default value is 3
- **vpc\_id**: VPC ID, assigned by referencing the VPC resource
- **network\_id**: Network subnet ID, assigned by referencing the subnet resource
- **security\_group\_id**: Security group ID, assigned by referencing the security group resource
- **access\_user**: Access user name, assigned by referencing input variable instance\_access\_user\_name, optional parameter
- **password**: Access password, assigned by referencing input variable instance\_access\_user\_password, optional parameter
- **enabled\_mechanisms**: Enabled authentication mechanisms, assigned by referencing input variable instance\_enabled\_mechanisms, default value is \["PLAIN"]
- **port\_protocol**: Port protocol configuration, configured through dynamic blocks, supports multiple protocols for private and public network access

### 5. Create Kafka Topic Resource

Add the following script to the TF file (e.g., main.tf) to create a Kafka topic:

```hcl
variable "topic_name" {
  description = "The name of the topic"
  type        = string
}

variable "topic_partitions" {
  description = "The number of partitions of the topic"
  type        = number
  default     = 10
}

variable "topic_replicas" {
  description = "The number of replicas of the topic"
  type        = number
  default     = 3
}

variable "topic_aging_time" {
  description = "The aging time of the topic"
  type        = number
  default     = 72
}

variable "topic_sync_replication" {
  description = "The sync replication of the topic"
  type        = bool
  default     = false
}

variable "topic_sync_flushing" {
  description = "The sync flushing of the topic"
  type        = bool
  default     = false
}

variable "topic_description" {
  description = "The description of the topic"
  type        = string
  default     = null
}

variable "topic_configs" {
  description = "The configs of the topic"

  type = list(object({
    name  = string
    value = string
  }))

  default  = []
  nullable = false
}

# Create Kafka topic
resource "huaweicloud_dms_kafka_topic" "test" {
  instance_id      = huaweicloud_dms_kafka_instance.test.id
  name             = var.topic_name
  partitions       = var.topic_partitions
  replicas         = var.topic_replicas
  aging_time       = var.topic_aging_time
  sync_replication = var.topic_sync_replication
  sync_flushing    = var.topic_sync_flushing
  description      = var.topic_description

  dynamic "configs" {
    for_each = var.topic_configs

    content {
      name  = configs.value.name
      value = configs.value.value
    }
  }
}
```

**Parameter Description**:

- **instance\_id**: Kafka instance ID, assigned by referencing the Kafka instance resource
- **name**: Topic name, assigned by referencing input variable topic\_name
- **partitions**: Number of partitions, assigned by referencing input variable topic\_partitions, default value is 10
- **replicas**: Number of replicas, assigned by referencing input variable topic\_replicas, default value is 3
- **aging\_time**: Aging time, assigned by referencing input variable topic\_aging\_time, default value is 72 (hours)
- **sync\_replication**: Sync replication, assigned by referencing input variable topic\_sync\_replication, default value is false
- **sync\_flushing**: Sync flushing, assigned by referencing input variable topic\_sync\_flushing, default value is false
- **description**: Topic description, assigned by referencing input variable topic\_description, optional parameter
- **configs**: Topic configurations, configured through dynamic blocks, optional parameter

### 6. Create Kafka Message Produce Resource

Add the following script to the TF file (e.g., main.tf) to create a Kafka message produce resource to send messages to the topic:

```hcl
variable "message_body" {
  description = "The body of the message to be sent"
  type        = string
}

variable "message_properties" {
  description = "The properties of the message to be sent"

  type = list(object({
    name  = string
    value = string
  }))

  default  = []
  nullable = false
}

# Create Kafka message produce
resource "huaweicloud_dms_kafka_message_produce" "test" {
  instance_id = huaweicloud_dms_kafka_instance.test.id
  topic       = huaweicloud_dms_kafka_topic.test.name
  body        = var.message_body

  dynamic "property_list" {
    for_each = var.message_properties

    content {
      name  = property_list.value.name
      value = property_list.value.value
    }
  }
}
```

**Parameter Description**:

- **instance\_id**: Kafka instance ID, assigned by referencing the Kafka instance resource
- **topic**: Topic name, assigned by referencing the Kafka topic resource
- **body**: Message body content, assigned by referencing input variable message\_body
- **property\_list**: Message property list, configured through dynamic blocks, optional parameter, supports setting properties such as KEY, PARTITION, etc.

### 7. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and Subnet Configuration
vpc_name    = "tf_test_kafka_instance"
vpc_cidr    = "192.168.0.0/16"
subnet_name = "tf_test_kafka_instance"

# Security Group Configuration
security_group_name = "tf_test_kafka_instance"

# Kafka Instance Configuration
instance_name = "tf_test_kafka_instance"

# Kafka Topic Configuration
topic_name = "tf_test_topic"

# Message Produce Configuration
message_body = "Hello Kafka!"

message_properties = [
  {
    name  = "KEY"
    value = "testKey"
  },
  {
    name  = "PARTITION"
    value = "1"
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `message_body` needs to be set to the message content to be sent
   - `message_properties` can set message properties, such as KEY (message key), PARTITION (partition number), etc.
   - If the Kafka instance enables authentication, you need to configure `instance_access_user_name` and `instance_access_user_password`
   - `instance_access_user_password` needs to be set to a password that meets password complexity requirements
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="message_body=Hello World" -var="topic_name=my_topic"`
2. Environment variables: `export TF_VAR_message_body=Hello World` and `export TF_VAR_topic_name=my_topic`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. Since password contains sensitive information, it is recommended to use environment variables or encrypted variable files for setting. In addition, ensure that the Kafka instance has been created and is in normal status, and the topic has been created, before messages can be successfully produced.

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create Kafka topic message production:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating Kafka instances, topics, and message production
4. Run `terraform show` to view the details of the created message production

> Note: After the message production resource is created, messages will be immediately sent to the specified Kafka topic. If message properties (such as PARTITION) are set, messages will be sent to the specified partition. The instance's availability zones and flavor ID cannot be modified after creation, so they need to be configured correctly during creation. Through lifecycle.ignore\_changes, Terraform can be prevented from modifying these immutable parameters in subsequent updates.

## Reference Information

- [Huawei Cloud Distributed Message Service Kafka Product Documentation](https://support.huaweicloud.com/kafka/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Topic Message Produce](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dms/kafka/topic-message-produce)