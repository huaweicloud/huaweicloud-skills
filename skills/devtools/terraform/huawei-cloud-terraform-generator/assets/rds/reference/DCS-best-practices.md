# Deploy Single-Node Redis Instance

## Application Scenario

Distributed Cache Service (DCS) is a high-performance, highly available in-memory database service provided by Huawei Cloud, supporting mainstream cache engines such as Redis and Memcached. DCS service provides multiple instance specifications and deployment modes, including single-node, master-standby, and cluster, meeting cache requirements for different scales and scenarios.

Single-node Redis instance is the basic deployment mode in DCS service, suitable for development and testing environments, small-scale applications, or scenarios with low high availability requirements. Single-node instances have the characteristics of low cost, simple deployment, and easy maintenance, making them an ideal choice for learning and using Redis. This best practice will introduce how to use Terraform to automatically deploy DCS single-node Redis instances, including VPC creation, instance configuration, and basic network setup.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [DCS Flavors Query Data Source (data.huaweicloud\_dcs\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/dcs_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [DCS Instance Resource (huaweicloud\_dcs\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dcs_instance)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones.test
    └── huaweicloud_dcs_instance.test

data.huaweicloud_dcs_flavors.test
    └── huaweicloud_dcs_instance.test

huaweicloud_vpc.test
    └── huaweicloud_vpc_subnet.test
        └── huaweicloud_dcs_instance.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create VPC

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC resource:

```hcl
variable "vpc_name" {
  description = "VPC name"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
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
- **cidr**: VPC CIDR block, assigned by referencing the input variable vpc\_cidr

### 3. Create VPC Subnet

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "Subnet name"
  type        = string
}

variable "subnet_cidr" {
  description = "Subnet CIDR block"
  type        = string
  default     = ""
  nullable    = false
}

variable "subnet_gateway_ip" {
  description = "Subnet gateway IP address"
  type        = string
  default     = ""
  nullable    = false
}

# Create a VPC subnet resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr != "" ? var.subnet_cidr : cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0)
  gateway_ip = var.subnet_gateway_ip != "" ? var.subnet_gateway_ip : cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1)
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID, assigned by referencing the VPC resource (huaweicloud\_vpc.test) ID
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, prioritizes using input variable, if empty then calculated using cidrsubnet function
- **gateway\_ip**: Gateway IP, prioritizes using input variable, if empty then calculated using cidrhost function

### 4. Query Availability Zone Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to create DCS instances:

```hcl
variable "availability_zone" {
  description = "Availability zone to which the Redis single-node instance belongs"
  type        = string
  default     = ""
  nullable    = false
}

# Get all availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create DCS instances
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}
```

**Parameter Description**:

- **count**: Data source creation count, used to control whether to execute the availability zones list query data source, only creates data source when `var.availability_zone` is empty

### 5. Query DCS Flavor Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to create DCS instances:

```hcl
variable "instance_flavor_id" {
  description = "Redis single-node instance flavor ID"
  type        = string
  default     = ""
}

variable "instance_capacity" {
  description = "Redis instance capacity (GB)"
  type        = number
  default     = 1
}

variable "instance_engine_version" {
  description = "Redis single-node instance engine version"
  type        = string
  default     = "7.0"
}

# Get all DCS flavor information that meets the conditions under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create DCS instances
data "huaweicloud_dcs_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  cache_mode     = "single"
  capacity       = var.instance_capacity
  engine_version = var.instance_engine_version
}
```

**Parameter Description**:

- **count**: Data source creation count, used to control whether to execute the DCS flavors list query data source, only creates data source when `var.instance_flavor_id` is empty
- **cache\_mode**: Cache mode, set to "single" for single-node mode
- **capacity**: Capacity, assigned by referencing the input variable instance\_capacity
- **engine\_version**: Engine version, assigned by referencing the input variable instance\_engine\_version

### 6. Create DCS Single-Node Redis Instance

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a DCS instance resource:

```hcl
variable "instance_name" {
  description = "Redis single-node instance name"
  type        = string
}

variable "enterprise_project_id" {
  description = "Enterprise project ID to which the Redis single-node instance belongs"
  type        = string
  default     = null
}

variable "instance_password" {
  description = "Redis instance password"
  type        = string
  sensitive   = true
  default     = null
}

variable "charging_mode" {
  description = "Redis instance charging mode"
  type        = string
  default     = "postPaid"
}

variable "period_unit" {
  description = "Charging period unit"
  type        = string
  default     = null
}

variable "period" {
  description = "Redis instance charging period"
  type        = number
  default     = null
}

variable "auto_renew" {
  description = "Whether to enable auto-renewal"
  type        = string
  default     = "false"
}

# Create a DCS instance resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_dcs_instance" "test" {
  name                  = var.instance_name
  engine                = "Redis"
  enterprise_project_id = var.enterprise_project_id
  engine_version        = var.instance_engine_version
  capacity              = var.instance_capacity
  flavor                = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_dcs_flavors.test[0].flavors[0].name, null)
  availability_zones    = var.availability_zone != "" ? [var.availability_zone] : try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 1), null)
  vpc_id                = huaweicloud_vpc.test.id
  subnet_id             = huaweicloud_vpc_subnet.test.id
  password              = var.instance_password
  charging_mode         = var.charging_mode
  period_unit           = var.period_unit
  period                = var.period
  auto_renew            = var.auto_renew

  # If you want to change the `flavor` or `availability_zones`, you need to delete it from the `lifecycle.ignore_changes`.
  lifecycle {
    ignore_changes = [
      flavor,
      availability_zones,
    ]
  }
}
```

**Parameter Description**:

- **name**: Instance name, assigned by referencing the input variable instance\_name
- **engine**: Engine type, set to "Redis"
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable enterprise\_project\_id
- **engine\_version**: Engine version, assigned by referencing the input variable instance\_engine\_version
- **capacity**: Capacity, assigned by referencing the input variable instance\_capacity
- **flavor**: Flavor, prioritizes using input variable, if empty then uses the first result from DCS flavors list query data source
- **availability\_zones**: Availability zones list, prioritizes using input variable, if empty then uses the first result from availability zones list query data source
- **vpc\_id**: VPC ID, assigned by referencing the VPC resource (huaweicloud\_vpc.test) ID
- **subnet\_id**: Subnet ID, assigned by referencing the VPC subnet resource (huaweicloud\_vpc\_subnet.test) ID
- **password**: Password, assigned by referencing the input variable instance\_password
- **charging\_mode**: Charging mode, assigned by referencing the input variable charging\_mode
- **period\_unit**: Charging period unit, assigned by referencing the input variable period\_unit
- **period**: Charging period, assigned by referencing the input variable period
- **auto\_renew**: Auto-renewal, assigned by referencing the input variable auto\_renew
- **lifecycle.ignore\_changes**: Lifecycle ignore changes, ignores changes to flavor and availability\_zones

### 7. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Network configuration
vpc_name    = "tf_test_dcs_instance_vpc"
subnet_name = "tf_test_dcs_instance_subnet"

# DCS instance configuration
instance_name     = "tf_test_dcs_instance"
instance_password = "YourRedisInstancePassword!"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="instance_name=my-redis"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the DCS single-node Redis instance
4. Run `terraform show` to view the details of the created DCS single-node Redis instance

## Reference Information

- [Huawei Cloud DCS Product Documentation](https://support.huaweicloud.com/dcs/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For DCS Single-Node Redis Instance](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dcs/redis-single-instance)

# Deploy Master-Standby Redis Instance

## Application Scenario

Distributed Cache Service (DCS) is a high-performance, highly available in-memory database service provided by Huawei Cloud, supporting mainstream cache engines such as Redis and Memcached. DCS service provides multiple instance specifications and deployment modes, including single-node, master-standby, and cluster, meeting cache requirements for different scales and scenarios.

Master-standby Redis instance is the high availability deployment mode in DCS service, implementing data redundancy and automatic failover through master-standby architecture, ensuring high availability of cache services. Master-standby instances support automatic fault detection and failover. When the master node fails, the standby node will automatically take over the service, ensuring business continuity. This best practice will introduce how to use Terraform to automatically deploy DCS master-standby Redis instances, including VPC creation, instance configuration, backup policy, and whitelist management.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [DCS Flavors Query Data Source (data.huaweicloud\_dcs\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/dcs_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [DCS Instance Resource (huaweicloud\_dcs\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dcs_instance)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones.test
    └── huaweicloud_dcs_instance.test

data.huaweicloud_dcs_flavors.test
    └── huaweicloud_dcs_instance.test

huaweicloud_vpc.test
    └── huaweicloud_vpc_subnet.test
        └── huaweicloud_dcs_instance.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create VPC

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC resource:

```hcl
variable "vpc_name" {
  description = "VPC name"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
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
- **cidr**: VPC CIDR block, assigned by referencing the input variable vpc\_cidr

### 3. Create VPC Subnet

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "Subnet name"
  type        = string
}

