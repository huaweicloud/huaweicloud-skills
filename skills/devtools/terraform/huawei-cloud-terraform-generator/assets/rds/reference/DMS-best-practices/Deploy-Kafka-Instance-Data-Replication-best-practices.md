# Deploy Kafka Instance Data Replication

## Application Scenario

Huawei Cloud Distributed Message Service Kafka supports data replication between Kafka instances through Smart Connect, suitable for cross-region data synchronization, disaster recovery, data migration and other scenarios. By configuring Smart Connect tasks, you can establish data replication channels between source and target instances to achieve automatic topic data synchronization. This best practice will introduce how to use Terraform to automatically deploy Kafka instance data replication, including creating multiple Kafka instances, Smart Connect, and Smart Connect tasks.

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
- [Kafka Smart Connect Resource (huaweicloud\_dms\_kafka\_smart\_connect)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dms_kafka_smart_connect)
- [Kafka Smart Connect Task Resource (huaweicloud\_dms\_kafkav2\_smart\_connect\_task)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dms_kafkav2_smart_connect_task)

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
    ├── huaweicloud_dms_kafka_topic
    ├── huaweicloud_dms_kafka_smart_connect
    └── huaweicloud_dms_kafkav2_smart_connect_task
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Data Sources

Add the following script to the TF file (e.g., main.tf) to query availability zone and Kafka flavor information:

```hcl
# Query availability zone information
data "huaweicloud_availability_zones" "test" {
  count = anytrue([for v in var.instance_configurations : length(v.availability_zones) == 0]) ? 1 : 0
}

# Query Kafka flavor information (only query instance configurations without flavor_id)
locals {
  instance_configurations_without_flavor_id = [for v in var.instance_configurations : v if v.flavor_id == ""]
}

data "huaweicloud_dms_kafka_flavors" "test" {
  count = length(local.instance_configurations_without_flavor_id)

  type               = local.instance_configurations_without_flavor_id[count.index].flavor_type
  availability_zones = length(local.instance_configurations_without_flavor_id[count.index].availability_zones) == 0 ? try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 1)) : null
  storage_spec_code  = local.instance_configurations_without_flavor_id[count.index].storage_spec_code
}
```

**Parameter Description**:

- **type**: Flavor type, assigned by referencing the local variable instance\_configurations\_without\_flavor\_id, default value is "cluster" (cluster mode)
- **availability\_zones**: Availability zone list, assigned by referencing input variables or availability zones data source
- **storage\_spec\_code**: Storage specification code, assigned by referencing the local variable, default value is "dms.physical.storage.ultra.v2"

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

### 4. Create Kafka Instance Resources

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create multiple Kafka instance resources (at least 2 instances are required):

