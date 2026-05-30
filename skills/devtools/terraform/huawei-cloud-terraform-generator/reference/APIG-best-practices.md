# Create Kafka Forward Plugin

## Application Scenario

API Gateway's Kafka forward plugin is a plugin used to asynchronously forward HTTP API requests to Kafka topics, enabling asynchronous processing of API requests and message queue integration. The Kafka forward plugin supports configuring Kafka connection information, topics, message keys, retry strategies, and other parameters, helping you achieve flexible API request forwarding management. By configuring the Kafka forward plugin, API requests can be converted into Kafka messages, enabling asynchronous processing of requests and decoupling of subsequent processing flows, improving system scalability and reliability. This best practice will introduce how to use Terraform to automatically create API Gateway's Kafka forward plugin.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [DMS Kafka Flavor Query Data Source (data.huaweicloud\_dms\_kafka\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/dms_kafka_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [API Gateway Instance Resource (huaweicloud\_apig\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/apig_instance)
- [DMS Kafka Instance Resource (huaweicloud\_dms\_kafka\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dms_kafka_instance)
- [DMS Kafka Topic Resource (huaweicloud\_dms\_kafka\_topic)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dms_kafka_topic)
- [API Gateway Plugin Resource (huaweicloud\_apig\_plugin)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/apig_plugin)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── huaweicloud_apig_instance
    └── huaweicloud_dms_kafka_instance

data.huaweicloud_dms_kafka_flavors
    └── huaweicloud_dms_kafka_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        ├── huaweicloud_apig_instance
        └── huaweicloud_dms_kafka_instance

huaweicloud_networking_secgroup
    ├── huaweicloud_apig_instance
    └── huaweicloud_dms_kafka_instance

huaweicloud_dms_kafka_instance
    ├── huaweicloud_dms_kafka_topic
    └── huaweicloud_apig_plugin

huaweicloud_apig_instance
    └── huaweicloud_apig_plugin
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zone Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to create API Gateway instances and DMS Kafka instances:

```hcl
variable "availability_zones" {
  description = "The availability zones to which the instance belongs"
  type        = list(string)
  default     = []
  nullable    = false
}

variable "availability_zones_count" {
  description = "The number of availability zones to which the instance belongs"
  type        = number
  default     = 1
}

# Query all availability zone information in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used to create API Gateway instances and DMS Kafka instances
data "huaweicloud_availability_zones" "test" {
  count = length(var.availability_zones) > 0 ? 0 : 1
}
```

**Parameter Description**:

- **count**: The number of data sources to create, used to control whether to execute the availability zone list query data source, only created when `var.availability_zones` is empty (i.e., execute the availability zone list query)

### 3. Create VPC Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC resource:

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

# Create VPC resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used to deploy API Gateway instances and DMS Kafka instances
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: The VPC name, assigned by referencing the input variable vpc\_name
- **cidr**: The VPC CIDR block, assigned by referencing the input variable vpc\_cidr, default value is "192.168.0.0/16"

### 4. Create VPC Subnet Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "The name of the subnet"
  type        = string
}

variable "subnet_cidr" {
  description = "The CIDR block of the subnet"
  type        = string
  default     = ""
  nullable    = false
}

variable "subnet_gateway_ip" {
  description = "The gateway IP address of the subnet"
  type        = string
  default     = ""
  nullable    = false
}

# Create VPC subnet resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used to deploy API Gateway instances and DMS Kafka instances
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr != "" ? var.subnet_cidr : cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0)
  gateway_ip = var.subnet_gateway_ip != "" ? var.subnet_gateway_ip : cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1)
}
```

**Parameter Description**:

- **vpc\_id**: The ID of the VPC to which the subnet belongs, referencing the ID of the previously created VPC resource (huaweicloud\_vpc.test)
- **name**: The subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: The subnet CIDR block, assigned by referencing the input variable subnet\_cidr, automatically calculated when the value is an empty string
- **gateway\_ip**: The subnet gateway IP, assigned by referencing the input variable subnet\_gateway\_ip, automatically calculated when the value is an empty string

### 5. Create Security Group Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create security group resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used to deploy API Gateway instances and DMS Kafka instances
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: The security group name, assigned by referencing the input variable security\_group\_name
- **delete\_default\_rules**: Whether to delete default rules, set to true

### 6. Create API Gateway Instance Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an API Gateway instance resource:

```hcl
variable "instance_name" {
  description = "The name of the APIG instance"
  type        = string
}

variable "instance_edition" {
  description = "The edition of the APIG instance"
  type        = string
  default     = "BASIC"
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project"
  type        = string
  default     = null
}