variable "subnet_cidr" {
  description = "Subnet CIDR block"
  type        = string
  default     = ""
  nullable    = false
}

variable "subnet_gateway_ip" {
  description = "Subnet gateway IP address"
  type        = string
  default     = ""
  nullable    = false
}

# Create a VPC subnet resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr != "" ? var.subnet_cidr : cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0)
  gateway_ip = var.subnet_gateway_ip != "" ? var.subnet_gateway_ip : cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1)
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID, assigned by referencing the VPC resource (huaweicloud\_vpc.test) ID
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, prioritizes using input variable, if empty then calculated using cidrsubnet function
- **gateway\_ip**: Gateway IP, prioritizes using input variable, if empty then calculated using cidrhost function

### 4. Query Availability Zone Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to create DCS instances:

```hcl
variable "availability_zones" {
  description = "Availability zones list to which the Redis instance belongs"
  type        = list(string)
  default     = []
  nullable    = false
}

# Get all availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create DCS instances
data "huaweicloud_availability_zones" "test" {
  count = length(var.availability_zones) < 1 ? 1 : 0
}
```

**Parameter Description**:

- **count**: Data source creation count, used to control whether to execute the availability zones list query data source, only creates data source when `var.availability_zones` length is less than 1

### 5. Query DCS Flavor Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to create DCS instances:

