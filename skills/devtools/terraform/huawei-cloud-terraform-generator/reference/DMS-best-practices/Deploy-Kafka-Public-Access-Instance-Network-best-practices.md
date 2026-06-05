# Deploy Kafka Public Access Instance Network

## Application Scenario

Huawei Cloud Distributed Message Service Kafka supports public network access to instances, suitable for scenarios that require accessing Kafka services in a public network environment, such as cross-region access, development and testing environments, etc. By configuring public network access, you can bind Elastic IP (EIP) to Kafka instances and configure corresponding security group rules and port protocols to achieve secure public network access. This best practice will introduce how to use Terraform to automatically deploy Kafka instance network configuration that supports public network access, including VPC, subnet, security group, EIP, and Kafka instance public access configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Data Source (huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [Kafka Flavors Data Source (huaweicloud\_dms\_kafka\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/dms_kafka_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Security Group Rule Resource (huaweicloud\_networking\_secgroup\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup_rule)
- [Elastic IP Resource (huaweicloud\_vpc\_eip)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_eip)
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
    ├── huaweicloud_networking_secgroup_rule
    └── huaweicloud_dms_kafka_instance

huaweicloud_vpc_eip
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
  availability_zones = length(var.availability_zones) == 0 ? try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 1)) : var.availability_zones
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

### 4. Create Security Group Rules

Add the following script to the TF file (e.g., main.tf) to create security group rules that allow public network access to Kafka instance ports:

```hcl
variable "security_group_rule_ports" {
  description = "The ports of the security group rule"
  type        = string
  default     = "9094,9095"
}

variable "security_group_rule_remote_ip_prefix" {
  description = "The remote IP prefix of the security group rule"
  type        = string
}

# Create security group rule
resource "huaweicloud_networking_secgroup_rule" "test" {
  security_group_id = huaweicloud_networking_secgroup.test.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  ports             = var.security_group_rule_ports
  remote_ip_prefix  = var.security_group_rule_remote_ip_prefix
}
```

**Parameter Description**:

- **security\_group\_id**: Security group ID, assigned by referencing the security group resource
- **direction**: Rule direction, set to "ingress" (inbound)
- **ethertype**: IP protocol type, set to "IPv4"
- **protocol**: Protocol type, set to "tcp"
- **ports**: Port range, assigned by referencing the input variable security\_group\_rule\_ports, default value is "9094,9095" (Kafka public network access ports)
- **remote\_ip\_prefix**: Remote IP address segment, assigned by referencing the input variable security\_group\_rule\_remote\_ip\_prefix, used to limit the IP range allowed to access

### 5. Create Elastic IP

Add the following script to the TF file (e.g., main.tf) to create Elastic IP (EIP) for binding to Kafka instances:

```hcl
variable "instance_broker_num" {
  description = "The number of brokers of the Kafka instance"
  type        = number
  default     = 3
}

variable "eip_type" {
  description = "The type of the EIP"
  type        = string
  default     = "5_bgp"
}

variable "bandwidth_name" {
  description = "The name of the bandwidth"
  type        = string
}

variable "bandwidth_size" {
  description = "The size of the bandwidth"
  type        = number
  default     = 5
}

variable "bandwidth_share_type" {
  description = "The share type of the bandwidth"
  type        = string
  default     = "PER"
}

variable "bandwidth_charge_mode" {
  description = "The charge mode of the bandwidth"
  type        = string
  default     = "traffic"
}

# Create Elastic IP (create corresponding number of EIPs based on broker count)
resource "huaweicloud_vpc_eip" "test" {
  count = var.instance_broker_num

  publicip {
    type = var.eip_type
  }

  bandwidth {
    name        = var.bandwidth_name
    size        = var.bandwidth_size
    share_type  = var.bandwidth_share_type
    charge_mode = var.bandwidth_charge_mode
  }
}
```

**Parameter Description**:

- **count**: Creation count, assigned by referencing the input variable instance\_broker\_num, ensuring one EIP is created for each broker
- **publicip.type**: Public IP type, assigned by referencing the input variable eip\_type, default value is "5\_bgp" (full dynamic BGP)
- **bandwidth.name**: Bandwidth name, assigned by referencing the input variable bandwidth\_name
- **bandwidth.size**: Bandwidth size, assigned by referencing the input variable bandwidth\_size, default value is 5 (Mbit/s)
- **bandwidth.share\_type**: Bandwidth sharing type, assigned by referencing the input variable bandwidth\_share\_type, default value is "PER" (dedicated)
- **bandwidth.charge\_mode**: Bandwidth billing mode, assigned by referencing the input variable bandwidth\_charge\_mode, default value is "traffic" (pay-per-use)

### 6. Create Kafka Instance Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Kafka instance resource that supports public network access:

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

variable "instance_description" {
  description = "The description of the Kafka instance"
  type        = string
  default     = ""
}

variable "instance_access_user_name" {
  description = "The access user name of the Kafka instance"
  type        = string
  default     = null
}

variable "instance_access_user_password" {
  description = "The access password of the Kafka instance"
  type        = string
  sensitive   = true
  default     = null
}

variable "instance_enabled_mechanisms" {
  description = "The enabled mechanisms of the Kafka instance"
  type        = list(string)
  default     = null
}

variable "instance_public_plain_enable" {
  description = "Whether to enable public plaintext access"
  type        = bool
  default     = true
}

variable "instance_public_sasl_ssl_enable" {
  description = "Whether to enable public SASL SSL access"
  type        = bool
  default     = false
}

variable "instance_public_sasl_plaintext_enable" {
  description = "Whether to enable public SASL plaintext access"
  type        = bool
  default     = false
}

# Create Kafka instance resource that supports public network access in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
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
  description        = var.instance_description
  public_ip_ids      = huaweicloud_vpc_eip.test[*].id
  access_user        = var.instance_access_user_name
  password           = var.instance_access_user_password
  enabled_mechanisms = var.instance_enabled_mechanisms

  port_protocol {
    private_plain_enable         = true
    public_plain_enable          = var.instance_public_plain_enable
    public_sasl_ssl_enable       = var.instance_public_sasl_ssl_enable
    public_sasl_plaintext_enable = var.instance_public_sasl_plaintext_enable
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
- **description**: Instance description, assigned by referencing the input variable instance\_description, optional parameter, default value is empty string
- **public\_ip\_ids**: Public IP ID list, assigned by referencing the EIP resource list, used to bind public IPs to Kafka instances
- **access\_user**: Access user name, assigned by referencing the input variable instance\_access\_user\_name, optional parameter, default value is null
- **password**: Access password, assigned by referencing the input variable instance\_access\_user\_password, optional parameter, default value is null
- **enabled\_mechanisms**: Enabled authentication mechanisms, assigned by referencing the input variable instance\_enabled\_mechanisms, optional parameter, default value is null, supports "SCRAM-SHA-512", etc.
- **port\_protocol.private\_plain\_enable**: Whether to enable private network plaintext access, set to true
- **port\_protocol.public\_plain\_enable**: Whether to enable public network plaintext access, assigned by referencing the input variable instance\_public\_plain\_enable, default value is true
- **port\_protocol.public\_sasl\_ssl\_enable**: Whether to enable public network SASL SSL access, assigned by referencing the input variable instance\_public\_sasl\_ssl\_enable, default value is false
- **port\_protocol.public\_sasl\_plaintext\_enable**: Whether to enable public network SASL plaintext access, assigned by referencing the input variable instance\_public\_sasl\_plaintext\_enable, default value is false

### 7. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and Subnet Configuration
vpc_name    = "tf_test_kafka_instance"
vpc_cidr    = "192.168.0.0/16"
subnet_name = "tf_test_kafka_instance"

# Security Group Configuration
security_group_name                  = "tf_test_kafka_instance"
security_group_rule_remote_ip_prefix = "your_client_ip_address"

# Kafka Instance Configuration
instance_name                 = "tf_test_kafka_instance"
bandwidth_name                = "tf_test_kafka_instance_bandwidth"
instance_access_user_name     = "admin"
instance_access_user_password = "yourInstanceAccessPassword!"
instance_enabled_mechanisms   = ["SCRAM-SHA-512"]
instance_public_sasl_ssl_enable = true
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `security_group_rule_remote_ip_prefix` needs to be set to the client IP address segment allowed to access (e.g., "0.0.0.0/0" means allowing all IPs to access, but it is recommended to set it to a specific IP segment to improve security)
   - `instance_access_user_password` needs to be set to a password that meets password complexity requirements
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="instance_name=my_kafka" -var="vpc_name=my_vpc"`
2. Environment variables: `export TF_VAR_instance_name=my_kafka` and `export TF_VAR_vpc_name=my_vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. Since instance\_access\_user\_password contains sensitive information, it is recommended to use environment variables or encrypted variable files for setting. In addition, for security reasons, it is recommended to set security\_group\_rule\_remote\_ip\_prefix to a specific client IP address segment instead of "0.0.0.0/0".

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create a Kafka instance that supports public network access:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the Kafka instance and related resources
4. Run `terraform show` to view the details of the created Kafka instance

> Note: After the Kafka instance is created, an EIP will be bound to each broker, and you can access the Kafka service through the public IP. It is recommended to enable SASL SSL access to improve security. The instance's availability zones and flavor ID cannot be modified after creation, so they need to be configured correctly during creation. Through lifecycle.ignore\_changes, Terraform can be prevented from modifying these immutable parameters in subsequent updates.

## Reference Information

- [Huawei Cloud Distributed Message Service Kafka Product Documentation](https://support.huaweicloud.com/kafka/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Public Access Instance Network](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dms/kafka/public-access-instance-network)