# Create API Gateway instance resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_apig_instance" "test" {
  name                  = var.instance_name
  edition               = var.instance_edition
  vpc_id                = huaweicloud_vpc.test.id
  subnet_id             = huaweicloud_vpc_subnet.test.id
  security_group_id     = huaweicloud_networking_secgroup.test.id
  enterprise_project_id = var.enterprise_project_id
  availability_zones    = length(var.availability_zones) > 0 ? var.availability_zones : try(slice(data.huaweicloud_availability_zones.test[0].names, 0, var.availability_zones_count), null)
}
```

**Parameter Description**:

- **name**: The API Gateway instance name, assigned by referencing the input variable instance\_name
- **edition**: The API Gateway instance edition, assigned by referencing the input variable instance\_edition, default value is "BASIC"
- **vpc\_id**: The VPC ID, referencing the ID of the previously created VPC resource (huaweicloud\_vpc.test)
- **subnet\_id**: The subnet ID, referencing the ID of the previously created VPC subnet resource (huaweicloud\_vpc\_subnet.test)
- **security\_group\_id**: The security group ID, referencing the ID of the previously created security group resource (huaweicloud\_networking\_secgroup.test)
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, default value is null
- **availability\_zones**: The availability zones list, uses the input variable availability\_zones when it is not empty, otherwise assigned based on the return results of the availability zones query data source (data.huaweicloud\_availability\_zones)

### 7. Query DMS Kafka Flavor Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to create DMS Kafka instances:

```hcl
variable "kafka_instance_flavor_id" {
  description = "The flavor ID of the DMS Kafka instance"
  type        = string
  default     = ""
  nullable    = false
}

variable "kafka_instance_flavor_type" {
  description = "The flavor type of the DMS Kafka instance"
  type        = string
  default     = "cluster"
}

variable "kafka_instance_storage_spec_code" {
  description = "The storage spec code of the DMS Kafka instance"
  type        = string
  default     = "dms.physical.storage.high.v2"
}

# Query DMS Kafka flavor information of the specified type in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used to create DMS Kafka instances
data "huaweicloud_dms_kafka_flavors" "test" {
  count = var.kafka_instance_flavor_id != "" ? 0 : 1

  type               = var.kafka_instance_flavor_type
  storage_spec_code  = var.kafka_instance_storage_spec_code
  availability_zones = length(var.availability_zones) > 0 ? var.availability_zones : try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 3))
}
```

**Parameter Description**:

- **count**: The number of data sources to create, used to control whether to execute the DMS Kafka flavor query data source, only created when `var.kafka_instance_flavor_id` is empty (i.e., execute the flavor query)
- **type**: The flavor type, assigned by referencing the input variable kafka\_instance\_flavor\_type, default value is "cluster"
- **storage\_spec\_code**: The storage spec code, assigned by referencing the input variable kafka\_instance\_storage\_spec\_code
- **availability\_zones**: The availability zones list, uses the input variable availability\_zones when it is not empty, otherwise assigned based on the return results of the availability zones query data source (data.huaweicloud\_availability\_zones)

### 8. Create DMS Kafka Instance Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a DMS Kafka instance resource:

```hcl
variable "kafka_instance_name" {
  description = "The name of the DMS Kafka instance"
  type        = string
}

variable "kafka_instance_description" {
  description = "The description of the DMS Kafka instance"
  type        = string
  default     = ""
}

variable "kafka_instance_ssl_enable" {
  description = "Whether to enable SSL for the DMS Kafka instance"
  type        = bool
  default     = false
}

variable "kafka_instance_engine_version" {
  description = "The engine version of the DMS Kafka instance"
  type        = string
}

variable "kafka_instance_storage_space" {
  description = "The storage space of the DMS Kafka instance in GB"
  type        = number
}

variable "kafka_instance_broker_num" {
  description = "The number of brokers for the DMS Kafka instance"
  type        = number
}

variable "kafka_charging_mode" {
  description = "The charging mode of the DMS Kafka instance. Options: prePaid, postPaid"
  type        = string
  default     = "prePaid"
}

variable "kafka_period_unit" {
  description = "The period unit of the DMS Kafka instance. Options: month, year"
  type        = string
  default     = "month"
}

variable "kafka_period" {
  description = "The period of the DMS Kafka instance"
  type        = number
  default     = 1
}

variable "kafka_auto_new" {
  description = "Whether to enable auto renewal for the DMS Kafka instance"
  type        = string
  default     = "false"
}

variable "kafka_instance_user_name" {
  description = "The access user name for the DMS Kafka instance"
  type        = string
  sensitive   = true
}

variable "kafka_instance_user_password" {
  description = "The access user password for the DMS Kafka instance"
  type        = string
  sensitive   = true
}

