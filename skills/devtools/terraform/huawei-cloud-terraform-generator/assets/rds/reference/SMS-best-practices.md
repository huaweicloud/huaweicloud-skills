# Deploy Migration Project

## Application Scenario

Server Migration Service (SMS) is a server migration service provided by Huawei Cloud, supporting migration of physical servers, virtual machines, or servers from other cloud platforms to Huawei Cloud, achieving seamless business migration. Migration projects are fundamental resources of SMS service, used to manage and organize migration tasks. By creating migration projects, parameters such as migration region, network type, server type, and synchronization policy can be configured, providing basic configuration for subsequent migration tasks. This best practice introduces how to use Terraform to automatically deploy migration projects, including project basic information, region configuration, network configuration, and synchronization policy configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [Migration Project Resource (huaweicloud\_sms\_migration\_project)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/sms_migration_project)

### Resource/Data Source Dependencies

```
huaweicloud_sms_migration_project
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Create Migration Project

Add the following script to the TF file (such as main.tf) to create a migration project:

```hcl
variable "migration_project_name" {
  description = "The migration project name"
  type        = string
}

variable "migration_project_region" {
  description = "The region name"
  type        = string
}

variable "migration_project_use_public_ip" {
  description = "Whether to use a public IP address for migration"
  type        = bool
}

variable "migration_project_exist_server" {
  description = "Whether the server already exists"
  type        = bool
}

variable "migration_project_type" {
  description = "The migration project typ"
  type        = string
}

variable "migration_project_syncing" {
  description = "Whether to continue syncing after the first copy or sync"
  type        = bool
}

# Create migration project resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_sms_migration_project" "test" {
  name          = var.migration_project_name
  region        = var.migration_project_region
  use_public_ip = var.migration_project_use_public_ip
  exist_server  = var.migration_project_exist_server
  type          = var.migration_project_type
  syncing       = var.migration_project_syncing
}
```

**Parameter Description**:

- **name**: Migration project name, assigned by referencing the input variable `migration_project_name`
- **region**: Region name, assigned by referencing the input variable `migration_project_region`, used to specify the migration target region
- **use\_public\_ip**: Whether to use public IP for migration, assigned by referencing the input variable `migration_project_use_public_ip`
- **exist\_server**: Whether the server already exists, assigned by referencing the input variable `migration_project_exist_server`
- **type**: Migration project type, assigned by referencing the input variable `migration_project_type`
- **syncing**: Whether to continue syncing after the first copy or sync, assigned by referencing the input variable `migration_project_syncing`

> Note: Migration projects are used to manage and organize migration tasks, and need to configure corresponding parameters according to actual migration scenarios. If using public IP for migration, ensure that the source server can access the public network.

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Migration project basic information (Required)
migration_project_name          = "tf_test_sms_migration_project"
migration_project_region        = "cn-north-4"
migration_project_use_public_ip = true
migration_project_exist_server  = true
migration_project_type          = "LINUX"
migration_project_syncing       = true
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="migration_project_name=tf_test_sms_migration_project" -var="migration_project_region=cn-north-4"`
2. Environment variables: `export TF_VAR_migration_project_name=tf_test_sms_migration_project`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the migration project
4. Run `terraform show` to view the created migration project

## Reference Information

