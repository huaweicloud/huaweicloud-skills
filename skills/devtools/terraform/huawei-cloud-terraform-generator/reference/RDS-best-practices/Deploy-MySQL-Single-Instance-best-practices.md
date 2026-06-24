# Deploy MySQL Single Instance

## Application Scenario

Huawei Cloud Relational Database Service (RDS) MySQL single instance functionality provides highly available, high-performance MySQL database services, supporting enterprise-level functions such as automatic backup, monitoring alerts, and elastic scaling. By configuring MySQL single instances, you can quickly deploy production-grade MySQL databases, meeting database requirements for scenarios such as web applications, enterprise systems, and data analysis.

This best practice is particularly suitable for scenarios that require rapid MySQL database deployment, implementing persistent data storage, and building enterprise application backends, such as web application development, enterprise management systems, data analysis platforms, etc. This best practice will introduce how to use Terraform to automatically deploy RDS MySQL single instances, including VPC network, security group, RDS instance, database account, database, and backup creation, implementing a complete MySQL database management solution.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zone Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [RDS Flavor Query Data Source (data.huaweicloud\_rds\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/rds_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Security Group Rule Resource (huaweicloud\_networking\_secgroup\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup_rule)
- [Random Password Resource (random\_password)](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/password)
- [RDS Instance Resource (huaweicloud\_rds\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rds_instance)
- [RDS MySQL Account Resource (huaweicloud\_rds\_mysql\_account)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rds_mysql_account)
- [RDS MySQL Database Resource (huaweicloud\_rds\_mysql\_database)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rds_mysql_database)
- [RDS MySQL Database Privilege Resource (huaweicloud\_rds\_mysql\_database\_privilege)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rds_mysql_database_privilege)
- [RDS Backup Resource (huaweicloud\_rds\_backup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rds_backup)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── huaweicloud_vpc_subnet
    └── huaweicloud_rds_instance

data.huaweicloud_rds_flavors
    └── huaweicloud_rds_instance

huaweicloud_vpc
    ├── huaweicloud_vpc_subnet
    └── huaweicloud_rds_instance

huaweicloud_vpc_subnet
    └── huaweicloud_rds_instance

huaweicloud_networking_secgroup
    ├── huaweicloud_networking_secgroup_rule
    └── huaweicloud_rds_instance

huaweicloud_networking_secgroup_rule
    └── huaweicloud_rds_instance

random_password
    ├── huaweicloud_rds_instance
    └── huaweicloud_rds_mysql_account

huaweicloud_rds_instance
    ├── huaweicloud_rds_mysql_account
    ├── huaweicloud_rds_mysql_database
    └── huaweicloud_rds_backup

huaweicloud_rds_mysql_account
    └── huaweicloud_rds_mysql_database_privilege

huaweicloud_rds_mysql_database
    └── huaweicloud_rds_mysql_database_privilege

huaweicloud_rds_mysql_database_privilege
    └── huaweicloud_rds_backup
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create VPC Network

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

- **name**: VPC name, assigned by referencing the input variable vpc\_name
- **cidr**: VPC CIDR block, assigned by referencing the input variable vpc\_cidr, default value is "192.168.0.0/16"

### 3. Query Availability Zone Information

Add the following script to the TF file to instruct Terraform to query availability zone information:

```hcl
variable "availability_zone" {
  description = "The availability zone to which the RDS instance belongs"
  type        = string
  default     = ""
}

# Get all available availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create RDS instances
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}
```

**Parameter Description**:

- **count**: Conditional creation, creates this data source when availability\_zone variable is an empty string

### 4. Create VPC Subnet

Add the following script to the TF file to instruct Terraform to create a VPC subnet resource:

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

- **vpc\_id**: VPC ID that the subnet belongs to, referencing the ID of the previously created VPC resource
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, automatically calculated if subnet\_cidr is empty, otherwise uses subnet\_cidr value
- **gateway\_ip**: Subnet gateway IP, automatically calculated if gateway\_ip is empty, otherwise uses gateway\_ip value
- **availability\_zone**: Availability zone that the subnet belongs to, prioritizes using availability\_zone variable, uses the first queried availability zone if empty

### 5. Query RDS Flavor Information

Add the following script to the TF file to instruct Terraform to query RDS flavor information:

```hcl
variable "instance_flavor_id" {
  description = "The flavor ID of the RDS instance"
  type        = string
  default     = ""
}

variable "instance_db_type" {
  description = "The database engine type"
  type        = string
  default     = "MySQL"
}

variable "instance_db_version" {
  description = "The database engine version"
  type        = string
  default     = "8.0"
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

# Get all RDS flavor information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block) that meets specific conditions, used to create RDS instances
data "huaweicloud_rds_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  db_type           = var.instance_db_type
  db_version        = var.instance_db_version
  instance_mode     = var.instance_mode
  group_type        = var.instance_flavor_group_type
  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
}
```

**Parameter Description**:

- **count**: Conditional creation, creates this data source when instance\_flavor\_id variable is an empty string
- **db\_type**: Database engine type, assigned by referencing the input variable instance\_db\_type, default value is "MySQL"
- **db\_version**: Database engine version, assigned by referencing the input variable instance\_db\_version, default value is "8.0"
- **instance\_mode**: Instance mode, assigned by referencing the input variable instance\_mode, default value is "single"
- **group\_type**: Flavor group type, assigned by referencing the input variable instance\_flavor\_group\_type, default value is "general"
- **availability\_zone**: Availability zone, prioritizes using availability\_zone variable, uses the first queried availability zone if empty

### 6. Create Security Group

Add the following script to the TF file to instruct Terraform to create a security group resource:

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

- **name**: Security group name, assigned by referencing the input variable security\_group\_name
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default security group rules

### 7. Create Security Group Rules

Add the following script to the TF file to instruct Terraform to create security group rule resources:

```hcl
variable "instance_db_port" {
  description = "The database port"
  type        = number
  default     = 3306
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

- **security\_group\_id**: Security group ID, referencing the ID of the previously created security group resource
- **direction**: Rule direction, set to "ingress" for inbound rules
- **ethertype**: IP protocol type, set to "IPv4" for IPv4 protocol
- **remote\_ip\_prefix**: Remote IP prefix, using VPC CIDR block
- **ports**: Port number, assigned by referencing the input variable instance\_db\_port, default value is 3306
- **protocol**: Protocol type, set to "tcp" for TCP protocol

### 8. Create Random Password

Add the following script to the TF file to instruct Terraform to create a random password resource:

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

- **count**: Conditional creation, creates this resource when instance\_password variable is an empty string
- **length**: Password length, set to 12 characters
- **special**: Whether to include special characters, set to true to include special characters
- **override\_special**: Special character set, set to "!@%^\*-\_=+"

### 9. Create RDS Instance

Add the following script to the TF file to instruct Terraform to create an RDS instance resource:

```hcl
variable "instance_name" {
  description = "The MySQL RDS instance name"
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
}

variable "instance_backup_keep_days" {
  description = "The number of days to retain backups"
  type        = number
}

# Create an RDS instance resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
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
    ]
  }
}
```

**Parameter Description**:

- **name**: RDS instance name, assigned by referencing the input variable instance\_name
- **flavor**: Instance flavor, prioritizes using instance\_flavor\_id variable, uses queried flavor name if empty
- **vpc\_id**: VPC ID, referencing the ID of the previously created VPC resource
- **subnet\_id**: Subnet ID, referencing the ID of the previously created VPC subnet resource
- **security\_group\_id**: Security group ID, referencing the ID of the previously created security group resource
- **availability\_zone**: Availability zone list, prioritizes using availability\_zone variable, uses queried availability zone if empty
- **db**: Database configuration block
  - **type**: Database engine type, assigned by referencing the input variable instance\_db\_type
  - **version**: Database engine version, assigned by referencing the input variable instance\_db\_version
  - **port**: Database port, assigned by referencing the input variable instance\_db\_port
  - **password**: Database password, prioritizes using instance\_password variable, uses randomly generated password if empty
- **volume**: Storage volume configuration block
  - **type**: Storage type, assigned by referencing the input variable instance\_volume\_type, default value is "CLOUDSSD"
  - **size**: Storage size, assigned by referencing the input variable instance\_volume\_size, default value is 40 (GB)
- **backup\_strategy**: Backup strategy configuration block
  - **start\_time**: Backup time window, assigned by referencing the input variable instance\_backup\_time\_window
  - **keep\_days**: Backup retention days, assigned by referencing the input variable instance\_backup\_keep\_days
- **lifecycle.ignore\_changes**: Lifecycle management, ignores flavor changes

### 10. Create RDS MySQL Account

Add the following script to the TF file to instruct Terraform to create an RDS MySQL account resource:

```hcl
variable "account_name" {
  description = "Username with elevated privileges"
  type        = string
}

variable "account_password" {
  description = "The password for the database account"
  type        = string
  default     = ""
}

# Create an RDS MySQL account resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_rds_mysql_account" "test" {
  instance_id = huaweicloud_rds_instance.test.id
  name        = var.account_name
  password    = var.account_password != "" ? var.account_password : try(random_password.test[0].result, null)
}
```

**Parameter Description**:

- **instance\_id**: RDS instance ID, referencing the ID of the previously created RDS instance resource
- **name**: Account name, assigned by referencing the input variable account\_name
- **password**: Account password, prioritizes using account\_password variable, uses randomly generated password if empty

### 11. Create RDS MySQL Database

Add the following script to the TF file to instruct Terraform to create an RDS MySQL database resource:

```hcl
variable "database_name" {
  description = "The name of the initial database"
  type        = string
}