# Create DMS Kafka instance resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_dms_kafka_instance" "test" {
  name               = var.kafka_instance_name
  description        = var.kafka_instance_description
  availability_zones = length(var.availability_zones) > 0 ? var.availability_zones : try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 3))
  vpc_id             = huaweicloud_vpc.test.id
  network_id         = huaweicloud_vpc_subnet.test.id
  security_group_id  = huaweicloud_networking_secgroup.test.id
  ssl_enable         = var.kafka_instance_ssl_enable
  flavor_id          = var.kafka_instance_flavor_id != "" ? var.kafka_instance_flavor_id : try(data.huaweicloud_dms_kafka_flavors.test[0].flavors[0].id, null)
  engine_version     = var.kafka_instance_engine_version
  storage_spec_code  = var.kafka_instance_storage_spec_code
  storage_space      = var.kafka_instance_storage_space
  broker_num         = var.kafka_instance_broker_num
  charging_mode      = var.kafka_charging_mode
  period_unit        = var.kafka_period_unit
  period             = var.kafka_period
  auto_renew         = var.kafka_auto_new
  access_user        = var.kafka_instance_user_name
  password           = var.kafka_instance_user_password

  lifecycle {
    ignore_changes = [
      access_user,
      availability_zones,
      flavor_id,
    ]
  }
}
```

**Parameter Description**:

- **name**: The DMS Kafka instance name, assigned by referencing the input variable kafka\_instance\_name
- **description**: The DMS Kafka instance description, assigned by referencing the input variable kafka\_instance\_description, default value is an empty string
- **availability\_zones**: The availability zones list, uses the input variable availability\_zones when it is not empty, otherwise assigned based on the return results of the availability zones query data source (data.huaweicloud\_availability\_zones)
- **vpc\_id**: The VPC ID, referencing the ID of the previously created VPC resource (huaweicloud\_vpc.test)
- **network\_id**: The network ID, referencing the ID of the previously created VPC subnet resource (huaweicloud\_vpc\_subnet.test)
- **security\_group\_id**: The security group ID, referencing the ID of the previously created security group resource (huaweicloud\_networking\_secgroup.test)
- **ssl\_enable**: Whether to enable SSL, assigned by referencing the input variable kafka\_instance\_ssl\_enable, default value is false
- **flavor\_id**: The flavor ID, uses the input variable kafka\_instance\_flavor\_id when it is not empty, otherwise assigned based on the return results of the DMS Kafka flavor query data source (data.huaweicloud\_dms\_kafka\_flavors)
- **engine\_version**: The engine version, assigned by referencing the input variable kafka\_instance\_engine\_version
- **storage\_spec\_code**: The storage spec code, assigned by referencing the input variable kafka\_instance\_storage\_spec\_code
- **storage\_space**: The storage space (unit: GB), assigned by referencing the input variable kafka\_instance\_storage\_space
- **broker\_num**: The number of brokers, assigned by referencing the input variable kafka\_instance\_broker\_num
- **charging\_mode**: The billing mode, assigned by referencing the input variable kafka\_charging\_mode, default value is "prePaid"
- **period\_unit**: The billing period unit, assigned by referencing the input variable kafka\_period\_unit, default value is "month"
- **period**: The billing period, assigned by referencing the input variable kafka\_period, default value is 1
- **auto\_renew**: Whether to enable auto renewal, assigned by referencing the input variable kafka\_auto\_new, default value is "false"
- **access\_user**: The access user name, assigned by referencing the input variable kafka\_instance\_user\_name
- **password**: The access password, assigned by referencing the input variable kafka\_instance\_user\_password

### 9. Create DMS Kafka Topic Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a DMS Kafka topic resource:

```hcl
variable "kafka_topic_name" {
  description = "The name of the Kafka topic to receive messages"
  type        = string
}

variable "kafka_topic_partitions" {
  description = "The number of partitions for the Kafka topic"
  type        = number
  default     = 1
}

# Create DMS Kafka topic resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_dms_kafka_topic" "test" {
  instance_id = huaweicloud_dms_kafka_instance.test.id
  name        = var.kafka_topic_name
  partitions  = var.kafka_topic_partitions
}
```

**Parameter Description**:

- **instance\_id**: The Kafka instance ID, referencing the ID of the previously created DMS Kafka instance resource (huaweicloud\_dms\_kafka\_instance.test)
- **name**: The topic name, assigned by referencing the input variable kafka\_topic\_name
- **partitions**: The number of partitions, assigned by referencing the input variable kafka\_topic\_partitions, default value is 1

### 10. Create API Gateway Kafka Forward Plugin Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an API Gateway Kafka forward plugin resource:

```hcl
variable "plugin_name" {
  description = "The name of the Kafka forward plugin"
  type        = string
}

variable "plugin_description" {
  description = "The description of the Kafka forward plugin"
  type        = string
  default     = null
}

variable "kafka_security_protocol" {
  description = "The security protocol for Kafka connection. Options: PLAINTEXT, SASL_PLAINTEXT, SASL_SSL, SSL"
  type        = string
  default     = "PLAINTEXT"
  nullable    = false

  validation {
    condition     = contains(["PLAINTEXT", "SASL_PLAINTEXT", "SASL_SSL", "SSL"], var.kafka_security_protocol)
    error_message = "kafka_security_protocol must be one of: PLAINTEXT, SASL_PLAINTEXT, SASL_SSL, SSL."
  }
}

variable "kafka_message_key" {
  description = "The message key extraction strategy. Can be a static value or a variable expression like $context.requestId"
  type        = string
  default     = ""
}

variable "kafka_max_retry_count" {
  description = "The maximum number of retry attempts for failed message sends"
  type        = number
  default     = 3
}

variable "kafka_retry_backoff" {
  description = "The backoff time in seconds between retries"
  type        = number
  default     = 10
}

variable "kafka_sasl_mechanisms" {
  description = "The SASL mechanism for authentication. Options: PLAIN, SCRAM-SHA-256, SCRAM-SHA-512"
  type        = string
  default     = "PLAIN"

  validation {
    condition     = contains(["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"], var.kafka_sasl_mechanisms)
    error_message = "kafka_sasl_mechanisms must be one of: PLAIN, SCRAM-SHA-256, SCRAM-SHA-512."
  }
}