- [Huawei Cloud SMS Product Documentation](https://support.huaweicloud.com/sms/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Migration Project](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/sms/migration-project)

# Deploy Migration Task

## Application Scenario

Server Migration Service (SMS) is a server migration service provided by Huawei Cloud, supporting migration of physical servers, virtual machines, or servers from other cloud platforms to Huawei Cloud, achieving seamless business migration. Migration tasks are core resources of SMS service, used to execute specific server migration operations. By creating migration tasks, parameters such as migration type, operating system type, source server, and target template can be configured, achieving automated server migration. This best practice introduces how to use Terraform to automatically deploy migration tasks, including querying availability zones and source servers, creating server templates, and creating migration tasks.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [Source Servers Query Data Source (data.huaweicloud\_sms\_source\_servers)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/sms_source_servers)

### Resources

- [Server Template Resource (huaweicloud\_sms\_server\_template)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/sms_server_template)
- [Migration Task Resource (huaweicloud\_sms\_task)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/sms_task)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── huaweicloud_sms_server_template

data.huaweicloud_sms_source_servers
    └── huaweicloud_sms_task

huaweicloud_sms_server_template
    └── huaweicloud_sms_task
```

> Note: Migration tasks depend on source servers and server templates. Server templates need to specify availability zones for creating target servers. Migration tasks configure migration parameters by referencing source server IDs and server template IDs.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Query Availability Zones List

Add the following script to the TF file (such as main.tf) to query the availability zones list:

```hcl
# Query availability zones list data source
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**:

- This data source does not require input parameters and will automatically query all availability zones in the current region

> Note: The availability zones list is used to specify availability zones when creating server templates later.

### 3. Query Source Servers List

Add the following script to the TF file (such as main.tf) to query the source servers list:

```hcl
variable "source_server_name" {
  description = "The name of the SMS source server"
  type        = string
  default     = null
}

# Query source servers list data source
data "huaweicloud_sms_source_servers" "test" {
  name = var.source_server_name
}
```

**Parameter Description**:

- **name**: Source server name, assigned by referencing the input variable `source_server_name`, optional parameter, used to filter source servers

> Note: The source servers list is used to obtain information about source servers that need to be migrated. The source server ID needs to be referenced when creating migration tasks later.

### 4. Create Server Template

Add the following script to the TF file (such as main.tf) to create a server template:

```hcl
variable "server_template_name" {
  description = "The name of the SMS server template"
  type        = string
}

# Create server template resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_sms_server_template" "test" {
  name              = var.server_template_name
  availability_zone = try(data.huaweicloud_availability_zones.test.names[0], null)
}
```

**Parameter Description**:

- **name**: Server template name, assigned by referencing the input variable `server_template_name`
- **availability\_zone**: Availability zone, assigned by referencing the first availability zone name from the availability zones list data source, using `try` function to handle possible null values

> Note: Server templates are used to define target server configurations, including availability zones, specifications, and other information. Server template IDs need to be referenced when creating migration tasks.

### 5. Create Migration Task

Add the following script to the TF file (such as main.tf) to create a migration task:

```hcl
variable "migrate_task_type" {
  description = "The type of the SMS task"
  type        = string
}

variable "server_os_type" {
  description = "The OS type of the server"
  type        = string
}

# Create migration task resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_sms_task" "test" {
  type             = var.migrate_task_type
  os_type          = var.server_os_type
  source_server_id = try(data.huaweicloud_sms_source_servers.test.servers[0].id, null)
  vm_template_id   = huaweicloud_sms_server_template.test.id
}
```

**Parameter Description**:

- **type**: Migration task type, assigned by referencing the input variable `migrate_task_type`, supports `MIGRATE_BLOCK` (block-level migration) and `MIGRATE_FILE` (file-level migration)
- **os\_type**: Server operating system type, assigned by referencing the input variable `server_os_type`, supports `WINDOWS` and `LINUX`
- **source\_server\_id**: Source server ID, assigned by referencing the first server ID from the source servers list data source, using `try` function to handle possible null values
- **vm\_template\_id**: Virtual machine template ID, assigned by referencing the server template resource ID

> Note: Migration tasks are used to execute specific server migration operations. Migration task types need to be selected according to actual requirements. Block-level migration is suitable for whole machine migration, and file-level migration is suitable for file migration. Source server ID and virtual machine template ID are required parameters.

### 6. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Source server configuration (Optional)
source_server_name = "tf_source_server_name"

# Server template configuration (Required)
server_template_name = "tf_server_template_name"

# Migration task configuration (Required)
migrate_task_type = "MIGRATE_BLOCK"
server_os_type    = "WINDOWS"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="server_template_name=tf_server_template_name" -var="migrate_task_type=MIGRATE_BLOCK"`
2. Environment variables: `export TF_VAR_server_template_name=tf_server_template_name`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 7. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating server template and migration task
4. Run `terraform show` to view the created migration task

## Reference Information

- [Huawei Cloud SMS Product Documentation](https://support.huaweicloud.com/sms/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Migration Task](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/sms/migration-task)

# Deploy Server Template

## Application Scenario

Server Migration Service (SMS) is a server migration service provided by Huawei Cloud, supporting migration of physical servers, virtual machines, or servers from other cloud platforms to Huawei Cloud, achieving seamless business migration. Server templates are important resources of SMS service, used to define target server configuration information, including availability zones, specifications, networks, and other parameters. By creating server templates, configuration templates for target servers can be provided for migration tasks, achieving standardization and automation of the migration process. This best practice introduces how to use Terraform to automatically deploy server templates, including querying availability zones and creating server templates.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)

### Resources

- [Server Template Resource (huaweicloud\_sms\_server\_template)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/sms_server_template)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── huaweicloud_sms_server_template
```

> Note: Server templates need to specify availability zones for creating target servers. Availability zone information in the current region can be obtained by querying the availability zones list data source.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Query Availability Zones List

Add the following script to the TF file (such as main.tf) to query the availability zones list:

```hcl
# Query availability zones list data source
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**:

- This data source does not require input parameters and will automatically query all availability zones in the current region

> Note: The availability zones list is used to specify availability zones when creating server templates later.

### 3. Create Server Template

Add the following script to the TF file (such as main.tf) to create a server template:

```hcl
variable "server_template_name" {
  description = "The server template name"
  type        = string
}

# Create server template resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_sms_server_template" "test" {
  name              = var.server_template_name
  availability_zone = try(data.huaweicloud_availability_zones.test.names[0], null)
}
```

**Parameter Description**:

- **name**: Server template name, assigned by referencing the input variable `server_template_name`
- **availability\_zone**: Availability zone, assigned by referencing the first availability zone name from the availability zones list data source, using `try` function to handle possible null values

> Note: Server templates are used to define target server configurations, including availability zones, specifications, and other information. Server template IDs need to be referenced when creating migration tasks. Availability zones need to be selected according to actual requirements, ensuring sufficient resources in the target region.

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Server template configuration (Required)
server_template_name = "tf_test_sms_server_template"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="server_template_name=tf_test_sms_server_template"`
2. Environment variables: `export TF_VAR_server_template_name=tf_test_sms_server_template`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the server template
4. Run `terraform show` to view the created server template

## Reference Information

- [Huawei Cloud SMS Product Documentation](https://support.huaweicloud.com/sms/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Server Template](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/sms/server-template)