variable "character_set" {
  description = "The character set of the database"
  type        = string
  default     = "utf8"
}

# Create an RDS MySQL database resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_rds_mysql_database" "test" {
  instance_id   = huaweicloud_rds_instance.test.id
  name          = var.database_name
  character_set = var.character_set
}
```

**Parameter Description**:

- **instance\_id**: RDS instance ID, referencing the ID of the previously created RDS instance resource
- **name**: Database name, assigned by referencing the input variable database\_name
- **character\_set**: Character set, assigned by referencing the input variable character\_set, default value is "utf8"

### 12. Create RDS MySQL Database Privilege

Add the following script to the TF file to instruct Terraform to create an RDS MySQL database privilege resource:

```hcl
# Create an RDS MySQL database privilege resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_rds_mysql_database_privilege" "test" {
  instance_id = huaweicloud_rds_instance.test.id
  db_name     = var.database_name

  users {
    name     = huaweicloud_rds_mysql_account.test.name
    readonly = true
  }

  depends_on = [huaweicloud_rds_mysql_database.test]
}
```

**Parameter Description**:

- **instance\_id**: RDS instance ID, referencing the ID of the previously created RDS instance resource
- **db\_name**: Database name, assigned by referencing the input variable database\_name
- **users**: User privilege configuration block
  - **name**: Username, referencing the name of the previously created RDS MySQL account resource
  - **readonly**: Whether read-only privilege, set to true for read-only privilege
- **depends\_on**: Explicit dependency relationship, ensures database exists before privilege creation

### 13. Create RDS Backup

Add the following script to the TF file to instruct Terraform to create an RDS backup resource:

```hcl
variable "backup_name" {
  description = "The name for instance backups"
  type        = string
}