variable "kafka_sasl_username" {
  description = "The SASL username for authentication (leave empty to use kafka_access_user)"
  type        = string
  default     = ""
  sensitive   = true
  nullable    = false
}

variable "kafka_access_user" {
  description = "The access user for Kafka authentication (used when kafka_sasl_username is empty and security_protocol is not PLAINTEXT)"
  type        = string
  default     = ""
  sensitive   = true
  nullable    = false
}

variable "kafka_sasl_password" {
  description = "The SASL password for authentication (leave empty to use kafka_password)"
  type        = string
  default     = ""
  sensitive   = true
  nullable    = false
}

variable "kafka_password" {
  description = "The password for Kafka authentication (used when kafka_sasl_password is empty and security_protocol is not PLAINTEXT)"
  type        = string
  default     = ""
  sensitive   = true
  nullable    = false
}

variable "kafka_ssl_ca_content" {
  description = "The SSL CA certificate content for SSL/TLS encrypted connections"
  type        = string
  default     = ""
  sensitive   = true
  nullable    = false
}

# Create API Gateway Kafka forward plugin resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_apig_plugin" "test" {
  instance_id = huaweicloud_apig_instance.test.id
  name        = var.plugin_name
  description = var.plugin_description
  type        = "kafka_log"

  content = jsonencode({
    broker_list     = var.kafka_security_protocol == "PLAINTEXT" ? (split(",", huaweicloud_dms_kafka_instance.test.port_protocol[0].private_plain_address)) : var.kafka_security_protocol == "SASL_PLAINTEXT" ? (split(",",huaweicloud_dms_kafka_instance.test.port_protocol[0].private_sasl_plaintext_address)) : (split(",", huaweicloud_dms_kafka_instance.test.port_protocol[0].private_sasl_ssl_address))
    topic           = var.kafka_topic_name
    key             = var.kafka_message_key
    max_retry_count = var.kafka_max_retry_count
    retry_backoff   = var.kafka_retry_backoff

    sasl_config = {
      security_protocol = var.kafka_security_protocol
      sasl_mechanisms   = var.kafka_sasl_mechanisms
      sasl_username     = var.kafka_sasl_username != "" ? nonsensitive(var.kafka_sasl_username) : (var.kafka_security_protocol == "PLAINTEXT" ? "" : nonsensitive(var.kafka_access_user))
      sasl_password     = var.kafka_sasl_password != "" ? nonsensitive(var.kafka_sasl_password) : (var.kafka_security_protocol == "PLAINTEXT" ? "" : nonsensitive(var.kafka_password))
      ssl_ca_content    = var.kafka_ssl_ca_content != "" ? nonsensitive(var.kafka_ssl_ca_content) : ""
    }
  })

  lifecycle {
    ignore_changes = [
      content,
    ]
  }
}
```

**Parameter Description**:

- **instance\_id**: The API Gateway instance ID, referencing the ID of the previously created API Gateway instance resource (huaweicloud\_apig\_instance.test)
- **name**: The plugin name, assigned by referencing the input variable plugin\_name
- **description**: The plugin description, assigned by referencing the input variable plugin\_description, default value is null
- **type**: The plugin type, set to "kafka\_log" (indicating Kafka log forward plugin)
- **content**: The plugin configuration content, encoded as a JSON string using the jsonencode function, where:
  - **broker\_list**: The Kafka Broker list, obtained from the DMS Kafka instance's port\_protocol attribute based on the security protocol type
  - **topic**: The Kafka topic name, assigned by referencing the input variable kafka\_topic\_name
  - **key**: The message key extraction strategy, assigned by referencing the input variable kafka\_message\_key, can be a static value or a variable expression (e.g., $context.requestId)
  - **max\_retry\_count**: The maximum number of retries, assigned by referencing the input variable kafka\_max\_retry\_count, default value is 3
  - **retry\_backoff**: The retry backoff time (unit: seconds), assigned by referencing the input variable kafka\_retry\_backoff, default value is 10
  - **sasl\_config.security\_protocol**: The security protocol, assigned by referencing the input variable kafka\_security\_protocol
  - **sasl\_config.sasl\_mechanisms**: The SASL mechanism, assigned by referencing the input variable kafka\_sasl\_mechanisms
  - **sasl\_config.sasl\_username**: The SASL username, uses kafka\_sasl\_username when it is not empty, otherwise uses kafka\_access\_user when the security protocol is not PLAINTEXT
  - **sasl\_config.sasl\_password**: The SASL password, uses kafka\_sasl\_password when it is not empty, otherwise uses kafka\_password when the security protocol is not PLAINTEXT
  - **sasl\_config.ssl\_ca\_content**: The SSL CA certificate content, assigned by referencing the input variable kafka\_ssl\_ca\_content

### 11. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC Configuration
vpc_name    = "tf_test_apig_kafka_forward_plugin"
vpc_cidr    = "192.168.0.0/16"
subnet_name = "tf_test_apig_kafka_forward_plugin"

# Security Group Configuration
security_group_name = "tf_test_apig_kafka_forward_plugin"

# API Gateway Instance Configuration
instance_name    = "tf_test_apig_kafka_forward_plugin"
instance_edition = "BASIC"

# DMS Kafka Instance Configuration
kafka_instance_name              = "tf_test_apig_kafka_forward_plugin"
kafka_instance_engine_version   = "2.7"
kafka_instance_storage_space    = 600
kafka_instance_broker_num       = 3
kafka_instance_user_name         = "user"
kafka_instance_user_password     = "YourPassword123"

# DMS Kafka Topic Configuration
kafka_topic_name       = "tf_test_apig_kafka_forward_plugin"
kafka_topic_partitions = 1

# API Gateway Plugin Configuration
plugin_name            = "tf_test_apig_kafka_forward_plugin"
plugin_description     = "This is a Kafka forward plugin created by Terraform"
kafka_security_protocol = "PLAINTEXT"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=test-vpc" -var="instance_name=test-instance"`
2. Environment variables: `export TF_VAR_vpc_name=test-vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 12. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the API Gateway Kafka forward plugin
4. Run `terraform show` to view the details of the created API Gateway Kafka forward plugin

## Reference Information

- [Huawei Cloud API Gateway Product Documentation](https://support.huaweicloud.com/apig/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For API Gateway Kafka Forward Plugin](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/apig/kafka-forward-plugin)

# Create Proxy Cache Plugin

## Application Scenario

The proxy cache plugin of API Gateway is a plugin used to cache API response data, which can significantly improve API response speed and reduce the load on backend services. The proxy cache plugin supports configuring cache keys, cache policies, TTL (Time To Live), and other parameters to help you achieve flexible API response cache management. By properly configuring cache policies, you can reduce the pressure of repeated requests on backend services and improve the overall system performance and availability. This best practice will introduce how to use Terraform to automatically create the proxy cache plugin for API Gateway.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [API Gateway Instance Resource (huaweicloud\_apig\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/apig_instance)
- [API Gateway Plugin Resource (huaweicloud\_apig\_plugin)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/apig_plugin)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── huaweicloud_apig_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_apig_instance

huaweicloud_networking_secgroup
    └── huaweicloud_apig_instance

huaweicloud_apig_instance
    └── huaweicloud_apig_plugin
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration introduction, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy).

### 2. Query Availability Zones Required for API Gateway Instance Resource Creation Through Data Source

Add the following script to the TF file (such as main.tf) to inform Terraform to perform a data source query, the query results are used to create API Gateway instances:

```hcl
variable "availability_zones" {
  description = "The availability zones to which the instance belongs"
  type        = list(string)
  default     = []
  nullable    = false
}