```hcl
variable "instance_configurations" {
  description = "The list of configurations for multiple Kafka instances"

  type = list(object({
    name               = string
    availability_zones = optional(list(string), [])
    engine_version     = optional(string, "3.x")
    flavor_id          = optional(string, "")
    flavor_type        = optional(string, "cluster")
    storage_spec_code  = optional(string, "dms.physical.storage.ultra.v2")
    storage_space      = optional(number, 600)
    broker_num         = optional(number, 3)
    access_user        = optional(string, "")
    password           = optional(string, "")
    enabled_mechanisms = optional(list(string), null)

    port_protocol = optional(object({
      private_plain_enable          = optional(bool, true)
      private_sasl_ssl_enable       = optional(bool, null)
      private_sasl_plaintext_enable = optional(bool, null)
    }), {})
  }))

  nullable = false
  default  = []

  validation {
    condition     = length(var.instance_configurations) >= 2
    error_message = "At least two instances are required"
  }
}

# Create multiple Kafka instances (at least 2 instances are required for data replication)
resource "huaweicloud_dms_kafka_instance" "test" {
  count = length(var.instance_configurations)

  name               = var.instance_configurations[count.index].name
  availability_zones = length(var.instance_configurations[count.index].availability_zones) > 0 ? var.instance_configurations[count.index].availability_zones : try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 1))
  engine_version     = var.instance_configurations[count.index].engine_version
  flavor_id          = var.instance_configurations[count.index].flavor_id != "" ? var.instance_configurations[count.index].flavor_id : try(data.huaweicloud_dms_kafka_flavors.test[count.index].flavors[0].id, null)
  storage_spec_code  = var.instance_configurations[count.index].storage_spec_code
  storage_space      = var.instance_configurations[count.index].storage_space
  broker_num         = var.instance_configurations[count.index].broker_num
  vpc_id             = huaweicloud_vpc.test.id
  network_id         = huaweicloud_vpc_subnet.test.id
  security_group_id  = huaweicloud_networking_secgroup.test.id
  access_user        = var.instance_configurations[count.index].access_user
  password           = var.instance_configurations[count.index].password
  enabled_mechanisms = var.instance_configurations[count.index].enabled_mechanisms

  dynamic "port_protocol" {
    for_each = length(var.instance_configurations[count.index].port_protocol) > 0 ? [var.instance_configurations[count.index].port_protocol] : []

    content {
      private_plain_enable          = port_protocol.value.private_plain_enable
      private_sasl_ssl_enable       = port_protocol.value.private_sasl_ssl_enable
      private_sasl_plaintext_enable = port_protocol.value.private_sasl_plaintext_enable
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

- **count**: Creation count, assigned by referencing the length of input variable instance\_configurations, at least 2 instances are required
- **name**: Kafka instance name, assigned by referencing input variable instance\_configurations
- **availability\_zones**: Availability zone list, assigned by referencing input variables or availability zones data source
- **engine\_version**: Engine version, assigned by referencing input variables, default value is "3.x"
- **flavor\_id**: Flavor ID, assigned by referencing input variables or Kafka flavors data source
- **storage\_spec\_code**: Storage specification code, assigned by referencing input variables, default value is "dms.physical.storage.ultra.v2"
- **storage\_space**: Storage space, assigned by referencing input variables, default value is 600 (GB)
- **broker\_num**: Number of brokers, assigned by referencing input variables, default value is 3
- **vpc\_id**: VPC ID, assigned by referencing the VPC resource
- **network\_id**: Network subnet ID, assigned by referencing the subnet resource
- **security\_group\_id**: Security group ID, assigned by referencing the security group resource
- **access\_user**: Access user name, assigned by referencing input variables, optional parameter
- **password**: Access password, assigned by referencing input variables, optional parameter
- **enabled\_mechanisms**: Enabled authentication mechanisms, assigned by referencing input variables, optional parameter, supports "SCRAM-SHA-512", etc.
- **port\_protocol**: Port protocol configuration, configured through dynamic blocks, optional parameter

### 5. Create Kafka Topic Resource (Optional)

Add the following script to the TF file (e.g., main.tf) to create a Kafka topic (if task\_topics is not specified, create a topic):

```hcl
variable "task_topics" {
  description = "The topics of the Smart Connect task"
  type        = list(string)
  default     = []
}