```hcl
variable "instance_flavor_id" {
  description = "Redis instance flavor ID"
  type        = string
  default     = ""
  nullable    = false
}

variable "instance_cache_mode" {
  description = "Redis instance cache mode"
  type        = string
  default     = "ha"
}

variable "instance_capacity" {
  description = "Redis instance capacity (GB)"
  type        = number
  default     = 4
}

variable "instance_engine_version" {
  description = "Redis instance engine version"
  type        = string
  default     = "5.0"
}

# Get all DCS flavor information that meets the conditions under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create DCS instances
data "huaweicloud_dcs_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  cache_mode     = var.instance_cache_mode
  capacity       = var.instance_capacity
  engine_version = var.instance_engine_version
}
```

**Parameter Description**:

- **count**: Data source creation count, used to control whether to execute the DCS flavors list query data source, only creates data source when `var.instance_flavor_id` is empty
- **cache\_mode**: Cache mode, assigned by referencing the input variable instance\_cache\_mode, set to "ha" for master-standby mode
- **capacity**: Capacity, assigned by referencing the input variable instance\_capacity
- **engine\_version**: Engine version, assigned by referencing the input variable instance\_engine\_version

### 6. Create DCS Master-Standby Redis Instance

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a DCS instance resource:

```hcl
variable "instance_name" {
  description = "Redis instance name"
  type        = string
}

variable "enterprise_project_id" {
  description = "Enterprise project ID to which the Redis instance belongs"
  type        = string
  default     = null
}

variable "instance_password" {
  description = "Redis instance password"
  type        = string
  sensitive   = true
  default     = null
}

variable "instance_backup_policy" {
  description = "Redis instance backup policy"
  type = object({
    backup_type = optional(string, "auto")
    backup_at   = list(number)
    begin_at    = string
    save_days   = optional(number, null)
    period_type = optional(string, null)
  })
  default = null
}

variable "instance_whitelists" {
  description = "Redis instance whitelist"
  type = list(object({
    group_name = string
    ip_address = list(string)
  }))
  default  = []
  nullable = false
}

variable "instance_parameters" {
  description = "Redis instance parameters"
  type = list(object({
    id    = string
    name  = string
    value = string
  }))
  default  = []
  nullable = false
}

variable "instance_tags" {
  description = "Redis instance tags"
  type        = map(string)
  default     = {}
}

variable "instance_rename_commands" {
  description = "Redis instance rename commands"
  type        = map(string)
  default     = {}
}

variable "charging_mode" {
  description = "Redis instance charging mode"
  type        = string
  default     = "postPaid"
}

variable "period_unit" {
  description = "Charging period unit"
  type        = string
  default     = null
}

variable "period" {
  description = "Redis instance charging period"
  type        = number
  default     = null
}

variable "auto_renew" {
  description = "Whether to enable auto-renewal"
  type        = string
  default     = "false"
}

# Create a DCS instance resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_dcs_instance" "test" {
  name                  = var.instance_name
  engine                = "Redis"
  enterprise_project_id = var.enterprise_project_id
  engine_version        = var.instance_engine_version
  capacity              = var.instance_capacity
  flavor                = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_dcs_flavors.test[0].flavors[0].name, null)
  availability_zones    = length(var.availability_zones) > 0 ? var.availability_zones : try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 2), null)
  vpc_id                = huaweicloud_vpc.test.id
  subnet_id             = huaweicloud_vpc_subnet.test.id
  password              = var.instance_password

  dynamic "backup_policy" {
    for_each = var.instance_backup_policy != null ? [var.instance_backup_policy] : []
    content {
      backup_type = lookup(backup_policy.value, "backup_type", null)
      save_days   = lookup(backup_policy.value, "save_days", null)
      period_type = lookup(backup_policy.value, "period_type", null)
      backup_at   = backup_policy.value["backup_at"]
      begin_at    = backup_policy.value["begin_at"]
    }
  }

  dynamic "whitelists" {
    for_each = var.instance_whitelists
    content {
      group_name = whitelists.value["group_name"]
      ip_address = whitelists.value["ip_address"]
    }
  }

  dynamic "parameters" {
    for_each = var.instance_parameters
    content {
      id    = parameters.value["id"]
      name  = parameters.value["name"]
      value = parameters.value["value"]
    }
  }

  tags            = var.instance_tags
  rename_commands = var.instance_rename_commands

  charging_mode = var.charging_mode
  period_unit   = var.period_unit
  period        = var.period
  auto_renew    = var.auto_renew

  # If you want to change the `flavor` or `availability_zones`, you need to delete it from the `lifecycle.ignore_changes`.
  lifecycle {
    ignore_changes = [
      flavor,
      availability_zones,
    ]
  }
}
```