variable "availability_zones_count" {
  description = "The number of availability zones to which the instance belongs"
  type        = number
  default     = 1
}

# Get all availability zone information in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating API Gateway instances
data "huaweicloud_availability_zones" "test" {
  count = length(var.availability_zones) == 0 ? 1 : 0
}
```

**Parameter Description**:

- **count**: The number of data source creations, used to control whether to execute the availability zone list query data source. The data source is only created (i.e., the availability zone list query is executed) when `var.availability_zones` is empty.

### 3. Create VPC Resource

Add the following script to the TF file (such as main.tf) to inform Terraform to create VPC resources:

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

# Create VPC resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for deploying API Gateway instances
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing input variable vpc\_name
- **cidr**: VPC CIDR network segment, assigned by referencing input variable vpc\_cidr

### 4. Create VPC Subnet Resource

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
  description = "The gateway IP address of the subnet"
  type        = string
  default     = ""
}

# Create VPC subnet resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for deploying API Gateway instances
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}
```

**Parameter Description**:

- **vpc\_id**: The ID of the VPC to which the subnet belongs, referencing the ID of the VPC resource created earlier
- **name**: Subnet name, assigned by referencing input variable subnet\_name
- **cidr**: Subnet network segment. When subnet\_cidr is empty, it automatically calculates the subnet network segment from the VPC's CIDR; otherwise, it uses the value of input variable subnet\_cidr
- **gateway\_ip**: Gateway IP address. When subnet\_gateway\_ip is empty, it automatically gets the gateway IP from the calculated subnet network segment; otherwise, it uses the value of input variable subnet\_gateway\_ip

### 5. Create Security Group Resource

Add the following script to the TF file to inform Terraform to create security group resources:

```hcl
variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create security group resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for deploying API Gateway instances
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing input variable security\_group\_name
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default rules

### 6. Create API Gateway Instance Resource

Add the following script to the TF file to inform Terraform to create API Gateway instance resources:

```hcl
variable "instance_name" {
  description = "The name of the APIG instance"
  type        = string
}

variable "instance_edition" {
  description = "The edition of the APIG instance"
  type        = string
  default     = "BASIC"
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project"
  type        = string
  default     = null
}