# Create an RDS backup resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_rds_backup" "test" {
  instance_id = huaweicloud_rds_instance.test.id
  name        = var.backup_name

  depends_on = [huaweicloud_rds_mysql_database_privilege.test]
}
```

**Parameter Description**:

- **instance\_id**: RDS instance ID, referencing the ID of the previously created RDS instance resource
- **name**: Backup name, assigned by referencing the input variable backup\_name
- **depends\_on**: Explicit dependency relationship, ensures database privileges are configured before backup creation

### 14. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# VPC network configuration
vpc_name = "tf_test_vpc"

# Subnet configuration
subnet_name = "tf_test_subnet"

# Security group configuration
security_group_name = "tf_test_security_group"

# RDS instance configuration
instance_name = "tf_test_mysql_instance"

# Database account configuration
account_name = "tf_test_account"

# Database configuration
database_name = "tf_test_database"

# Backup configuration
backup_name                 = "tf_test_backup"
instance_backup_time_window = "08:00-09:00"
instance_backup_keep_days   = 1
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="instance_name=my-instance"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 15. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating MySQL single instances
4. Run `terraform show` to view the created MySQL single instance details

## Reference Information

- [Huawei Cloud Relational Database Service Product Documentation](https://support.huaweicloud.com/rds/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For RDS MySQL Single Instance](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/rds/mysql-single-instance)
