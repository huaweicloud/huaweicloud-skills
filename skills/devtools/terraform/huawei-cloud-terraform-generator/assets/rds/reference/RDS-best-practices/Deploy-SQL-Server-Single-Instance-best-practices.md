# Deploy SQL Server Single Instance

## Application Scenario

Relational Database Service (RDS) is a highly available, high-performance, and easily scalable relational database cloud service provided by Huawei Cloud, supporting multiple database engines such as MySQL, PostgreSQL, SQL Server, MariaDB, etc. RDS provides automatic backup, monitoring alerts, elastic scaling, read-write separation, and other functions, meeting the database requirements of enterprise applications.

SQL Server is a relational database management system developed by Microsoft, widely used in enterprise application development. Huawei Cloud RDS supports SQL Server database engines, providing SQL Server 2019 SE, 2019 EE, and other versions, supporting database applications in Windows environments.

This best practice will introduce how to use Terraform to automatically deploy an RDS SQL Server single instance, including VPC network, security group, and RDS instance creation, supporting complete SQL Server database management functions.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zone List Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [RDS Flavor List Query Data Source (data.huaweicloud\_rds\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/rds_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Security Group Rule Resource (huaweicloud\_networking\_secgroup\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup_rule)
- [Random Password Resource (random\_password)](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/password)
- [RDS Instance Resource (huaweicloud\_rds\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rds_instance)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── huaweicloud_vpc_subnet
    └── data.huaweicloud_rds_flavors

data.huaweicloud_rds_flavors
    └── huaweicloud_rds_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet

huaweicloud_vpc_subnet
    └── huaweicloud_rds_instance

huaweicloud_networking_secgroup
    └── huaweicloud_networking_secgroup_rule
    └── huaweicloud_rds_instance

huaweicloud_networking_secgroup_rule
    └── huaweicloud_rds_instance

random_password
    └── huaweicloud_rds_instance
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zone Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the results of which are used to create VPC subnets and RDS instances:

```hcl
variable "availability_zone" {
  description = "The availability zone to which the RDS instance belongs"
  type        = string
  default     = ""
}

# Get all availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create VPC subnets and RDS instances
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}
```

**Parameter Description**:

- **count**: Data source creation count, used to control whether to execute the availability zone list query data source, only creates the data source when `var.availability_zone` is empty (i.e., execute availability zone list query)

### 3. Query RDS Flavor Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the results of which are used to create RDS instances:

```hcl
variable "instance_flavor_id" {
  description = "The flavor ID of the RDS instance"
  type        = string
  default     = ""
}

variable "instance_db_type" {
  description = "The database engine type"
  type        = string
  default     = "SQLServer"
}

variable "instance_db_version" {
  description = "The database engine version"
  type        = string
  default     = "2019_SE"
}

variable "instance_mode" {
  description = "The instance mode for the RDS instance flavor"
  type        = string
  default     = "single"
}

variable "instance_flavor_group_type" {
  description = "The group type for the RDS instance flavor"
  type        = string
  default     = "general"
}

variable "instance_flavor_memory" {
  description = "The memory size for the RDS instance flavor"
  type        = number
  default     = 4
}

# Get all RDS flavor information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create RDS instances
data "huaweicloud_rds_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  db_type           = var.instance_db_type
  db_version        = var.instance_db_version
  instance_mode     = var.instance_mode
  group_type        = var.instance_flavor_group_type
  memory            = var.instance_flavor_memory
  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
}
```

**Parameter Description**:

- **count**: Data source creation count, used to control whether to execute the RDS flavor list query data source, only creates the data source when `var.instance_flavor_id` is empty
- **db\_type**: Database type, assigned by referencing the input variable `instance_db_type`
- **db\_version**: Database version, assigned by referencing the input variable `instance_db_version`
- **instance\_mode**: Instance mode, assigned by referencing the input variable `instance_mode`
- **group\_type**: Flavor group type, assigned by referencing the input variable `instance_flavor_group_type`
- **memory**: Memory size, assigned by referencing the input variable `instance_flavor_memory`
- **availability\_zone**: Availability zone, assigned based on the return results of the availability zone list query data source (data.huaweicloud\_availability\_zones)

### 4. Create VPC Network

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

- **name**: VPC name, assigned by referencing the input variable `vpc_name`
- **cidr**: VPC CIDR block, assigned by referencing the input variable `vpc_cidr`

### 5. Create VPC Subnet

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
}

variable "gateway_ip" {
  description = "The gateway IP address of the subnet"
  type        = string
  default     = ""
}

# Create a VPC subnet resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id            = huaweicloud_vpc.test.id
  name              = var.subnet_name
  cidr              = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip        = var.gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.gateway_ip
  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID, assigned by referencing the ID of the VPC resource (huaweicloud\_vpc)
- **name**: Subnet name, assigned by referencing the input variable `subnet_name`
- **cidr**: Subnet CIDR block, assigned by referencing the input variable `subnet_cidr`, automatically calculated if empty
- **gateway\_ip**: Subnet gateway IP address, assigned by referencing the input variable `gateway_ip`, automatically calculated if empty
- **availability\_zone**: Availability zone where the subnet is located, assigned based on the return results of the availability zone list query data source (data.huaweicloud\_availability\_zones)

### 6. Create Security Group

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

- **name**: Security group name, assigned by referencing the input variable `security_group_name`
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default security group rules

### 7. Create Security Group Rules

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create security group rule resources:

```hcl
variable "instance_db_port" {
  description = "The database port"
  type        = number
  default     = 1433
}

# Create a security group rule resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_networking_secgroup_rule" "test" {
  security_group_id = huaweicloud_networking_secgroup.test.id
  direction         = "ingress"
  ethertype         = "IPv4"
  remote_ip_prefix  = var.vpc_cidr
  ports             = var.instance_db_port
  protocol          = "tcp"
}
```

**Parameter Description**:

- **security\_group\_id**: Security group ID, assigned by referencing the ID of the security group resource (huaweicloud\_networking\_secgroup)
- **direction**: Rule direction, set to "ingress" for inbound rules
- **ethertype**: Ethernet type, set to "IPv4"
- **remote\_ip\_prefix**: Remote IP prefix, assigned by referencing the input variable `vpc_cidr`
- **ports**: Port number, assigned by referencing the input variable `instance_db_port`
- **protocol**: Protocol type, set to "tcp"

### 8. Create Random Password

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a random password resource:

```hcl
variable "instance_password" {
  description = "The password for the RDS instance"
  type        = string
  default     = ""
}

# Create a random password resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "random_password" "test" {
  count = var.instance_password == "" ? 1 : 0

  length           = 12
  special          = true
  override_special = "!@%^*-_=+"
}
```

**Parameter Description**:

- **count**: Resource creation count, used to control whether to execute random password resource creation, only creates the resource when `var.instance_password` is empty
- **length**: Password length, set to 12 characters
- **special**: Whether to include special characters, set to true
- **override\_special**: Special character set, set to "!@%^\*-\_=+"

### 9. Create RDS SQL Server Single Instance

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an RDS SQL Server single instance resource:

```hcl
variable "instance_name" {
  description = "The SQLServer RDS instance name"
  type        = string
}

variable "instance_volume_type" {
  description = "The storage volume type"
  type        = string
  default     = "CLOUDSSD"
}

variable "instance_volume_size" {
  description = "The storage volume size in GB"
  type        = number
  default     = 40
}

variable "instance_backup_time_window" {
  description = "The backup time window in HH:MM-HH:MM format"
  type        = string
  default     = "03:00-04:00"
}

variable "instance_backup_keep_days" {
  description = "The number of days to retain backups"
  type        = number
  default     = 7
}

# Create an RDS SQL Server single instance resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_rds_instance" "test" {
  name              = var.instance_name
  flavor            = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_rds_flavors.test[0].flavors[0].name, null)
  vpc_id            = huaweicloud_vpc.test.id
  subnet_id         = huaweicloud_vpc_subnet.test.id
  security_group_id = huaweicloud_networking_secgroup.test.id
  availability_zone = var.availability_zone != "" ? [var.availability_zone] : try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 1), [])

  db {
    type     = var.instance_db_type
    version  = var.instance_db_version
    port     = var.instance_db_port
    password = var.instance_password != "" ? var.instance_password : try(random_password.test[0].result, null)
  }

  volume {
    type = var.instance_volume_type
    size = var.instance_volume_size
  }

  backup_strategy {
    start_time = var.instance_backup_time_window
    keep_days  = var.instance_backup_keep_days
  }

  lifecycle {
    ignore_changes = [
      flavor,
      availability_zone
    ]
  }

  depends_on = [
    huaweicloud_networking_secgroup_rule.test
  ]
}
```

**Parameter Description**:

- **name**: RDS instance name, assigned by referencing the input variable `instance_name`
- **flavor**: RDS instance flavor, assigned by referencing the input variable `instance_flavor_id`, if empty then assigned based on the return results of the RDS flavor list query data source (data.huaweicloud\_rds\_flavors)
- **vpc\_id**: VPC ID, assigned by referencing the ID of the VPC resource (huaweicloud\_vpc)
- **subnet\_id**: Subnet ID, assigned by referencing the ID of the VPC subnet resource (huaweicloud\_vpc\_subnet)
- **security\_group\_id**: Security group ID, assigned by referencing the ID of the security group resource (huaweicloud\_networking\_secgroup)
- **availability\_zone**: Availability zone list, assigned based on the return results of the availability zone list query data source (data.huaweicloud\_availability\_zones)
- **db**: Database configuration block, includes database type, version, port, and password
- **volume**: Storage volume configuration block, includes storage type and size
- **backup\_strategy**: Backup strategy configuration block, includes backup time window and retention days
- **lifecycle**: Lifecycle configuration block, used to ignore changes to specific parameters
- **depends\_on**: Explicit dependency relationship, ensures security group rules are created before creating RDS instance

### 10. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Network configuration
vpc_name            = "tf_test_vpc"
subnet_name         = "tf_test_subnet"
security_group_name = "tf_test_security_group"

# Instance configuration
instance_name       = "tf_test_sqlserver_instance"
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
3. After confirming the resource plan is correct, run `terraform apply` to start creating RDS SQL Server single instances
4. Run `terraform show` to view the created RDS SQL Server single instances

## Reference Information

- [Huawei Cloud Relational Database Service Product Documentation](https://support.huaweicloud.com/rds/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For RDS SQL Server Single Instance](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/rds/sqlserver-single-instance)