# Create API Gateway instance resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing)
resource "huaweicloud_apig_instance" "test" {
  name                  = var.instance_name
  edition               = var.instance_edition
  vpc_id                = huaweicloud_vpc.test.id
  subnet_id             = huaweicloud_vpc_subnet.test.id
  security_group_id     = huaweicloud_networking_secgroup.test.id
  availability_zones    = length(var.availability_zones) == 0 ? try(slice(data.huaweicloud_availability_zones.test[0].names, 0, var.availability_zones_count), null) : var.availability_zones
  enterprise_project_id = var.enterprise_project_id
}
```

**Parameter Description**:

- **name**: API Gateway instance name, assigned by referencing input variable instance\_name
- **edition**: Instance specification, assigned by referencing input variable instance\_edition, default value is "BASIC"
- **vpc\_id**: VPC ID, referencing the ID of the VPC resource created earlier
- **subnet\_id**: Subnet ID, referencing the ID of the subnet resource created earlier
- **security\_group\_id**: Security group ID, referencing the ID of the security group resource created earlier
- **availability\_zones**: Availability zone list. When availability\_zones is empty, it uses the result of the availability zone list query data source; otherwise, it uses the value of input variable availability\_zones
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing input variable enterprise\_project\_id

### 7. Create API Gateway Plugin Resource

Add the following script to the TF file to inform Terraform to create API Gateway plugin resources:

```hcl
variable "plugin_name" {
  description = "The name of the APIG plugin"
  type        = string
}

variable "plugin_description" {
  description = "The description of the APIG plugin"
  type        = string
  default     = null
}

# Create API Gateway plugin resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing)
resource "huaweicloud_apig_plugin" "test" {
  instance_id = huaweicloud_apig_instance.test.id
  name        = var.plugin_name
  type        = "proxy_cache"
  description = var.plugin_description

  content = jsonencode({
    cache_key = {
      system_params = []
      parameters = [
        "custom_param"
      ],
      headers = []
    },
    cache_http_status_and_ttl = [
      {
        http_status = [
          202,
          203
        ],
        ttl = 5
      }
    ],
    client_cache_control = {
      mode  = "off",
      datas = []
    },
    cacheable_headers = [
      "X-Custom-Header"
    ]
  })
}
```

**Parameter Description**:

- **instance\_id**: API Gateway instance ID, referencing the ID of the API Gateway instance resource created earlier
- **name**: Plugin name, assigned by referencing input variable plugin\_name
- **type**: Plugin type, set to "proxy\_cache" to create a proxy cache plugin
- **description**: Plugin description, assigned by referencing input variable plugin\_description
- **content**: Plugin configuration content, encoded in JSON format, containing the following configuration items:
  - **cache\_key**: Cache key configuration, including system parameters, custom parameters, and request headers
  - **cache\_http\_status\_and\_ttl**: Cache HTTP status code and TTL configuration, specifying which HTTP status code responses need to be cached and the cache time
  - **client\_cache\_control**: Client cache control configuration, setting client cache mode
  - **cacheable\_headers**: List of cacheable request headers

### 8. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content, and these input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `terraform.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC configuration
vpc_name              = "tf_test_apig_instance_vpc"

# Subnet configuration
subnet_name           = "tf_test_apig_instance_subnet"

# Security group configuration
security_group_name   = "tf_test_apig_instance_security_group"

# API Gateway instance configuration
instance_name         = "tf_test_apig_instance"
enterprise_project_id = "0"

# API Gateway plugin configuration
plugin_name           = "tf_test_apig_plugin"
plugin_description    = "Created by Terraform script"
```

**Usage Method**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content in this `tfvars` file when executing terraform commands, other names need to add `.auto` definition before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="subnet_name=my-subnet"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 9. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the proxy cache plugin
4. Run `terraform show` to view the details of the created proxy cache plugin

## Reference Information

- [Huawei Cloud API Gateway Product Documentation](https://support.huaweicloud.com/apig/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For APIG Proxy Cache Plugin](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/apig/proxy-cache-plugin)

# Deploy API with Custom Authentication

## Application Scenario

Huawei Cloud API Gateway (APIG) supports multiple authentication methods, including IAM authentication, APP authentication, etc. At the same time, API Gateway also supports users to use their own authentication methods (hereinafter referred to as custom authentication) to better make existing business capabilities compatible. Custom authentication can meet complex authentication requirements, such as integrating third-party authentication systems, implementing custom permission control logic, etc. This best practice will introduce how to use Terraform to automatically deploy APIs with custom authentication and how to use FunctionGraph functions to implement frontend authentication for APIs.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Security Group Rule Resource (huaweicloud\_networking\_secgroup\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup_rule)
- [API Gateway Instance Resource (huaweicloud\_apig\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/apig_instance)
- [API Gateway Group Resource (huaweicloud\_apig\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/apig_group)
- [API Definition Resource (huaweicloud\_apig\_api)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/apig_api)
- [Custom Authorizer Resource (huaweicloud\_apig\_custom\_authorizer)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/apig_custom_authorizer)
- [Function Resource (huaweicloud\_fgs\_function)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/fgs_function)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── huaweicloud_apig_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_apig_instance

huaweicloud_networking_secgroup
    └── huaweicloud_networking_secgroup_rule
        └── huaweicloud_apig_instance

huaweicloud_apig_instance
    └── huaweicloud_apig_group
        └── huaweicloud_apig_api
            └── huaweicloud_apig_custom_authorizer
                └── huaweicloud_fgs_function
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration introduction, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy).

### 2. Query Availability Zones Required for API Gateway Instance Resource Creation Through Data Source

Add the following script to the TF file (such as main.tf) to inform Terraform to perform a data source query, the query results are used to create API Gateway instances:

```hcl
# Get all availability zone information in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating API Gateway instances
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**: This data source does not require additional parameters and queries all available availability zone information in the current region by default.