variable "topic_name" {
  description = "The name of the Kafka topic"
  type        = string
  default     = ""
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

# Create Kafka topic (only create when task_topics is not specified)
resource "huaweicloud_dms_kafka_topic" "test" {
  count = length(var.task_topics) == 0 ? 1 : 0

  instance_id      = huaweicloud_dms_kafka_instance.test[0].id
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

- **count**: Creation count, create 1 topic when task\_topics is empty, otherwise do not create
- **instance\_id**: Kafka instance ID, assigned by referencing the first Kafka instance resource
- **name**: Topic name, assigned by referencing input variable topic\_name
- **partitions**: Number of partitions, assigned by referencing input variable topic\_partitions, default value is 10
- **replicas**: Number of replicas, assigned by referencing input variable topic\_replicas, default value is 3
- **aging\_time**: Aging time, assigned by referencing input variable topic\_aging\_time, default value is 72 (hours)
- **sync\_replication**: Sync replication, assigned by referencing input variable topic\_sync\_replication, default value is false
- **sync\_flushing**: Sync flushing, assigned by referencing input variable topic\_sync\_flushing, default value is false
- **description**: Topic description, assigned by referencing input variable topic\_description, optional parameter
- **configs**: Topic configurations, configured through dynamic blocks, optional parameter

### 6. Create Smart Connect Resource

Add the following script to the TF file (e.g., main.tf) to create Smart Connect:

```hcl
variable "smart_connect_storage_spec_code" {
  description = "The storage specification code of the Smart Connect"
  type        = string
  default     = null
}

variable "smart_connect_bandwidth" {
  description = "The bandwidth of the Smart Connect"
  type        = string
  default     = null
}

variable "smart_connect_node_count" {
  description = "The number of nodes of the Smart Connect"
  type        = number
  default     = 2
}

# Create Smart Connect
resource "huaweicloud_dms_kafka_smart_connect" "test" {
  instance_id       = huaweicloud_dms_kafka_instance.test[0].id
  storage_spec_code = var.smart_connect_storage_spec_code
  bandwidth         = var.smart_connect_bandwidth
  node_count        = var.smart_connect_node_count
}
```

**Parameter Description**:

- **instance\_id**: Kafka instance ID, assigned by referencing the first Kafka instance resource
- **storage\_spec\_code**: Storage specification code, assigned by referencing input variable smart\_connect\_storage\_spec\_code, optional parameter
- **bandwidth**: Bandwidth, assigned by referencing input variable smart\_connect\_bandwidth, optional parameter
- **node\_count**: Number of nodes, assigned by referencing input variable smart\_connect\_node\_count, default value is 2

### 7. Create Smart Connect Task Resource

Add the following script to the TF file (e.g., main.tf) to create a Smart Connect task to achieve data replication between instances:

```hcl
variable "task_name" {
  description = "The name of the Smart Connect task"
  type        = string
}

variable "task_start_later" {
  description = "The start later of the Smart Connect task"
  type        = bool
  default     = false
}

variable "task_direction" {
  description = "The direction of the Smart Connect task"
  type        = string
  default     = "two-way"
}

variable "task_replication_factor" {
  description = "The replication factor of the Smart Connect task"
  type        = number
  default     = 3
}

variable "task_task_num" {
  description = "The number of tasks of the Smart Connect task"
  type        = number
  default     = 2
}

variable "task_provenance_header_enabled" {
  description = "The provenance header enabled of the Smart Connect task"
  type        = bool
  default     = false
}

variable "task_sync_consumer_offsets_enabled" {
  description = "The sync consumer offsets enabled of the Smart Connect task"
  type        = bool
  default     = false
}

variable "task_rename_topic_enabled" {
  description = "The rename topic enabled of the Smart Connect task"
  type        = bool
  default     = true
}

variable "task_consumer_strategy" {
  description = "The consumer strategy of the Smart Connect task"
  type        = string
  default     = "latest"
}

variable "task_compression_type" {
  description = "The compression type of the Smart Connect task"
  type        = string
  default     = "none"
}

variable "task_topics_mapping" {
  description = "The topics mapping of the Smart Connect task"
  type        = list(string)
  default     = []
}

# Create Smart Connect task
resource "huaweicloud_dms_kafkav2_smart_connect_task" "test" {
  instance_id = huaweicloud_dms_kafka_instance.test[0].id
  task_name   = var.task_name
  source_type = "KAFKA_REPLICATOR_SOURCE"
  start_later = var.task_start_later
  topics      = length(var.task_topics) > 0 ? var.task_topics : huaweicloud_dms_kafka_topic.test[*].name

  source_task {
    peer_instance_id              = huaweicloud_dms_kafka_instance.test[1].id
    direction                     = var.task_direction
    replication_factor            = var.task_replication_factor
    task_num                      = var.task_task_num
    provenance_header_enabled     = var.task_provenance_header_enabled
    sync_consumer_offsets_enabled = var.task_sync_consumer_offsets_enabled
    rename_topic_enabled          = var.task_rename_topic_enabled
    consumer_strategy             = var.task_consumer_strategy
    compression_type              = var.task_compression_type
    topics_mapping                = var.task_topics_mapping
    security_protocol             = try(huaweicloud_dms_kafka_instance.test[1].port_protocol[0].private_sasl_ssl_enable, false) ? "SASL_SSL" : try(huaweicloud_dms_kafka_instance.test[1].port_protocol[0].private_sasl_plaintext_enable, false) ? "PLAINTEXT" : null
    sasl_mechanism                = try(tolist(huaweicloud_dms_kafka_instance.test[1].enabled_mechanisms)[0], null)
    user_name                     = try(huaweicloud_dms_kafka_instance.test[1].access_user, null)
    password                      = try(huaweicloud_dms_kafka_instance.test[1].password, null)
  }

  depends_on = [huaweicloud_dms_kafka_smart_connect.test]
}
```

**Parameter Description**:

- **instance\_id**: Kafka instance ID, assigned by referencing the first Kafka instance resource
- **task\_name**: Task name, assigned by referencing input variable task\_name
- **source\_type**: Source type, set to "KAFKA\_REPLICATOR\_SOURCE" (Kafka replicator source)
- **start\_later**: Whether to start later, assigned by referencing input variable task\_start\_later, default value is false
- **topics**: Topic list, assigned by referencing input variable task\_topics or topic resources
- **source\_task.peer\_instance\_id**: Peer instance ID, assigned by referencing the second Kafka instance resource
- **source\_task.direction**: Replication direction, assigned by referencing input variable task\_direction, default value is "two-way"
- **source\_task.replication\_factor**: Replication factor, assigned by referencing input variable task\_replication\_factor, default value is 3
- **source\_task.task\_num**: Number of tasks, assigned by referencing input variable task\_task\_num, default value is 2
- **source\_task.provenance\_header\_enabled**: Whether to enable provenance header, assigned by referencing input variable task\_provenance\_header\_enabled, default value is false
- **source\_task.sync\_consumer\_offsets\_enabled**: Whether to sync consumer offsets, assigned by referencing input variable task\_sync\_consumer\_offsets\_enabled, default value is false
- **source\_task.rename\_topic\_enabled**: Whether to rename topic, assigned by referencing input variable task\_rename\_topic\_enabled, default value is true
- **source\_task.consumer\_strategy**: Consumer strategy, assigned by referencing input variable task\_consumer\_strategy, default value is "latest"
- **source\_task.compression\_type**: Compression type, assigned by referencing input variable task\_compression\_type, default value is "none"
- **source\_task.topics\_mapping**: Topic mapping, assigned by referencing input variable task\_topics\_mapping, optional parameter
- **source\_task.security\_protocol**: Security protocol, automatically determined based on peer instance port protocol configuration
- **source\_task.sasl\_mechanism**: SASL mechanism, automatically determined based on peer instance authentication mechanism
- **source\_task.user\_name**: User name, obtained from peer instance
- **source\_task.password**: Password, obtained from peer instance

### 8. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and Subnet Configuration
vpc_name    = "tf_test_kafka_instance"
vpc_cidr    = "192.168.0.0/16"
subnet_name = "tf_test_kafka_instance"

# Security Group Configuration
security_group_name = "tf_test_kafka_instance"

# Smart Connect Task Configuration
task_name  = "tf_test_kafka_task"
topic_name = "tf_test_kafka_topic"

# Kafka Instance Configuration (at least 2 instances are required)
instance_configurations = [
  {
    name = "tf_test_instance"
  },
  {
    name               = "tf_test_peer_instance"
    access_user        = "admin"
    password           = "YourKafkaInstancePassword!"
    enabled_mechanisms = ["SCRAM-SHA-512"]
    port_protocol      = {
      private_plain_enable    = false
      private_sasl_ssl_enable = true
    }
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `instance_configurations` needs to configure at least 2 instances, the first instance as the target instance, the second instance as the source instance
   - If the source instance enables SASL authentication, you need to configure `access_user`, `password` and `enabled_mechanisms`
   - `password` needs to be set to a password that meets password complexity requirements
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="task_name=my_task" -var="vpc_name=my_vpc"`
2. Environment variables: `export TF_VAR_task_name=my_task` and `export TF_VAR_vpc_name=my_vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. Since password contains sensitive information, it is recommended to use environment variables or encrypted variable files for setting. In addition, ensure network connectivity between source and target instances, and the authentication configuration of the source instance is correct.

### 9. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create Kafka instance data replication:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating Kafka instances, Smart Connect, and Smart Connect tasks
4. Run `terraform show` to view the details of the created Smart Connect task

> Note: After the Smart Connect task is created, data replication will automatically start according to the configuration. If `start_later=true` is set, the task will not start immediately after creation and needs to be started manually. The instance's availability zones and flavor ID cannot be modified after creation, so they need to be configured correctly during creation. Through lifecycle.ignore\_changes, Terraform can be prevented from modifying these immutable parameters in subsequent updates.

## Reference Information

- [Huawei Cloud Distributed Message Service Kafka Product Documentation](https://support.huaweicloud.com/kafka/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Instance Data Replication](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dms/kafka/replicate-instance-data)
