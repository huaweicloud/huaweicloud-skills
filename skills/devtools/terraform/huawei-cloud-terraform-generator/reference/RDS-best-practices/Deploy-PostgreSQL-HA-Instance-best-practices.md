# Deploy PostgreSQL HA Instance

## Application Scenario

Huawei Cloud Relational Database Service (RDS) PostgreSQL HA instance functionality provides highly available, high-performance PostgreSQL database services, supporting primary-standby architecture, automatic failover, read-write separation, and other enterprise-level functions. By configuring PostgreSQL HA instances, you can build highly available database clusters, meeting strict requirements for data security and service continuity in production environments.

This best practice is particularly suitable for scenarios that require highly available database services, implementing data redundancy backup, building enterprise application backends, such as production system databases, critical business applications, data warehouses, etc. This best practice will introduce how to use Terraform to automatically deploy RDS PostgreSQL HA instances, including VPC network, security group, RDS instance, PostgreSQL account, database, schema, and backup creation, implementing a complete PostgreSQL high-availability database solution.

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
- [RDS PostgreSQL Account Resource (huaweicloud\_rds\_pg\_account)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rds_pg_account)
- [RDS PostgreSQL Account Privileges Resource (huaweicloud\_rds\_pg\_account\_privileges)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rds_pg_account_privileges)
- [RDS PostgreSQL Database Resource (huaweicloud\_rds\_pg\_database)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rds_pg_database)
- [RDS PostgreSQL Schema Resource (huaweicloud\_rds\_pg\_schema)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rds_pg_schema)
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
    └── huaweicloud_rds_pg_account

huaweicloud_rds_instance
    ├── huaweicloud_rds_pg_account
    ├── huaweicloud_rds_pg_database
    └── huaweicloud_rds_backup

huaweicloud_rds_pg_account
    ├── huaweicloud_rds_pg_account_privileges
    └── huaweicloud_rds_pg_schema

huaweicloud_rds_pg_database
    └── huaweicloud_rds_pg_schema

huaweicloud_rds_pg_schema
    └── huaweicloud_rds_backup
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create VPC Resource

Add the following script to the TF file to instruct Terraform to create a VPC resource:

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
variable "availability_zones" {
  description = "The list of availability zones to which the RDS instance belong"
  type        = list(string)
  default     = []
  nullable    = false

  validation {
    condition     = var.instance_mode == "ha" && (length(var.availability_zones) == 0 || length(var.availability_zones) > 1) || var.instance_mode != "ha" && length(var.availability_zones) <= 1
    error_message = "The availability zones must be a list of strings"
  }
}

# Query availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
data "huaweicloud_availability_zones" "test" {
  count = length(var.availability_zones) < 1 ? 1 : 0
}
```

**Parameter Description**:

- **count**: Query availability zone information when availability\_zones variable is empty, otherwise do not query
- **availability\_zones**: Availability zone list, assigned by referencing the input variable availability\_zones, supports validation rules to ensure HA mode requires multiple availability zones

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
  availability_zone = length(var.availability_zones) > 0 ? element(var.availability_zones, 0) : try(data.huaweicloud_availability_zones.test[0].names[0], null)
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID, referencing the ID of the previously created VPC resource
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, prioritizes using subnet\_cidr variable, automatically calculated if empty
- **gateway\_ip**: Gateway IP address, prioritizes using gateway\_ip variable, automatically calculated if empty
- **availability\_zone**: Availability zone, prioritizes using the first element of availability\_zones variable, otherwise uses the first queried availability zone

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
  default     = "PostgreSQL"
}

variable "instance_db_version" {
  description = "The database engine version"
  type        = string
  default     = "16"
}

variable "instance_mode" {
  description = "The instance mode for the RDS instance flavor"
  type        = string
  default     = "ha"
}

variable "instance_flavor_group_type" {
  description = "The group type for the RDS instance flavor"
  type        = string
  default     = "general"
}

variable "instance_flavor_memory" {
  description = "The memory size for the RDS instance flavor"
  type        = number
  default     = 8
}

# Query RDS flavor information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
data "huaweicloud_rds_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  db_type           = var.instance_db_type
  db_version        = var.instance_db_version
  instance_mode     = var.instance_mode
  group_type        = var.instance_flavor_group_type
  memory            = var.instance_flavor_memory
  availability_zone = length(var.availability_zones) > 0 ? element(var.availability_zones, 0) : try(data.huaweicloud_availability_zones.test[0].names[0], null)
}
```