### 3. Create VPC Resource

Add the following script to the TF file (such as main.tf) to inform Terraform to create VPC resources:

```hcl
variable "vpc_name" {
  description = "VPC name"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
}

# Create VPC resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for deploying API Gateway instances
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing input variable vpc\_name
- **cidr**: VPC CIDR network segment, assigned by referencing input variable vpc\_cidr

### 4. Create VPC Subnet Resource

Add the following script to the TF file to inform Terraform to create VPC subnet resources:

```hcl
variable "subnet_name" {
  description = "Subnet name"
  type        = string
}

variable "subnet_cidr" {
  description = "Subnet CIDR block"
  type        = string
}

variable "subnet_gateway" {
  description = "Subnet gateway address"
  type        = string
}

# Create VPC subnet resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for deploying API Gateway instances
resource "huaweicloud_vpc_subnet" "test" {
  name       = var.subnet_name
  cidr       = var.subnet_cidr
  gateway_ip = var.subnet_gateway
  vpc_id     = huaweicloud_vpc.test.id
}
```

**Parameter Description**:

- **name**: Subnet name, assigned by referencing input variable subnet\_name
- **cidr**: Subnet network segment, assigned by referencing input variable subnet\_cidr
- **gateway\_ip**: Gateway IP address, assigned by referencing input variable subnet\_gateway
- **vpc\_id**: ID of the VPC to which the subnet belongs, referencing the ID of the VPC resource created earlier

### 5. Create Security Group Resource

Add the following script to the TF file to inform Terraform to create security group resources:

```hcl
variable "secgroup_name" {
  description = "Security group name"
  type        = string
}

# Create security group resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for deploying API Gateway instances
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.secgroup_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing input variable secgroup\_name
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default rules

### 6. Create Security Group Rule Resource

Add the following script to the TF file to inform Terraform to create security group rule resources:

```hcl
# Create security group rule resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for configuring API Gateway instance access control
resource "huaweicloud_networking_secgroup_rule" "allow_web" {
  security_group_id = huaweicloud_networking_secgroup.test.id
  direction         = "ingress"
  ethertype        = "IPv4"
  protocol         = "tcp"
  port_range_min   = 80
  port_range_max   = 80
  remote_ip_prefix = "0.0.0.0/0"
  description      = "Allow HTTP access"
}

resource "huaweicloud_networking_secgroup_rule" "allow_https" {
  security_group_id = huaweicloud_networking_secgroup.test.id
  direction         = "ingress"
  ethertype        = "IPv4"
  protocol         = "tcp"
  port_range_min   = 443
  port_range_max   = 443
  remote_ip_prefix = "0.0.0.0/0"
  description      = "Allow HTTPS access"
}
```

**Parameter Description**:

- **security\_group\_id**: Security group ID, referencing the ID of the security group resource created earlier
- **direction**: Rule direction, set to "ingress" for inbound rules
- **ethertype**: Network protocol version, set to "IPv4"
- **protocol**: Protocol type, set to "tcp"
- **port\_range\_min/port\_range\_max**: Port range, set to 80 and 443 respectively
- **remote\_ip\_prefix**: Allowed access IP range, set to "0.0.0.0/0" to allow all IP access
- **description**: Rule description

### 7. Create API Gateway Instance Resource

Add the following script to the TF file to inform Terraform to create API Gateway instance resources:

```hcl
variable "apig_name" {
  description = "API Gateway instance name"
  type        = string
}

# Create API Gateway instance resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing)
resource "huaweicloud_apig_instance" "test" {
  name                  = var.apig_name
  edition              = "BASIC"
  vpc_id               = huaweicloud_vpc.test.id
  subnet_id            = huaweicloud_vpc_subnet.test.id
  security_group_id    = huaweicloud_networking_secgroup.test.id
  availability_zones   = [data.huaweicloud_availability_zones.test.names[0]]
  description          = "API Gateway instance"
  enterprise_project_id = "0"
}
```

**Parameter Description**:

- **name**: API Gateway instance name, assigned by referencing input variable apig\_name
- **edition**: Instance specification, set to "BASIC"
- **vpc\_id**: VPC ID, referencing the ID of the VPC resource created earlier
- **subnet\_id**: Subnet ID, referencing the ID of the subnet resource created earlier
- **security\_group\_id**: Security group ID, referencing the ID of the security group resource created earlier
- **availability\_zones**: Availability zone list, using the first availability zone from the availability zone list query data source
- **description**: Instance description
- **enterprise\_project\_id**: Enterprise project ID, set to "0"

### 8. Create API Gateway Group Resource

Add the following script to the TF file to inform Terraform to create API Gateway group resources:

```hcl
variable "group_name" {
  description = "API group name"
  type        = string
}

# Create API Gateway group resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing)
resource "huaweicloud_apig_group" "test" {
  name        = var.group_name
  description = "API group"
  instance_id = huaweicloud_apig_instance.test.id
}
```