**Parameter Description**:

- **name**: Instance name, assigned by referencing the input variable instance\_name
- **engine**: Engine type, set to "Redis"
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable enterprise\_project\_id
- **engine\_version**: Engine version, assigned by referencing the input variable instance\_engine\_version
- **capacity**: Capacity, assigned by referencing the input variable instance\_capacity
- **flavor**: Flavor, prioritizes using input variable, if empty then uses the first result from DCS flavors list query data source
- **availability\_zones**: Availability zones list, prioritizes using input variable, if empty then uses the first two results from availability zones list query data source
- **vpc\_id**: VPC ID, assigned by referencing the VPC resource (huaweicloud\_vpc.test) ID
- **subnet\_id**: Subnet ID, assigned by referencing the VPC subnet resource (huaweicloud\_vpc\_subnet.test) ID
- **password**: Password, assigned by referencing the input variable instance\_password
- **backup\_policy.backup\_type**: Backup type, assigned by referencing the backup\_type field in backup policy
- **backup\_policy.save\_days**: Save days, assigned by referencing the save\_days field in backup policy
- **backup\_policy.period\_type**: Period type, assigned by referencing the period\_type field in backup policy
- **backup\_policy.backup\_at**: Backup time, assigned by referencing the backup\_at field in backup policy
- **backup\_policy.begin\_at**: Begin time, assigned by referencing the begin\_at field in backup policy
- **whitelists.group\_name**: Whitelist group name, assigned by referencing the group\_name field in whitelist list
- **whitelists.ip\_address**: IP address list, assigned by referencing the ip\_address field in whitelist list
- **parameters.id**: Parameter ID, assigned by referencing the id field in parameter list
- **parameters.name**: Parameter name, assigned by referencing the name field in parameter list
- **parameters.value**: Parameter value, assigned by referencing the value field in parameter list
- **tags**: Tags, assigned by referencing the input variable instance\_tags
- **rename\_commands**: Rename commands, assigned by referencing the input variable instance\_rename\_commands
- **charging\_mode**: Charging mode, assigned by referencing the input variable charging\_mode
- **period\_unit**: Charging period unit, assigned by referencing the input variable period\_unit
- **period**: Charging period, assigned by referencing the input variable period
- **auto\_renew**: Auto-renewal, assigned by referencing the input variable auto\_renew
- **lifecycle.ignore\_changes**: Lifecycle ignore changes, ignores changes to flavor and availability\_zones

### 7. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Network configuration
vpc_name    = "tf_test_dcs_instance_vpc"
subnet_name = "tf_test_dcs_instance_subnet"

# DCS instance configuration
instance_name     = "tf_test_dcs_instance"
instance_password = "YourRedisInstancePassword!"

# Backup policy configuration
instance_backup_policy = {
  backup_type = "auto"
  backup_at   = [1, 3, 4, 5, 6]
  begin_at    = "02:00-04:00"
  save_days   = 7
}

# Whitelist configuration
instance_whitelists = [
  {
    group_name = "test-group1"
    ip_address = ["192.168.10.100", "192.168.0.0/24"]
  },
  {
    group_name = "test-group2"
    ip_address = ["172.16.10.100", "172.16.0.0/24"]
  }
]

# Parameter configuration
instance_parameters = [
  {
    id    = "1"
    name  = "timeout"
    value = "500"
  },
  {
    id    = "3"
    name  = "hash-max-ziplist-entries"
    value = "4096"
  }
]

# Tag configuration
instance_tags = {
  foo = "bar"
}
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="instance_name=my-redis"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the DCS master-standby Redis instance
4. Run `terraform show` to view the details of the created DCS master-standby Redis instance

## Reference Information

- [Huawei Cloud DCS Product Documentation](https://support.huaweicloud.com/dcs/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For DCS Master-Standby Redis Instance](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dcs/redis-high-availability-instance)