**Parameter Description**:

- **count**: Query RDS flavor information when instance\_flavor\_id variable is empty, otherwise do not query
- **db\_type**: Database engine type, assigned by referencing the input variable instance\_db\_type, default value is "PostgreSQL"
- **db\_version**: Database engine version, assigned by referencing the input variable instance\_db\_version, default value is "16"
- **instance\_mode**: Instance mode, assigned by referencing the input variable instance\_mode, default value is "ha" (HA mode)
- **group\_type**: Flavor group type, assigned by referencing the input variable instance\_flavor\_group\_type, default value is "general"
- **memory**: Memory size, assigned by referencing the input variable instance\_flavor\_memory, default value is 8
- **availability\_zone**: Availability zone, prioritizes using the first element of availability\_zones variable, otherwise uses the first queried availability zone

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
  default     = 5432
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
- **ethertype**: Ethernet type, set to "IPv4"
- **remote\_ip\_prefix**: Remote IP prefix, assigned by referencing the input variable vpc\_cidr, allows access within VPC
- **ports**: Port number, assigned by referencing the input variable instance\_db\_port, default value is 5432 (PostgreSQL default port)
- **protocol**: Protocol type, set to "tcp"

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

- **count**: Create random password when instance\_password variable is empty, otherwise do not create
- **length**: Password length, set to 12 characters
- **special**: Whether to include special characters, set to true
- **override\_special**: Special character set, set to "!@%^\*-\_=+"

### 9. Create RDS Instance

Add the following script to the TF file to instruct Terraform to create an RDS instance resource:

```hcl
variable "instance_name" {
  description = "The name of the RDS instance"
  type        = string
}

variable "ha_replication_mode" {
  description = "The HA replication mode of the RDS instance"
  type        = string
  default     = "async"
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
  name                = var.instance_name
  flavor              = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_rds_flavors.test[0].flavors[0].name, null)
  vpc_id              = huaweicloud_vpc.test.id
  subnet_id           = huaweicloud_vpc_subnet.test.id
  security_group_id   = huaweicloud_networking_secgroup.test.id
  availability_zone   = length(var.availability_zones) > 0 ? var.availability_zones : var.instance_mode == "ha" ? try(
    slice(data.huaweicloud_availability_zones.test[0].names, 0, 2), []) : try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 1), [])
  ha_replication_mode = var.instance_mode == "ha" ? var.ha_replication_mode : null

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
      availability_zone,
    ]
  }
}
```

**Parameter Description**:

- **name**: RDS instance name, assigned by referencing the input variable instance\_name
- **flavor**: Instance flavor, prioritizes using instance\_flavor\_id variable, uses the first queried flavor if empty
- **vpc\_id**: VPC ID, referencing the ID of the previously created VPC resource
- **subnet\_id**: Subnet ID, referencing the ID of the previously created subnet resource
- **security\_group\_id**: Security group ID, referencing the ID of the previously created security group resource
- **availability\_zone**: Availability zone list, HA mode requires multiple availability zones, single mode only needs one availability zone
- **ha\_replication\_mode**: HA replication mode, assigned by referencing the input variable ha\_replication\_mode, default value is "async"
- **db**: Database configuration block, includes database type, version, port, and password
- **volume**: Storage configuration block, includes storage type and size
- **backup\_strategy**: Backup strategy configuration block, includes backup time window and retention days
- **lifecycle**: Lifecycle configuration, ignores changes to flavor and availability\_zone

### 10. Create RDS PostgreSQL Account

Add the following script to the TF file to instruct Terraform to create an RDS PostgreSQL account resource:

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