**Parameter Description**:

- **name**: API group name, assigned by referencing input variable group\_name
- **description**: Group description
- **instance\_id**: API Gateway instance ID, referencing the ID of the API Gateway instance resource created earlier

### 9. Create Function Resource

Add the following script to the TF file to inform Terraform to create function resources:

```hcl
variable "function_name" {
  description = "Function name"
  type        = string
}

# Create function resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing)
resource "huaweicloud_fgs_function" "test" {
  name        = var.function_name
  app         = "default"
  handler     = "index.handler"
  memory_size = 128
  timeout     = 30
  runtime     = "Python3.6"
  code_type   = "inline"
  
  func_code = <<EOF
import json

def handler(event, context):
    # Get authentication header information
    token = event['headers'].get('Authorization', '')
    
    if not token:
        return {
            'statusCode': 401,
            'body': json.dumps({
                'message': 'Unauthorized'
            })
        }
    
    # Implement your authentication logic here
    # For example: verify token, check user permissions, etc.
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'principalId': 'user123',
            'context': {
                'userId': 'user123',
                'userRole': 'admin'
            }
        })
    }
EOF
}
```

**Parameter Description**:

- **name**: Function name, assigned by referencing input variable function\_name
- **app**: Application to which the function belongs, set to "default"
- **handler**: Function entry point, set to "index.handler"
- **memory\_size**: Function runtime memory size, set to 128MB
- **timeout**: Function timeout, set to 30 seconds
- **runtime**: Runtime environment, set to "Python3.6"
- **code\_type**: Code type, set to "inline"
- **func\_code**: Function code, containing custom authentication logic

### 10. Create Custom Authorizer Resource

Add the following script to the TF file to inform Terraform to create custom authorizer resources:

```hcl
variable "authorizer_name" {
  description = "Custom authorizer name"
  type        = string
}

# Create custom authorizer resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing)
resource "huaweicloud_apig_custom_authorizer" "test" {
  instance_id  = huaweicloud_apig_instance.test.id
  name         = var.authorizer_name
  type         = "FRONTEND"
  function_urn = huaweicloud_fgs_function.test.urn
  identities   = ["Authorization"]
}
```

**Parameter Description**:

- **instance\_id**: API Gateway instance ID, referencing the ID of the API Gateway instance resource created earlier
- **name**: Custom authorizer name, assigned by referencing input variable authorizer\_name
- **type**: Authorizer type, set to "FRONTEND"
- **function\_urn**: Function URN, referencing the URN of the function resource created earlier
- **identities**: Authentication parameter list, set to \["Authorization"]

### 11. Create API Definition Resource

Add the following script to the TF file to inform Terraform to create API definition resources:

```hcl
variable "api_name" {
  description = "API name"
  type        = string
}

# Create API definition resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing)
resource "huaweicloud_apig_api" "test" {
  instance_id       = huaweicloud_apig_instance.test.id
  group_id         = huaweicloud_apig_group.test.id
  name             = var.api_name
  type             = "Public"
  request_protocol = "HTTPS"
  request_method   = "GET"
  request_path     = "/test"
  security_authentication = "CUSTOM"
  backend_type     = "HTTP"
  backend_path     = "/test"
  backend_method   = "GET"
  backend_address  = "https://example.com"
}
```

**Parameter Description**:

- **instance\_id**: API Gateway instance ID, referencing the ID of the API Gateway instance resource created earlier
- **group\_id**: API group ID, referencing the ID of the API Gateway group resource created earlier
- **name**: API name, assigned by referencing input variable api\_name
- **type**: API type, set to "Public"
- **request\_protocol**: Request protocol, set to "HTTPS"
- **request\_method**: Request method, set to "GET"
- **request\_path**: Request path, set to "/test"
- **security\_authentication**: Security authentication method, set to "CUSTOM"
- **backend\_type**: Backend type, set to "HTTP"
- **backend\_path**: Backend path, set to "/test"
- **backend\_method**: Backend method, set to "GET"
- **backend\_address**: Backend address, set to "<https://example.com>"

### 12. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content, and these input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# VPC configuration
vpc_name = "tf_test_vpc"
vpc_cidr = "192.168.0.0/16"

# Subnet configuration
subnet_name = "tf_test_subnet"
subnet_cidr = "192.168.1.0/24"
subnet_gateway = "192.168.1.1"

# Security group configuration
secgroup_name = "tf_test_secgroup"

# API Gateway configuration
apig_name = "tf_test_apig"
group_name = "tf_test_group"
api_name = "tf_test_api"

# Function configuration
function_name = "tf_test_function"

# Custom authorizer configuration
authorizer_name = "tf_test_authorizer"
```

**Usage Method**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content in this `tfvars` file when executing terraform commands, other names need to add `.auto` definition before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="subnet_name=my-subnet"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values in the following priority: command line parameters > variable files > environment variables > default values.

### 13. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating API Gateway custom authentication
4. Run `terraform show` to view the details of the created API Gateway custom authentication

## Reference Information

- [Huawei Cloud API Gateway Product Documentation](https://support.huaweicloud.com/apig/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For APIG Custom Authentication](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/apig/api-custom-authorizer-with-functiongraph)