# Create an RDS PostgreSQL account resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_rds_pg_account" "test" {
  instance_id = huaweicloud_rds_instance.test.id
  name        = var.account_name
  password    = var.account_password != "" ? var.account_password : try(random_password.test[0].result, null)
}
```

**Parameter Description**:

- **instance\_id**: RDS instance ID, referencing the ID of the previously created RDS instance resource
- **name**: Account name, assigned by referencing the input variable account\_name
- **password**: Account password, prioritizes using account\_password variable, uses randomly generated password if empty

### 11. Create RDS PostgreSQL Account Privileges

Add the following script to the TF file to instruct Terraform to create an RDS PostgreSQL account privileges resource:

```hcl
# Create an RDS PostgreSQL account privileges resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_rds_pg_account_privileges" "test" {
  instance_id            = huaweicloud_rds_instance.test.id
  user_name              = huaweicloud_rds_pg_account.test.name
  role_privileges        = ["CREATEROLE", "CREATEDB", "LOGIN", "REPLICATION"]
  system_role_privileges = ["pg_signal_backend"]
}
```

**Parameter Description**:

- **instance\_id**: RDS instance ID, referencing the ID of the previously created RDS instance resource
- **user\_name**: Username, referencing the name of the previously created RDS PostgreSQL account resource
- **role\_privileges**: Role privileges list, set to \["CREATEROLE", "CREATEDB", "LOGIN", "REPLICATION"]
- **system\_role\_privileges**: System role privileges list, set to \["pg\_signal\_backend"]

### 12. Create RDS PostgreSQL Database

Add the following script to the TF file to instruct Terraform to create an RDS PostgreSQL database resource:

```hcl
variable "database_name" {
  description = "The name of the initial database"
  type        = string
}

# Create an RDS PostgreSQL database resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_rds_pg_database" "test" {
  instance_id = huaweicloud_rds_instance.test.id
  name        = var.database_name
}
```

**Parameter Description**:

- **instance\_id**: RDS instance ID, referencing the ID of the previously created RDS instance resource
- **name**: Database name, assigned by referencing the input variable database\_name

### 13. Create RDS PostgreSQL Schema

Add the following script to the TF file to instruct Terraform to create an RDS PostgreSQL schema resource:

```hcl
variable "schema_name" {
  description = "The name of the database schema"
  type        = string
}

# Create an RDS PostgreSQL schema resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_rds_pg_schema" "test" {
  instance_id = huaweicloud_rds_instance.test.id
  db_name     = huaweicloud_rds_pg_database.test.name
  owner       = huaweicloud_rds_pg_account.test.name
  schema_name = var.schema_name
}
```

**Parameter Description**:

- **instance\_id**: RDS instance ID, referencing the ID of the previously created RDS instance resource
- **db\_name**: Database name, referencing the name of the previously created RDS PostgreSQL database resource
- **owner**: Schema owner, referencing the name of the previously created RDS PostgreSQL account resource
- **schema\_name**: Schema name, assigned by referencing the input variable schema\_name

### 14. Create RDS Backup

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

  depends_on = [huaweicloud_rds_pg_schema.test]
}
```

**Parameter Description**:

- **instance\_id**: RDS instance ID, referencing the ID of the previously created RDS instance resource
- **name**: Backup name, assigned by referencing the input variable backup\_name
- **depends\_on**: Explicit dependency relationship, ensures schema is configured before backup creation

### 15. Preset Input Parameters Required for Resource Deployment (Optional)

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
instance_name = "tf_test_postgresql_instance"

# Backup configuration
instance_backup_time_window = "08:00-09:00"
instance_backup_keep_days   = 1

# Database account configuration
account_name = "tf_test_account"

# Database configuration
database_name = "tf_test_database"

# Schema configuration
schema_name = "tf_test_schema"

# Backup configuration
backup_name = "tf_test_backup"
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

### 16. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating PostgreSQL HA instances
4. Run `terraform show` to view the created PostgreSQL HA instance details

## Reference Information

- [Huawei Cloud Relational Database Service Product Documentation](https://support.huaweicloud.com/rds/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For RDS PostgreSQL HA Instance](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/rds/postgresql-ha-instance)
